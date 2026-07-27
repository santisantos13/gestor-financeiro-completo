"""Testes de integração de Relatórios: TestClient + banco real (SQLite).
Cobre autenticação obrigatória e um caso ponta-a-ponta real (cria conta +
transação de despesa, confirma que o CSV/PDF exportado reflete os dados
via `GET /relatorios/csv` e `GET /relatorios/pdf`, os mesmos endpoints que
o frontend chama)."""
from datetime import date


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente"):
    resposta = client.post("/contas", json={"nome": nome, "saldo_inicial": "1000.00"}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_transacao(client, headers, conta_id, **overrides):
    payload = {
        "tipo": "DESPESA",
        "valor": "150.00",
        "data": str(date.today()),
        "descricao": "Mercado",
        "status": "PAGO",
        "conta_id": conta_id,
    }
    payload.update(overrides)
    resposta = client.post("/transacoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_csv_e_pdf_exigem_autenticacao(client):
    assert client.get("/relatorios/csv").status_code == 401
    assert client.get("/relatorios/pdf").status_code == 401


def test_csv_de_um_periodo_sem_nenhum_dado_nao_quebra(client):
    headers = _registrar_e_logar(client)

    resposta = client.get("/relatorios/csv", params={"ano": 2020, "mes": 1}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/csv")
    assert 'filename="relatorio-2020-01.csv"' in resposta.headers["content-disposition"]
    assert "Entradas;0" in resposta.text
    assert "Saídas;0" in resposta.text


def test_pdf_de_um_periodo_sem_nenhum_dado_nao_quebra(client):
    headers = _registrar_e_logar(client)

    resposta = client.get("/relatorios/pdf", params={"ano": 2020, "mes": 1}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "application/pdf"
    assert 'filename="relatorio-2020-01.pdf"' in resposta.headers["content-disposition"]
    assert resposta.content.startswith(b"%PDF")


def test_csv_reflete_uma_despesa_real_lancada_na_conta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    hoje = date.today()
    _criar_transacao(client, headers, conta["id"], valor="150.00", descricao="Mercado")

    resposta = client.get("/relatorios/csv", params={"ano": hoje.year, "mes": hoje.month}, headers=headers)

    assert resposta.status_code == 200
    assert "Saídas;150.00" in resposta.text
    assert "Conta Corrente;150.00" in resposta.text


def test_isolamento_entre_usuarios(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bia = _registrar_e_logar(client, email="bia@example.com")
    conta_ana = _criar_conta(client, headers_ana, nome="Conta da Ana")
    hoje = date.today()
    _criar_transacao(client, headers_ana, conta_ana["id"], valor="300.00")

    resposta_bia = client.get(
        "/relatorios/csv", params={"ano": hoje.year, "mes": hoje.month}, headers=headers_bia
    )

    assert resposta_bia.status_code == 200
    assert "Saídas;0" in resposta_bia.text
    assert "Conta da Ana" not in resposta_bia.text


def test_ano_mes_omitidos_usa_mes_atual(client):
    headers = _registrar_e_logar(client)
    hoje = date.today()

    resposta = client.get("/relatorios/csv", headers=headers)

    assert resposta.status_code == 200
    assert f'filename="relatorio-{hoje.year:04d}-{hoje.month:02d}.csv"' in resposta.headers["content-disposition"]
