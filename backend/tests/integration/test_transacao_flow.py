"""Testes de integração do CRUD de Transação: TestClient + banco real
(SQLite em memória). Cobre isolamento entre usuários, validação estrutural
(conta XOR cartão, contrato/numero_parcela), resolução automática de
fatura para transação de cartão (via FaturaService.resolver_fatura_aberta),
status forçado para transação de cartão, imutabilidade de transação
vinculada a fatura fechada e ausência de soft delete.
"""


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente"):
    resposta = client.post("/contas", json={"nome": nome}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_cartao(client, headers, conta_id, nome="Nubank", dia_fechamento=10, dia_vencimento=17):
    payload = {
        "nome": nome,
        "conta_pagamento_id": conta_id,
        "instituicao": "Nu Pagamentos",
        "bandeira": "MASTERCARD",
        "ultimos_quatro_digitos": "1234",
        "limite": "5000.00",
        "dia_fechamento": dia_fechamento,
        "dia_vencimento": dia_vencimento,
    }
    resposta = client.post("/cartoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_categoria(client, headers, nome="Alimentação", tipo=None):
    payload = {"nome": nome}
    if tipo is not None:
        payload["tipo"] = tipo
    resposta = client.post("/categorias", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_tag(client, headers, nome="viagem"):
    resposta = client.post("/tags", json={"nome": nome}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_transacao(client, headers, **overrides):
    payload = {
        "tipo": "DESPESA",
        "valor": "100.00",
        "data": "2026-07-03",
        "descricao": "Compra",
    }
    payload.update(overrides)
    # chaves explicitamente None (ex: conta_id=None ao criar uma transacao
    # de cartao) sao omitidas do payload, nunca enviadas como JSON null -
    # nenhum teste aqui depende de mandar null de proposito.
    payload = {chave: valor for chave, valor in payload.items() if valor is not None}
    return client.post("/transacoes", json=payload, headers=headers)


# --- autenticação / estrutura -----------------------------------------------

def test_criar_transacao_sem_autenticacao_retorna_401(client):
    resposta = client.post(
        "/transacoes",
        json={"tipo": "DESPESA", "valor": "10.00", "data": "2026-07-03", "descricao": "x", "conta_id": 1},
    )
    assert resposta.status_code == 401


def test_criar_transacao_sem_conta_e_sem_cartao_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post(
        "/transacoes",
        json={"tipo": "DESPESA", "valor": "10.00", "data": "2026-07-03", "descricao": "x"},
        headers=headers,
    )
    assert resposta.status_code == 422


def test_criar_transacao_com_conta_e_cartao_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "10.00",
            "data": "2026-07-03",
            "descricao": "x",
            "conta_id": conta["id"],
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    assert resposta.status_code == 422


def test_criar_transacao_com_numero_parcela_sem_contrato_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "10.00",
            "data": "2026-07-03",
            "descricao": "x",
            "conta_id": conta["id"],
            "numero_parcela": 2,
        },
        headers=headers,
    )
    assert resposta.status_code == 422


# --- transação de conta ------------------------------------------------------

def test_criar_e_obter_transacao_de_conta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    resposta = _criar_transacao(client, headers, conta_id=conta["id"])
    assert resposta.status_code == 201, resposta.text
    transacao = resposta.json()
    assert transacao["conta_id"] == conta["id"]
    assert transacao["cartao_id"] is None
    assert transacao["status"] == "PENDENTE"  # default para transacao de conta
    assert transacao["fatura_id"] is None

    resposta_get = client.get(f"/transacoes/{transacao['id']}", headers=headers)
    assert resposta_get.status_code == 200
    assert resposta_get.json()["id"] == transacao["id"]


def test_criar_transacao_com_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)

    resposta = _criar_transacao(client, headers_ana, conta_id=conta_bruno["id"])
    assert resposta.status_code == 404


def test_criar_transacao_em_conta_inativa_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta_desativar = client.delete(f"/contas/{conta['id']}", headers=headers)
    assert resposta_desativar.status_code == 204

    resposta = _criar_transacao(client, headers, conta_id=conta["id"])
    assert resposta.status_code == 422


def test_criar_transacao_com_status_explicito_em_conta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_transacao(client, headers, conta_id=conta["id"], status="PAGO")
    assert resposta.json()["status"] == "PAGO"


# --- transação de cartão: resolução de fatura -------------------------------

def test_criar_transacao_de_cartao_resolve_e_cria_fatura_automaticamente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    resposta = _criar_transacao(
        client, headers, conta_id=None, cartao_id=cartao["id"], data="2026-07-03"
    )
    assert resposta.status_code == 201, resposta.text
    transacao = resposta.json()
    assert transacao["cartao_id"] == cartao["id"]
    assert transacao["fatura_id"] is not None
    assert transacao["status"] == "PAGO"  # forcado, mesmo sem enviar no payload

    resposta_faturas = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers)
    faturas = resposta_faturas.json()
    assert len(faturas) == 1
    assert faturas[0]["mes_referencia"] == "2026-07-01"
    assert faturas[0]["valor_total"] == "100.00"


