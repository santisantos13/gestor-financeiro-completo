"""Testes de integração do CRUD de Emprestimo: TestClient + banco real
(SQLite em memória). Cobre criação com geração eager do cronograma de
amortização (PRICE/SAC) via TransacaoService real - não fakes -, o
desembolso sempre gerado como Transacao de RECEITA avulsa, pagamento de
parcela via a ação dedicada (atualizando saldo_devedor e, na última
parcela, o status do contrato), bloqueio de `PATCH /transacoes/{id}` para
status de parcela de empréstimo, posse entre usuários, validação
estrutural, ausência de PATCH físico no próprio Emprestimo e
`DELETE /emprestimos/{id}` (sempre permitido, mesmo com parcelas já pagas -
as parcelas/desembolso só perdem o vínculo, `ondelete=SET NULL`). Ver
docs/analise-arquitetural-emprestimo.md.
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


def _criar_emprestimo(client, headers, **overrides):
    payload = {
        "descricao": "Empréstimo pessoal",
        "instituicao_financeira": "Banco X",
        "valor_liberado": "10000.00",
        "taxa_juros": "0.0150",
        "sistema_amortizacao": "PRICE",
        "num_parcelas": 12,
        "data_inicio": "2026-07-15",
    }
    payload.update(overrides)
    payload = {chave: valor for chave, valor in payload.items() if valor is not None}
    return client.post("/emprestimos", json=payload, headers=headers)


# --- autenticação / estrutura -----------------------------------------------

def test_criar_emprestimo_sem_autenticacao_retorna_401(client):
    resposta = client.post(
        "/emprestimos",
        json={
            "descricao": "x",
            "instituicao_financeira": "Banco X",
            "valor_liberado": "1000.00",
            "taxa_juros": "0.01",
            "num_parcelas": 2,
            "data_inicio": "2026-07-15",
            "conta_id": 1,
        },
    )
    assert resposta.status_code == 401


def test_criar_emprestimo_sem_conta_id_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = _criar_emprestimo(client, headers)
    assert resposta.status_code == 422


def test_criar_emprestimo_com_uma_unica_parcela_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_emprestimo(client, headers, conta_id=conta["id"], num_parcelas=1)
    assert resposta.status_code == 422


def test_criar_emprestimo_sem_valor_liberado_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/emprestimos",
        json={
            "descricao": "Empréstimo",
            "instituicao_financeira": "Banco X",
            "taxa_juros": "0.01",
            "num_parcelas": 5,
            "data_inicio": "2026-07-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    )
    assert resposta.status_code == 422


# --- criação: geração eager do cronograma via TransacaoService real --------

def test_criar_emprestimo_gera_todas_as_parcelas_imediatamente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    resposta = _criar_emprestimo(
        client,
        headers,
        conta_id=conta["id"],
        valor_liberado="100000.00",
        taxa_juros="0.0150",
        sistema_amortizacao="PRICE",
        num_parcelas=24,
    )
    assert resposta.status_code == 201, resposta.text
    emprestimo = resposta.json()
    assert emprestimo["status"] == "ATIVO"
    assert emprestimo["saldo_devedor"] == "100000.00"
    assert emprestimo["conta_id"] == conta["id"]

    resposta_parcelas = client.get(
        f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers
    )
    assert resposta_parcelas.status_code == 200
    parcelas = resposta_parcelas.json()
    assert len(parcelas) == 24
    assert sorted(p["numero_parcela"] for p in parcelas) == list(range(1, 25))
    assert all(p["tipo"] == "DESPESA" for p in parcelas)
    assert all(p["conta_id"] == conta["id"] for p in parcelas)
    assert all(p["status"] == "PENDENTE" for p in parcelas)


def test_criar_emprestimo_price_gera_parcelas_de_valor_fixo(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client,
        headers,
        conta_id=conta["id"],
        sistema_amortizacao="PRICE",
        num_parcelas=12,
    ).json()

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    valores = sorted((p["numero_parcela"], p["valor"]) for p in parcelas)
    valores_sem_ultima = [v for numero, v in valores if numero != 12]
    assert len(set(valores_sem_ultima)) == 1


def test_criar_emprestimo_sac_gera_parcelas_decrescentes(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client,
        headers,
        conta_id=conta["id"],
        sistema_amortizacao="SAC",
        num_parcelas=12,
    ).json()

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    valores_por_numero = {p["numero_parcela"]: float(p["valor"]) for p in parcelas}
    valores_ordenados = [valores_por_numero[n] for n in range(1, 13)]
    assert all(valores_ordenados[i] > valores_ordenados[i + 1] for i in range(len(valores_ordenados) - 1))


def test_criar_emprestimo_datas_avancam_um_mes_por_parcela(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client, headers, conta_id=conta["id"], num_parcelas=3, data_inicio="2026-11-30"
    ).json()

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    datas = {p["numero_parcela"]: p["data"] for p in parcelas}
    assert datas[1] == "2026-11-30"
    assert datas[2] == "2026-12-30"
    assert datas[3] == "2027-01-30"


# --- criação: desembolso sempre gerado (RECEITA avulsa) ---------------------

def test_criar_emprestimo_gera_desembolso_como_transacao_de_receita_avulsa(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client,
        headers,
        conta_id=conta["id"],
        valor_liberado="15000.00",
        num_parcelas=12,
    ).json()
    # diferente de Financiamento (entrada opcional, DESPESA): aqui o
    # desembolso e SEMPRE gerado e e uma RECEITA.
    assert emprestimo["saldo_devedor"] == "15000.00"

    todas_transacoes = client.get("/transacoes", headers=headers).json()
    desembolso = [t for t in todas_transacoes if t["emprestimo_id"] is None and t["tipo"] == "RECEITA"]
    assert len(desembolso) == 1
    assert desembolso[0]["valor"] == "15000.00"
    assert "Desembolso" in desembolso[0]["descricao"]
    assert desembolso[0]["numero_parcela"] is None

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    assert len(parcelas) == 12  # so as parcelas, desembolso nao entra nessa contagem


# --- posse -------------------------------------------------------------------

def test_obter_emprestimo_de_outro_usuario_retorna_404(client):
    headers1 = _registrar_e_logar(client, email="ana@example.com")
    conta1 = _criar_conta(client, headers1)
    emprestimo = _criar_emprestimo(client, headers1, conta_id=conta1["id"]).json()

    headers2 = _registrar_e_logar(client, email="bob@example.com")
    resposta = client.get(f"/emprestimos/{emprestimo['id']}", headers=headers2)
    assert resposta.status_code == 404


def test_listar_emprestimos_retorna_apenas_do_usuario_autenticado(client):
    headers1 = _registrar_e_logar(client, email="ana@example.com")
    conta1 = _criar_conta(client, headers1)
    _criar_emprestimo(client, headers1, conta_id=conta1["id"], descricao="Da Ana")

    headers2 = _registrar_e_logar(client, email="bob@example.com")
    conta2 = _criar_conta(client, headers2)
    _criar_emprestimo(client, headers2, conta_id=conta2["id"], descricao="Do Bob")

    resposta = client.get("/emprestimos", headers=headers1)
    assert resposta.status_code == 200
    descricoes = [e["descricao"] for e in resposta.json()]
    assert descricoes == ["Da Ana"]


# --- excluir -----------------------------------------------------------------

def test_excluir_emprestimo_retorna_204(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(client, headers, conta_id=conta["id"]).json()

    resposta = client.delete(f"/emprestimos/{emprestimo['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_obter = client.get(f"/emprestimos/{emprestimo['id']}", headers=headers)
    assert resposta_obter.status_code == 404


def test_excluir_emprestimo_com_parcela_paga_e_permitido_e_desvincula_transacao(client):
    """Decisão do usuário: exclusão sempre permitida. As Transacoes de
    parcela/desembolso não são apagadas - só perdem o vínculo
    (emprestimo_id vira None, ondelete=SET NULL)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client, headers, conta_id=conta["id"], num_parcelas=2, taxa_juros="0"
    ).json()
    client.post(f"/emprestimos/{emprestimo['id']}/parcelas/1/pagar", headers=headers)

    resposta = client.delete(f"/emprestimos/{emprestimo['id']}", headers=headers)
    assert resposta.status_code == 204

    transacoes = client.get(
        "/transacoes", params={"conta_id": conta["id"], "limit": 10}, headers=headers
    ).json()
    # 2 parcelas + 1 desembolso, todas desvinculadas.
    assert len(transacoes) == 3
    assert all(t["emprestimo_id"] is None for t in transacoes)


