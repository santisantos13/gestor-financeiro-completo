"""Testes de integração do CRUD de Alerta: TestClient + banco real (SQLite
em memória). Cobre autenticação, isolamento entre usuários, validação de
posse da entidade referenciada, e um caso de avaliação ponta-a-ponta
(LIMITE_CARTAO) para provar que o fluxo real (criar cartão → consumir
limite via Transacao → GET /alertas) dispara de verdade, não só no
isolamento do teste unitário.
"""
from datetime import date


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente", saldo_inicial="1000.00"):
    resposta = client.post("/contas", json={"nome": nome, "saldo_inicial": saldo_inicial}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_cartao(client, headers, conta_id, nome="Nubank", limite="1000.00"):
    payload = {
        "nome": nome,
        "conta_pagamento_id": conta_id,
        "instituicao": "Banco",
        "bandeira": "VISA",
        "ultimos_quatro_digitos": "1234",
        "limite": limite,
        "dia_fechamento": 10,
        "dia_vencimento": 20,
    }
    resposta = client.post("/cartoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_transacao(client, headers, **overrides):
    payload = {
        "tipo": "DESPESA",
        "valor": "50.00",
        "data": str(date.today()),
        "descricao": "Lançamento qualquer",
        "status": "PAGO",
    }
    payload.update(overrides)
    resposta = client.post("/transacoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_alerta(client, headers, **overrides):
    payload = {"tipo": "LIMITE_CARTAO", "condicao": {"limite_percentual": 90}}
    payload.update(overrides)
    return client.post("/alertas", json=payload, headers=headers)


# --- autenticação -------------------------------------------------------------

def test_todas_as_rotas_exigem_autenticacao(client):
    assert client.get("/alertas").status_code == 401
    assert client.post("/alertas", json={}).status_code == 401
    assert client.get("/alertas/1").status_code == 401
    assert client.patch("/alertas/1", json={}).status_code == 401
    assert client.delete("/alertas/1").status_code == 401


# --- criar --------------------------------------------------------------------

def test_criar_alerta_de_limite_cartao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = _criar_alerta(client, headers, entidade_id=cartao["id"])

    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    assert dados["tipo"] == "LIMITE_CARTAO"
    assert dados["ativo"] is True
    assert dados["condicao"] == {"limite_percentual": 90.0}


def test_criar_alerta_para_cartao_de_outro_usuario_da_404(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    headers_b = _registrar_e_logar(client, email="b@example.com")
    conta_b = _criar_conta(client, headers_b)
    cartao_b = _criar_cartao(client, headers_b, conta_b["id"])

    resposta = _criar_alerta(client, headers_a, entidade_id=cartao_b["id"])

    assert resposta.status_code == 404


def test_criar_alerta_limite_cartao_sem_limite_percentual_da_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = _criar_alerta(client, headers, entidade_id=cartao["id"], condicao={})

    assert resposta.status_code == 422


# --- listar / obter -------------------------------------------------------

def test_listar_alertas_filtra_apenas_ativos(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    alerta = _criar_alerta(client, headers, entidade_id=cartao["id"]).json()
    client.patch(f"/alertas/{alerta['id']}", json={"ativo": False}, headers=headers)
    _criar_alerta(client, headers, entidade_id=cartao["id"]).json()

    todos = client.get("/alertas", headers=headers).json()
    ativos = client.get("/alertas", params={"apenas_ativos": True}, headers=headers).json()

    assert len(todos) == 2
    assert len(ativos) == 1


def test_alertas_nao_vazam_entre_usuarios(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    headers_b = _registrar_e_logar(client, email="b@example.com")
    conta_a = _criar_conta(client, headers_a)
    cartao_a = _criar_cartao(client, headers_a, conta_a["id"])
    _criar_alerta(client, headers_a, entidade_id=cartao_a["id"])

    resposta_b = client.get("/alertas", headers=headers_b)

    assert resposta_b.json() == []


def test_obter_alerta_de_outro_usuario_da_404(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    headers_b = _registrar_e_logar(client, email="b@example.com")
    conta_a = _criar_conta(client, headers_a)
    cartao_a = _criar_cartao(client, headers_a, conta_a["id"])
    alerta = _criar_alerta(client, headers_a, entidade_id=cartao_a["id"]).json()

    resposta = client.get(f"/alertas/{alerta['id']}", headers=headers_b)

    assert resposta.status_code == 404


# --- atualizar / excluir ------------------------------------------------------

def test_atualizar_alerta_pausa_e_reativa(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    alerta = _criar_alerta(client, headers, entidade_id=cartao["id"]).json()

    pausado = client.patch(f"/alertas/{alerta['id']}", json={"ativo": False}, headers=headers)
    assert pausado.json()["ativo"] is False
    assert pausado.json()["disparado"] is None

    reativado = client.patch(f"/alertas/{alerta['id']}", json={"ativo": True}, headers=headers)
    assert reativado.json()["ativo"] is True


def test_atualizar_alerta_ignora_tentativa_de_mudar_tipo_ou_entidade_id(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    alerta = _criar_alerta(client, headers, entidade_id=cartao["id"]).json()

    resposta = client.patch(
        f"/alertas/{alerta['id']}", json={"tipo": "SALDO_BAIXO", "entidade_id": 999}, headers=headers
    )

    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "LIMITE_CARTAO"
    assert resposta.json()["entidade_id"] == cartao["id"]


def test_excluir_alerta_remove_definitivamente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    alerta = _criar_alerta(client, headers, entidade_id=cartao["id"]).json()

    resposta = client.delete(f"/alertas/{alerta['id']}", headers=headers)
    assert resposta.status_code == 204

    assert client.get(f"/alertas/{alerta['id']}", headers=headers).status_code == 404


def test_excluir_alerta_de_outro_usuario_da_404(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    headers_b = _registrar_e_logar(client, email="b@example.com")
    conta_a = _criar_conta(client, headers_a)
    cartao_a = _criar_cartao(client, headers_a, conta_a["id"])
    alerta = _criar_alerta(client, headers_a, entidade_id=cartao_a["id"]).json()

    resposta = client.delete(f"/alertas/{alerta['id']}", headers=headers_b)

    assert resposta.status_code == 404


# --- avaliação ponta-a-ponta ---------------------------------------------------

def test_alerta_de_limite_cartao_dispara_apos_consumir_o_limite_via_transacao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="1000.00")
    alerta = _criar_alerta(client, headers, entidade_id=cartao["id"], condicao={"limite_percentual": 50}).json()

    # ainda sem nenhuma compra - não deveria disparar.
    antes = client.get(f"/alertas/{alerta['id']}", headers=headers).json()
    assert antes["disparado"] is False

    # compra de 600 (60% de 1000) via cartão - ultrapassa os 50% configurados.
    _criar_transacao(client, headers, tipo="DESPESA", valor="600.00", cartao_id=cartao["id"])

    depois = client.get(f"/alertas/{alerta['id']}", headers=headers).json()
    assert depois["disparado"] is True
    assert "Nubank" in depois["mensagem"]
