"""Testes de integração do CRUD de Parcelamento: TestClient + banco real
(SQLite em memória). Cobre criação por cartão e por conta (geração eager
de todas as parcelas via TransacaoService/FaturaService reais - não
fakes), listagem de parcelas via `GET /transacoes?parcelamento_id=`,
cancelamento parcial preservando parcelas com fatura já fechada, posse
entre usuários, validação estrutural, ausência de PATCH/DELETE físico e
`valor_parcela` customizado (compra com juros embutidos pela loja, onde a
parcela real não é `valor_total / num_parcelas`).
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


def _criar_parcelamento(client, headers, **overrides):
    payload = {
        "descricao": "Notebook",
        "valor_total": "1000.00",
        "num_parcelas": 10,
        "data_inicio": "2026-07-15",
    }
    payload.update(overrides)
    payload = {chave: valor for chave, valor in payload.items() if valor is not None}
    return client.post("/parcelamentos", json=payload, headers=headers)


# --- autenticação / estrutura -----------------------------------------------

def test_criar_parcelamento_sem_autenticacao_retorna_401(client):
    resposta = client.post(
        "/parcelamentos",
        json={"descricao": "x", "valor_total": "10.00", "num_parcelas": 2, "data_inicio": "2026-07-15", "conta_id": 1},
    )
    assert resposta.status_code == 401


def test_criar_parcelamento_sem_cartao_e_sem_conta_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = _criar_parcelamento(client, headers)
    assert resposta.status_code == 422


def test_criar_parcelamento_com_cartao_e_conta_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    resposta = _criar_parcelamento(client, headers, conta_id=conta["id"], cartao_id=cartao["id"])
    assert resposta.status_code == 422


def test_criar_parcelamento_com_apenas_uma_parcela_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_parcelamento(client, headers, conta_id=conta["id"], num_parcelas=1)
    assert resposta.status_code == 422


# --- criação por conta: geração eager de todas as parcelas ------------------

def test_criar_parcelamento_de_conta_gera_todas_as_parcelas_imediatamente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    resposta = _criar_parcelamento(
        client, headers, conta_id=conta["id"], valor_total="1000.00", num_parcelas=10, data_inicio="2026-07-15"
    )
    assert resposta.status_code == 201, resposta.text
    parcelamento = resposta.json()
    assert parcelamento["ativo"] is True
    assert parcelamento["conta_id"] == conta["id"]
    assert parcelamento["cartao_id"] is None

    resposta_parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers)
    assert resposta_parcelas.status_code == 200
    parcelas = resposta_parcelas.json()
    assert len(parcelas) == 10
    assert sum(float(p["valor"]) for p in parcelas) == 1000.00
    assert sorted(p["numero_parcela"] for p in parcelas) == list(range(1, 11))
    assert all(p["tipo"] == "DESPESA" for p in parcelas)
    assert all(p["conta_id"] == conta["id"] for p in parcelas)


def test_criar_parcelamento_de_conta_datas_avancam_um_mes_por_parcela(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    parcelamento = _criar_parcelamento(
        client, headers, conta_id=conta["id"], num_parcelas=3, data_inicio="2026-11-30"
    ).json()

    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    datas = {p["numero_parcela"]: p["data"] for p in parcelas}
    # nov/2026 (dia 30) -> dez/2026 (dia 30) -> jan/2027 (dia 30): rollover de ano.
    assert datas[1] == "2026-11-30"
    assert datas[2] == "2026-12-30"
    assert datas[3] == "2027-01-30"


# --- criação por cartão: cada parcela cai na fatura do próprio ciclo -------

def test_criar_parcelamento_de_cartao_distribui_parcelas_entre_faturas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    parcelamento = _criar_parcelamento(
        client, headers, cartao_id=cartao["id"], conta_id=None, num_parcelas=3, data_inicio="2026-07-15"
    ).json()
    assert parcelamento["cartao_id"] == cartao["id"]

    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    assert len(parcelas) == 3
    assert all(p["status"] == "PAGO" for p in parcelas)  # status de cartao e sempre forcado
    faturas_das_parcelas = {p["fatura_id"] for p in parcelas}
    assert len(faturas_das_parcelas) == 3  # cada parcela cai num ciclo/fatura diferente

    resposta_faturas = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers)
    assert len(resposta_faturas.json()) == 3


# --- valor_parcela customizado (juros embutidos pela loja) -----------------

def test_criar_parcelamento_com_valor_parcela_usa_o_valor_informado_em_todas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    parcelamento = _criar_parcelamento(
        client,
        headers,
        conta_id=conta["id"],
        valor_total="1000.00",
        num_parcelas=10,
        valor_parcela="105.00",
        data_inicio="2026-07-15",
    ).json()

    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    assert len(parcelas) == 10
    assert all(p["valor"] == "105.00" for p in parcelas)
    # soma não bate com valor_total de propósito - o valor de referência da
    # compra e o valor realmente cobrado por parcela (com juros) são coisas
    # diferentes aqui.
    assert sum(float(p["valor"]) for p in parcelas) == 1050.00


def test_criar_parcelamento_sem_valor_parcela_mantem_divisao_padrao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    parcelamento = _criar_parcelamento(
        client, headers, conta_id=conta["id"], valor_total="1000.00", num_parcelas=10
    ).json()

    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    assert all(p["valor"] == "100.00" for p in parcelas)


# --- posse ------------------------------------------------------------------

def test_criar_parcelamento_com_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)

    resposta = _criar_parcelamento(client, headers_ana, conta_id=conta_bruno["id"])
    assert resposta.status_code == 404


def test_obter_parcelamento_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    parcelamento = _criar_parcelamento(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.get(f"/parcelamentos/{parcelamento['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_listar_parcelamentos_retorna_apenas_os_do_usuario(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_bruno = _criar_conta(client, headers_bruno)
    _criar_parcelamento(client, headers_ana, conta_id=conta_ana["id"], descricao="Da Ana")
    _criar_parcelamento(client, headers_bruno, conta_id=conta_bruno["id"], descricao="Do Bruno")

    resposta = client.get("/parcelamentos", headers=headers_ana)
    assert resposta.status_code == 200
    parcelamentos = resposta.json()
    assert len(parcelamentos) == 1
    assert parcelamentos[0]["descricao"] == "Da Ana"


# --- sem PATCH genérico e sem DELETE físico ---------------------------------

def test_parcelamento_nao_tem_patch_generico(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = _criar_parcelamento(client, headers, conta_id=conta["id"]).json()

    resposta = client.patch(f"/parcelamentos/{parcelamento['id']}", json={"descricao": "Outro"}, headers=headers)
    assert resposta.status_code == 405


def test_parcelamento_nao_tem_delete_fisico(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = _criar_parcelamento(client, headers, conta_id=conta["id"]).json()

    resposta = client.delete(f"/parcelamentos/{parcelamento['id']}", headers=headers)
    assert resposta.status_code == 405


# --- cancelar ----------------------------------------------------------------

def test_cancelar_parcelamento_de_conta_marca_inativo_e_remove_parcelas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = _criar_parcelamento(client, headers, conta_id=conta["id"], num_parcelas=3).json()

    resposta = client.post(f"/parcelamentos/{parcelamento['id']}/cancelar", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert parcelas_restantes == []


def test_cancelar_parcelamento_de_cartao_preserva_parcelas_com_fatura_fechada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    parcelamento = _criar_parcelamento(
        client, headers, cartao_id=cartao["id"], conta_id=None, num_parcelas=3, data_inicio="2026-07-15"
    ).json()
    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    primeira_parcela = next(p for p in parcelas if p["numero_parcela"] == 1)

    # fecha soh a fatura da primeira parcela - as outras duas (ciclos
    # futuros) continuam abertas.
    client.post(f"/faturas/{primeira_parcela['fatura_id']}/fechar", headers=headers)

    resposta_cancelar = client.post(f"/parcelamentos/{parcelamento['id']}/cancelar", headers=headers)
    assert resposta_cancelar.status_code == 200
    assert resposta_cancelar.json()["ativo"] is False

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    # so a parcela travada (fatura fechada) sobrevive ao cancelamento -
    # historico preservado, o resto foi removido.
    assert len(parcelas_restantes) == 1
    assert parcelas_restantes[0]["numero_parcela"] == 1


def test_excluir_uma_parcela_pelo_endpoint_generico_de_transacao_cancela_o_parcelamento_inteiro(client):
    """Bug real reportado pelo usuário em 2026-07-20: excluir uma única
    parcela de uma compra parcelada no cartão via `DELETE /transacoes/{id}`
    (o único jeito que a UI oferece hoje - não há tela dedicada de
    'cancelar parcelamento') atualizava a fatura do mês corrente (SUM ao
    vivo) mas deixava as OUTRAS parcelas - inclusive as de faturas futuras
    já resolvidas na criação - completamente intocadas, e o parcelamento
    continuava ativo. Mesmo cenário de
    `test_cancelar_parcelamento_de_conta_marca_inativo_e_remove_parcelas`,
    mas disparado pelo delete genérico de UMA parcela em vez da ação
    dedicada `/parcelamentos/{id}/cancelar`."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    parcelamento = _criar_parcelamento(
        client, headers, cartao_id=cartao["id"], conta_id=None, num_parcelas=3, data_inicio="2026-07-15"
    ).json()
    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    assert len(parcelas) == 3
    parcela_do_meio = next(p for p in parcelas if p["numero_parcela"] == 2)

    resposta = client.delete(f"/transacoes/{parcela_do_meio['id']}", headers=headers)
    assert resposta.status_code == 204

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert parcelas_restantes == []  # as 3, não só a clicada

    todos = client.get("/parcelamentos?apenas_ativos=false", headers=headers).json()
    assert next(p for p in todos if p["id"] == parcelamento["id"])["ativo"] is False