def test_excluir_emprestimo_de_outro_usuario_retorna_404(client):
    headers1 = _registrar_e_logar(client, email="ana@example.com")
    conta1 = _criar_conta(client, headers1)
    emprestimo = _criar_emprestimo(client, headers1, conta_id=conta1["id"]).json()

    headers2 = _registrar_e_logar(client, email="bob@example.com")
    resposta = client.delete(f"/emprestimos/{emprestimo['id']}", headers=headers2)
    assert resposta.status_code == 404


def test_excluir_emprestimo_sem_autenticacao_retorna_401(client):
    resposta = client.delete("/emprestimos/1")
    assert resposta.status_code == 401


# --- pagar_parcela: ação dedicada --------------------------------------------

def test_pagar_parcela_marca_transacao_como_paga_e_decrementa_saldo_devedor(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client, headers, conta_id=conta["id"], valor_liberado="300.00", taxa_juros="0", num_parcelas=3
    ).json()
    assert emprestimo["saldo_devedor"] == "300.00"

    resposta = client.post(f"/emprestimos/{emprestimo['id']}/parcelas/1/pagar", headers=headers)
    assert resposta.status_code == 200, resposta.text
    atualizado = resposta.json()
    assert atualizado["saldo_devedor"] == "200.00"
    assert atualizado["status"] == "ATIVO"

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    parcela_1 = next(p for p in parcelas if p["numero_parcela"] == 1)
    assert parcela_1["status"] == "PAGO"