def test_criar_transacao_ignora_status_enviado_para_cartao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = _criar_transacao(
        client, headers, conta_id=None, cartao_id=cartao["id"], status="PENDENTE"
    )
    assert resposta.json()["status"] == "PAGO"


def test_duas_compras_no_mesmo_ciclo_reaproveitam_a_mesma_fatura(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    t1 = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"], data="2026-07-01").json()
    t2 = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"], data="2026-07-08").json()

    assert t1["fatura_id"] == t2["fatura_id"]

    resposta_faturas = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers)
    assert len(resposta_faturas.json()) == 1


def test_compra_apos_fechamento_cai_no_ciclo_seguinte(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    antes = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"], data="2026-07-05").json()
    depois = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"], data="2026-07-15").json()

    assert antes["fatura_id"] != depois["fatura_id"]

    resposta_faturas = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers)
    faturas = {f["id"]: f["mes_referencia"] for f in resposta_faturas.json()}
    assert faturas[antes["fatura_id"]] == "2026-07-01"
    assert faturas[depois["fatura_id"]] == "2026-08-01"


def test_criar_transacao_com_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)
    cartao_bruno = _criar_cartao(client, headers_bruno, conta_bruno["id"])

    resposta = _criar_transacao(client, headers_ana, conta_id=None, cartao_id=cartao_bruno["id"])
    assert resposta.status_code == 404


def test_criar_transacao_em_cartao_inativo_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    client.delete(f"/cartoes/{cartao['id']}", headers=headers)

    resposta = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"])
    assert resposta.status_code == 422


# --- categoria / tags ---------------------------------------------------------

def test_criar_transacao_com_categoria_tipo_incompativel_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    categoria = _criar_categoria(client, headers, tipo="DESPESA")

    resposta = _criar_transacao(
        client, headers, conta_id=conta["id"], tipo="RECEITA", categoria_id=categoria["id"]
    )
    assert resposta.status_code == 422


def test_criar_transacao_com_categoria_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    categoria_bruno = _criar_categoria(client, headers_bruno)

    resposta = _criar_transacao(
        client, headers_ana, conta_id=conta_ana["id"], categoria_id=categoria_bruno["id"]
    )
    assert resposta.status_code == 404