def test_excluir_uma_parcela_pelo_endpoint_generico_preserva_a_que_ja_esta_em_fatura_fechada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)
    parcelamento = _criar_parcelamento(
        client, headers, cartao_id=cartao["id"], conta_id=None, num_parcelas=3, data_inicio="2026-07-15"
    ).json()
    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    primeira_parcela = next(p for p in parcelas if p["numero_parcela"] == 1)
    terceira_parcela = next(p for p in parcelas if p["numero_parcela"] == 3)

    # fecha só a fatura da primeira parcela - as outras duas continuam em
    # ciclos abertos.
    client.post(f"/faturas/{primeira_parcela['fatura_id']}/fechar", headers=headers)

    # exclui a TERCEIRA parcela (destravada) pelo endpoint genérico -
    # cascateia para cancelar o parcelamento inteiro, preservando só a
    # primeira (travada, já é passado).
    resposta = client.delete(f"/transacoes/{terceira_parcela['id']}", headers=headers)
    assert resposta.status_code == 204

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert len(parcelas_restantes) == 1
    assert parcelas_restantes[0]["numero_parcela"] == 1

    todos = client.get("/parcelamentos?apenas_ativos=false", headers=headers).json()
    assert next(p for p in todos if p["id"] == parcelamento["id"])["ativo"] is False