def test_pagar_ultima_parcela_quita_o_contrato(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client, headers, conta_id=conta["id"], valor_liberado="300.00", taxa_juros="0", num_parcelas=3
    ).json()

    for numero_parcela in (1, 2, 3):
        resposta = client.post(
            f"/emprestimos/{emprestimo['id']}/parcelas/{numero_parcela}/pagar", headers=headers
        )
        assert resposta.status_code == 200, resposta.text

    emprestimo_final = client.get(f"/emprestimos/{emprestimo['id']}", headers=headers).json()
    assert emprestimo_final["saldo_devedor"] == "0.00"
    assert emprestimo_final["status"] == "QUITADO"


# --- parcelas_ja_pagas (Etapa de Onboarding) ---------------------------------

def test_criar_emprestimo_com_parcelas_ja_pagas_decrementa_saldo_devedor(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client,
        headers,
        conta_id=conta["id"],
        valor_liberado="300.00",
        taxa_juros="0",
        num_parcelas=3,
        parcelas_ja_pagas=1,
    ).json()
    assert emprestimo["saldo_devedor"] == "200.00"

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    parcela_1 = next(p for p in parcelas if p["numero_parcela"] == 1)
    parcela_2 = next(p for p in parcelas if p["numero_parcela"] == 2)
    assert parcela_1["status"] == "PAGO"
    assert parcela_2["status"] == "PENDENTE"


