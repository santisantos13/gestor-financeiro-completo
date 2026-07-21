"""Teste de integração ponta-a-ponta: sobe a aplicação FastAPI real (com o
banco de teste no lugar do banco real) e faz uma requisição HTTP de
verdade via TestClient - prova que o wiring inteiro (main.py, routers,
middlewares) continua funcionando depois das mudanças de arquitetura desta
etapa.
"""


def test_healthcheck_retorna_ok(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