def test_criar_transacao_com_tag_do_usuario_e_aceita(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    tag = _criar_tag(client, headers)

    resposta = _criar_transacao(client, headers, conta_id=conta["id"], tag_ids=[tag["id"]])
    assert resposta.status_code == 201, resposta.text
    assert [t["id"] for t in resposta.json()["tags"]] == [tag["id"]]


def test_criar_transacao_com_tag_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    tag_bruno = _criar_tag(client, headers_bruno)

    resposta = _criar_transacao(client, headers_ana, conta_id=conta_ana["id"], tag_ids=[tag_bruno["id"]])
    assert resposta.status_code == 404


# --- listar / posse -----------------------------------------------------------

def test_obter_transacao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    transacao_ana = _criar_transacao(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.get(f"/transacoes/{transacao_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_listar_transacoes_retorna_apenas_as_do_usuario(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_bruno = _criar_conta(client, headers_bruno)
    _criar_transacao(client, headers_ana, conta_id=conta_ana["id"])
    _criar_transacao(client, headers_bruno, conta_id=conta_bruno["id"])

    resposta = client.get("/transacoes", headers=headers_ana)
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_listar_transacoes_filtra_por_conta_id(client):
    headers = _registrar_e_logar(client)
    conta_a = _criar_conta(client, headers, nome="Conta A")
    conta_b = _criar_conta(client, headers, nome="Conta B")
    _criar_transacao(client, headers, conta_id=conta_a["id"])
    _criar_transacao(client, headers, conta_id=conta_b["id"])

    resposta = client.get(f"/transacoes?conta_id={conta_a['id']}", headers=headers)
    transacoes = resposta.json()
    assert len(transacoes) == 1
    assert transacoes[0]["conta_id"] == conta_a["id"]


def test_listar_transacoes_filtra_por_fatura_id_retorna_so_as_compras_daquele_ciclo(client):
    """Pedido do usuário (2026-07-20): "seria interessante se cada fatura
    tivesse o histórico de compras dela". `fatura_id` filtra as compras
    lançadas NAQUELE ciclo - diferente de `fatura_paga_id` (pagamento da
    fatura, uma Transacao separada na Conta, nunca aparece aqui)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    _criar_transacao(client, headers, cartao_id=cartao["id"], descricao="Compra de julho 1", data="2026-07-03")
    _criar_transacao(client, headers, cartao_id=cartao["id"], descricao="Compra de julho 2", data="2026-07-05")
    _criar_transacao(client, headers, cartao_id=cartao["id"], descricao="Compra de agosto", data="2026-08-03")

    faturas = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers).json()
    fatura_julho = next(f for f in faturas if f["mes_referencia"] == "2026-07-01")

    resposta = client.get(f"/transacoes?fatura_id={fatura_julho['id']}", headers=headers)
    assert resposta.status_code == 200
    descricoes = {t["descricao"] for t in resposta.json()}
    assert descricoes == {"Compra de julho 1", "Compra de julho 2"}


def test_listar_transacoes_apenas_conta_esconde_compra_de_cartao_mas_mantem_pagamento_de_fatura(client):
    """Pedido explícito do usuário (2026-07-20): a tela de Transações não
    deve listar compras de cartão - só lançamentos de Conta (diretos ou
    pagamento de fatura, que também é uma Transacao com conta_id, nunca
    cartao_id - ver FaturaService.registrar_pagamento)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    _criar_transacao(client, headers, conta_id=conta["id"], descricao="Salário")
    _criar_transacao(client, headers, cartao_id=cartao["id"], descricao="Compra no cartão")

    # A compra de cartão acima já resolveu/criou a fatura ABERTA do ciclo
    # (FaturaService.resolver_fatura_aberta) - buscamos ela em vez de criar
    # de novo (POST /faturas duplicado daria 409).
    fatura = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers).json()[0]
    fatura_fechada = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers).json()
    client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": fatura_fechada["valor_total"], "data": "2026-07-18", "descricao": "Pagamento"},
        headers=headers,
    )

    resposta = client.get("/transacoes?apenas_conta=true", headers=headers)
    assert resposta.status_code == 200
    transacoes = resposta.json()
    descricoes = {t["descricao"] for t in transacoes}
    assert "Compra no cartão" not in descricoes
    assert "Salário" in descricoes
    assert any(t["fatura_paga_id"] == fatura["id"] for t in transacoes)
    assert all(t["cartao_id"] is None for t in transacoes)

    # Sem o filtro, a compra de cartão continua aparecendo normalmente -
    # a regra é opt-in, não muda o comportamento padrão de mais ninguém.
    resposta_sem_filtro = client.get("/transacoes", headers=headers)
    assert "Compra no cartão" in {t["descricao"] for t in resposta_sem_filtro.json()}


# --- atualizar -----------------------------------------------------------

def test_atualizar_transacao_de_conta_aplica_apenas_campos_enviados(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta_id=conta["id"], descricao="Original").json()

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"valor": "250.00"}, headers=headers
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["descricao"] == "Original"
    assert corpo["valor"] == "250.00"