def test_criar_emprestimo_com_parcelas_ja_pagas_marca_parcela_como_importada(client):
    """Espelha o teste equivalente de Financiamento - instrução explícita do
    usuário: "deixe por conta do usuário decidir se ele tá com saldo
    negativo ou não, evite deduções com base em informações resgatadas do
    passado financeiro antes do uso do app". `importada` marca só a parcela
    do onboarding, nunca o desembolso (`_gerar_transacao_de_desembolso`) -
    achado ao investigar: o desembolso nasce PENDENTE (`TransacaoCreate` sem
    `status` explícito, mesmo comportamento padrão de qualquer transação de
    Conta, nada alterado nesta correção), então nem ele entra na soma de
    `somar_transacoes_pagas` ainda - saldo_atual fica em 0.00 até o usuário
    confirmar o recebimento marcando essa transação como PAGO."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(
        client,
        headers,
        conta_id=conta["id"],
        valor_liberado="300.00",
        taxa_juros="0",
        num_parcelas=3,
        parcelas_ja_pagas=1,
    ).json()

    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    parcela_1 = next(p for p in parcelas if p["numero_parcela"] == 1)
    parcela_2 = next(p for p in parcelas if p["numero_parcela"] == 2)
    assert parcela_1["importada"] is True
    assert parcela_2["importada"] is False

    conta_atualizada = client.get(f"/contas/{conta['id']}", headers=headers).json()
    assert conta_atualizada["saldo_atual"] == "0.00"


def test_criar_emprestimo_com_parcelas_ja_pagas_maior_que_num_parcelas_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_emprestimo(
        client, headers, conta_id=conta["id"], num_parcelas=3, parcelas_ja_pagas=4
    )
    assert resposta.status_code == 422


def test_pagar_parcela_numero_fora_da_faixa_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(client, headers, conta_id=conta["id"], num_parcelas=5).json()

    resposta = client.post(f"/emprestimos/{emprestimo['id']}/parcelas/6/pagar", headers=headers)
    assert resposta.status_code == 422


def test_pagar_a_mesma_parcela_duas_vezes_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(client, headers, conta_id=conta["id"], num_parcelas=5).json()

    primeira = client.post(f"/emprestimos/{emprestimo['id']}/parcelas/1/pagar", headers=headers)
    assert primeira.status_code == 200

    segunda = client.post(f"/emprestimos/{emprestimo['id']}/parcelas/1/pagar", headers=headers)
    assert segunda.status_code == 422


def test_pagar_parcela_de_emprestimo_de_outro_usuario_retorna_404(client):
    headers1 = _registrar_e_logar(client, email="ana@example.com")
    conta1 = _criar_conta(client, headers1)
    emprestimo = _criar_emprestimo(client, headers1, conta_id=conta1["id"]).json()

    headers2 = _registrar_e_logar(client, email="bob@example.com")
    resposta = client.post(
        f"/emprestimos/{emprestimo['id']}/parcelas/1/pagar", headers=headers2
    )
    assert resposta.status_code == 404


# --- bloqueio de PATCH genérico para status de parcela de empréstimo -------

def test_patch_status_de_parcela_de_emprestimo_via_transacoes_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(client, headers, conta_id=conta["id"], num_parcelas=5).json()
    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    parcela_1 = next(p for p in parcelas if p["numero_parcela"] == 1)

    resposta = client.patch(
        f"/transacoes/{parcela_1['id']}", json={"status": "PAGO"}, headers=headers
    )
    assert resposta.status_code == 422

    # confirma que o saldo_devedor tambem nao mudou - a protecao funcionou.
    emprestimo_inalterado = client.get(f"/emprestimos/{emprestimo['id']}", headers=headers).json()
    assert emprestimo_inalterado["saldo_devedor"] == emprestimo["saldo_devedor"]


def test_patch_outros_campos_de_parcela_de_emprestimo_continua_permitido(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(client, headers, conta_id=conta["id"], num_parcelas=5).json()
    parcelas = client.get(f"/transacoes?emprestimo_id={emprestimo['id']}", headers=headers).json()
    parcela_1 = next(p for p in parcelas if p["numero_parcela"] == 1)

    resposta = client.patch(
        f"/transacoes/{parcela_1['id']}", json={"descricao": "Renomeada"}, headers=headers
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["descricao"] == "Renomeada"


# --- posse cruzada ao vincular emprestimo_id manualmente via /transacoes ---

def test_criar_transacao_manual_com_emprestimo_de_outro_usuario_retorna_404(client):
    headers1 = _registrar_e_logar(client, email="ana@example.com")
    conta1 = _criar_conta(client, headers1)
    emprestimo = _criar_emprestimo(client, headers1, conta_id=conta1["id"], num_parcelas=5).json()

    headers2 = _registrar_e_logar(client, email="bob@example.com")
    conta2 = _criar_conta(client, headers2)
    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Tentativa indevida",
            "conta_id": conta2["id"],
            "emprestimo_id": emprestimo["id"],
            "numero_parcela": 99,
        },
        headers=headers2,
    )
    assert resposta.status_code == 404


def test_criar_transacao_manual_com_numero_parcela_ja_usado_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    emprestimo = _criar_emprestimo(client, headers, conta_id=conta["id"], num_parcelas=5).json()

    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Duplicata",
            "conta_id": conta["id"],
            "emprestimo_id": emprestimo["id"],
            "numero_parcela": 1,
        },
        headers=headers,
    )
    assert resposta.status_code == 409