def test_excluir_a_parcela_clicada_com_fatura_fechada_ainda_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)
    parcelamento = _criar_parcelamento(
        client, headers, cartao_id=cartao["id"], conta_id=None, num_parcelas=2, data_inicio="2026-07-15"
    ).json()
    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    primeira_parcela = next(p for p in parcelas if p["numero_parcela"] == 1)
    client.post(f"/faturas/{primeira_parcela['fatura_id']}/fechar", headers=headers)

    # a trava de "não mexe em fatura fechada" continua valendo para a
    # transação efetivamente clicada - só as parcelas IRMÃS destravadas são
    # canceladas em cascata quando a exclusão é permitida.
    resposta = client.delete(f"/transacoes/{primeira_parcela['id']}", headers=headers)
    assert resposta.status_code == 422

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert len(parcelas_restantes) == 2  # nada foi excluído


def test_cancelar_parcelamento_ja_cancelado_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = _criar_parcelamento(client, headers, conta_id=conta["id"]).json()
    client.post(f"/parcelamentos/{parcelamento['id']}/cancelar", headers=headers)

    resposta = client.post(f"/parcelamentos/{parcelamento['id']}/cancelar", headers=headers)
    assert resposta.status_code == 422


def test_cancelar_parcelamento_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    parcelamento = _criar_parcelamento(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.post(f"/parcelamentos/{parcelamento['id']}/cancelar", headers=headers_bruno)
    assert resposta.status_code == 404


def test_parcelamento_cancelado_some_da_listagem_padrao_mas_aparece_com_apenas_ativos_false(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = _criar_parcelamento(client, headers, conta_id=conta["id"]).json()
    client.post(f"/parcelamentos/{parcelamento['id']}/cancelar", headers=headers)

    resposta_padrao = client.get("/parcelamentos", headers=headers)
    assert resposta_padrao.json() == []

    resposta_todos = client.get("/parcelamentos?apenas_ativos=false", headers=headers)
    assert len(resposta_todos.json()) == 1


# --- integração com limite de Cartão (Refinamento de Limite/Parcelamento) --


def test_excluir_parcela_de_compra_de_12_parcelas_cancela_todas_e_libera_limite_do_cartao(client):
    """Cenário explícito de validação pedido pelo usuário: compra parcelada
    em 12x, todas em ciclos ainda ABERTOS (nenhuma fatura fechada) -
    excluir UMA parcela precisa cancelar as 12 e devolver o limite inteiro
    consumido por elas, não só o valor da parcela clicada."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])  # limite 5000.00

    parcelamento = _criar_parcelamento(
        client,
        headers,
        cartao_id=cartao["id"],
        conta_id=None,
        valor_total="2400.00",
        num_parcelas=12,
        data_inicio="2026-07-15",
    ).json()

    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()
    assert len(parcelas) == 12

    # as 12 parcelas de R$200 já consomem limite de imediato - nenhuma
    # fatura fechada ainda, todos os ciclos resolvidos nascem ABERTOS.
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "2600.00"

    parcela_do_meio = next(p for p in parcelas if p["numero_parcela"] == 6)
    resposta = client.delete(f"/transacoes/{parcela_do_meio['id']}", headers=headers)
    assert resposta.status_code == 204

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert parcelas_restantes == []
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "5000.00"

    parcelamento_atualizado = client.get(f"/parcelamentos/{parcelamento['id']}", headers=headers).json()
    assert parcelamento_atualizado["ativo"] is False


def test_parcelamento_totalmente_pago_bloqueia_exclusao_de_qualquer_parcela(client):
    """Parcelamento de 2 parcelas cujas DUAS faturas já foram fechadas E
    pagas por completo - tentar excluir qualquer uma das duas (não só a
    "clicada" de um teste anterior) precisa continuar bloqueada com 422,
    sem remover nada nem mexer no parcelamento, mesmo com o parcelamento
    inteiro já quitado."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    parcelamento = _criar_parcelamento(
        client,
        headers,
        cartao_id=cartao["id"],
        conta_id=None,
        valor_total="600.00",
        num_parcelas=2,
        data_inicio="2026-07-15",
    ).json()
    parcelas = client.get(f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers).json()

    for parcela in parcelas:
        fatura_id = parcela["fatura_id"]
        fechada = client.post(f"/faturas/{fatura_id}/fechar", headers=headers)
        if fechada.status_code == 200:
            valor_total = fechada.json()["valor_total"]
            client.post(
                f"/faturas/{fatura_id}/pagamentos",
                json={"valor": valor_total, "data": "2026-08-01", "descricao": "Pagamento"},
                headers=headers,
            )

    for parcela in parcelas:
        fatura = client.get(f"/faturas/{parcela['fatura_id']}", headers=headers).json()
        assert fatura["status"] == "PAGA"

    for parcela in parcelas:
        resposta = client.delete(f"/transacoes/{parcela['id']}", headers=headers)
        assert resposta.status_code == 422

    parcelas_restantes = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert len(parcelas_restantes) == 2

    parcelamento_atualizado = client.get(f"/parcelamentos/{parcelamento['id']}", headers=headers).json()
    assert parcelamento_atualizado["ativo"] is True


def test_obter_parcelamento_retorna_num_parcelas_usado_pela_confirmacao_de_exclusao(client):
    """`GET /parcelamentos/{id}` é a fonte usada pelo novo diálogo de
    confirmação do frontend ("Esta compra possui N parcelas...", ver
    docs/analise-arquitetural-escopo-parcelamento.md, seção 4) - garante
    que `num_parcelas` sempre volta correto, não só na criação."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    parcelamento = _criar_parcelamento(client, headers, conta_id=conta["id"], num_parcelas=7).json()

    resposta = client.get(f"/parcelamentos/{parcelamento['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["num_parcelas"] == 7