def test_atualizar_transacao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    transacao_ana = _criar_transacao(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.patch(
        f"/transacoes/{transacao_ana['id']}", json={"descricao": "Hackeado"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


def test_atualizar_status_em_transacao_de_cartao_e_ignorado(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    transacao = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"]).json()
    assert transacao["status"] == "PAGO"

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"status": "PENDENTE"}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "PAGO"


def test_atualizar_valor_bloqueado_quando_fatura_fechada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    transacao = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"]).json()

    client.post(f"/faturas/{transacao['fatura_id']}/fechar", headers=headers)

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"valor": "999.00"}, headers=headers
    )
    assert resposta.status_code == 422


def test_atualizar_descricao_permitido_mesmo_com_fatura_fechada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    transacao = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"]).json()

    client.post(f"/faturas/{transacao['fatura_id']}/fechar", headers=headers)

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"descricao": "Recategorizada"}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.json()["descricao"] == "Recategorizada"


def test_atualizar_valor_permitido_enquanto_fatura_ainda_aberta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    transacao = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"]).json()

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"valor": "150.00"}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.json()["valor"] == "150.00"


# --- excluir -------------------------------------------------------------

def test_excluir_transacao_de_conta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta_id=conta["id"]).json()

    resposta = client.delete(f"/transacoes/{transacao['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/transacoes/{transacao['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_transacao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    transacao_ana = _criar_transacao(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.delete(f"/transacoes/{transacao_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_excluir_transacao_de_compra_com_fatura_fechada_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    transacao = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"]).json()

    client.post(f"/faturas/{transacao['fatura_id']}/fechar", headers=headers)

    resposta = client.delete(f"/transacoes/{transacao['id']}", headers=headers)
    assert resposta.status_code == 422


def test_excluir_transacao_de_pagamento_e_permitido_mesmo_com_fatura_fechada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    compra = _criar_transacao(client, headers, conta_id=None, cartao_id=cartao["id"], valor="50.00").json()

    client.post(f"/faturas/{compra['fatura_id']}/fechar", headers=headers)
    resposta_pagamento = client.post(
        f"/faturas/{compra['fatura_id']}/pagamentos",
        json={"valor": "50.00", "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta_pagamento.status_code == 201

    resposta_transacoes = client.get(f"/transacoes?conta_id={conta['id']}", headers=headers)
    pagamento = next(t for t in resposta_transacoes.json() if t["fatura_paga_id"] == compra["fatura_id"])

    resposta_exclusao = client.delete(f"/transacoes/{pagamento['id']}", headers=headers)
    assert resposta_exclusao.status_code == 204


# --- parcelamento_id: duplicidade de numero_parcela (achado da revisão) -----

def test_criar_transacao_com_numero_parcela_ja_usada_no_mesmo_parcelamento_retorna_409(client):
    # achado da revisao tecnica final do CRUD de Parcelamento: sem a
    # checagem em TransacaoService, essa duplicata so era barrada pelo
    # UniqueConstraint do banco - um IntegrityError cru (500), nunca
    # traduzido em resposta HTTP. Ver docs/revisao-tecnica-parcelamento.md.
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = client.post(
        "/parcelamentos",
        json={
            "descricao": "Notebook",
            "valor_total": "1000.00",
            "num_parcelas": 10,
            "data_inicio": "2026-07-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()

    resposta = _criar_transacao(
        client,
        headers,
        conta_id=conta["id"],
        parcelamento_id=parcelamento["id"],
        numero_parcela=1,
    )
    assert resposta.status_code == 409, resposta.text


def test_atualizar_numero_parcela_para_uma_ja_usada_por_outra_transacao_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = client.post(
        "/parcelamentos",
        json={
            "descricao": "Notebook",
            "valor_total": "1000.00",
            "num_parcelas": 10,
            "data_inicio": "2026-07-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()
    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    parcela_2 = next(p for p in parcelas if p["numero_parcela"] == 2)

    resposta = client.patch(
        f"/transacoes/{parcela_2['id']}", json={"numero_parcela": 1}, headers=headers
    )
    assert resposta.status_code == 409, resposta.text
