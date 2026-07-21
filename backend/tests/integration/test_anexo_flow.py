"""Testes de integração do CRUD de Anexo: TestClient + banco real (SQLite
em memória). Cobre a regra de domínio central desta entidade - posse SEMPRE
transitiva via Transacao, nunca direta ao usuário (ver
docs/analise-arquitetural-anexo.md) - isolamento entre usuários, soft
delete via HTTP real, o cascade físico quando a Transacao dona é excluída
(hard delete, sem soft delete em Transacao), e a ausência deliberada de
PATCH (decisão confirmada explicitamente com o usuário antes da
implementação).
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


def _criar_transacao(client, headers, conta_id, **overrides):
    payload = {
        "tipo": "DESPESA",
        "valor": "50.00",
        "data": "2026-07-15",
        "descricao": "Compra qualquer",
        "status": "PAGO",
        "conta_id": conta_id,
    }
    payload.update(overrides)
    resposta = client.post("/transacoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _payload_anexo(transacao_id, **overrides):
    payload = {
        "transacao_id": transacao_id,
        "nome_original": "comprovante.pdf",
        "caminho_arquivo": "/uploads/comprovante.pdf",
        "mime_type": "application/pdf",
        "tamanho_bytes": 2048,
    }
    payload.update(overrides)
    return payload


def _criar_anexo(client, headers, transacao_id, **overrides):
    resposta = client.post("/anexos", json=_payload_anexo(transacao_id, **overrides), headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --- autenticação / estrutura -----------------------------------------------

def test_criar_anexo_sem_autenticacao_retorna_401(client):
    resposta = client.post("/anexos", json=_payload_anexo(1))
    assert resposta.status_code == 401


def test_listar_anexos_sem_autenticacao_retorna_401(client):
    resposta = client.get("/anexos", params={"transacao_id": 1})
    assert resposta.status_code == 401


# --- criar -------------------------------------------------------------

def test_criar_e_obter_anexo(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])

    anexo = _criar_anexo(client, headers, transacao["id"])
    assert anexo["transacao_id"] == transacao["id"]
    assert anexo["nome_original"] == "comprovante.pdf"
    assert anexo["ativo"] is True
    assert anexo["data_upload"] is not None
    assert "usuario_id" not in anexo  # posse nunca direta ao usuário

    resposta = client.get(f"/anexos/{anexo['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == anexo["id"]


def test_criar_anexo_normaliza_espacos_no_nome_original(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])

    anexo = _criar_anexo(client, headers, transacao["id"], nome_original="  nota.pdf  ")
    assert anexo["nome_original"] == "nota.pdf"


def test_criar_anexo_com_nome_original_vazio_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])

    resposta = client.post(
        "/anexos", json=_payload_anexo(transacao["id"], nome_original="   "), headers=headers
    )
    assert resposta.status_code == 422


def test_criar_anexo_em_transacao_inexistente_retorna_404(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/anexos", json=_payload_anexo(999999), headers=headers)
    assert resposta.status_code == 404


def test_criar_anexo_em_transacao_de_outro_usuario_retorna_404(client):
    """Regra de domínio explícita: não permitir anexar arquivos em
    transações de outro usuário."""
    headers_a = _registrar_e_logar(client, email="a@example.com")
    conta_a = _criar_conta(client, headers_a)
    transacao_a = _criar_transacao(client, headers_a, conta_a["id"])

    headers_b = _registrar_e_logar(client, email="b@example.com")
    resposta = client.post("/anexos", json=_payload_anexo(transacao_a["id"]), headers=headers_b)
    assert resposta.status_code == 404


def test_criar_multiplos_anexos_na_mesma_transacao_e_permitido(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])

    anexo_a = _criar_anexo(client, headers, transacao["id"], nome_original="a.pdf")
    anexo_b = _criar_anexo(client, headers, transacao["id"], nome_original="b.pdf")
    assert anexo_a["id"] != anexo_b["id"]


# --- obter ---------------------------------------------------------------

def test_obter_anexo_inexistente_retorna_404(client):
    headers = _registrar_e_logar(client)
    resposta = client.get("/anexos/999999", headers=headers)
    assert resposta.status_code == 404


def test_obter_anexo_de_transacao_de_outro_usuario_retorna_404(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    conta_a = _criar_conta(client, headers_a)
    transacao_a = _criar_transacao(client, headers_a, conta_a["id"])
    anexo = _criar_anexo(client, headers_a, transacao_a["id"])

    headers_b = _registrar_e_logar(client, email="b@example.com")
    resposta = client.get(f"/anexos/{anexo['id']}", headers=headers_b)
    assert resposta.status_code == 404


# --- listar ----------------------------------------------------------------

def test_listar_anexos_por_transacao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])
    outra_transacao = _criar_transacao(client, headers, conta["id"], descricao="Outra")

    _criar_anexo(client, headers, transacao["id"], nome_original="a.pdf")
    _criar_anexo(client, headers, outra_transacao["id"], nome_original="b.pdf")

    resposta = client.get("/anexos", params={"transacao_id": transacao["id"]}, headers=headers)
    assert resposta.status_code == 200
    nomes = [a["nome_original"] for a in resposta.json()]
    assert nomes == ["a.pdf"]


def test_listar_anexos_de_transacao_de_outro_usuario_retorna_404(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    conta_a = _criar_conta(client, headers_a)
    transacao_a = _criar_transacao(client, headers_a, conta_a["id"])

    headers_b = _registrar_e_logar(client, email="b@example.com")
    resposta = client.get("/anexos", params={"transacao_id": transacao_a["id"]}, headers=headers_b)
    assert resposta.status_code == 404


def test_listar_anexos_filtra_apenas_ativos_por_padrao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])

    ativo = _criar_anexo(client, headers, transacao["id"], nome_original="ativo.pdf")
    inativo = _criar_anexo(client, headers, transacao["id"], nome_original="inativo.pdf")
    client.delete(f"/anexos/{inativo['id']}", headers=headers)

    resposta = client.get("/anexos", params={"transacao_id": transacao["id"]}, headers=headers)
    assert [a["nome_original"] for a in resposta.json()] == ["ativo.pdf"]

    resposta_todos = client.get(
        "/anexos", params={"transacao_id": transacao["id"], "apenas_ativos": False}, headers=headers
    )
    assert {a["nome_original"] for a in resposta_todos.json()} == {"ativo.pdf", "inativo.pdf"}


# --- soft delete -------------------------------------------------------------

def test_excluir_anexo_e_soft_delete(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])
    anexo = _criar_anexo(client, headers, transacao["id"])

    resposta = client.delete(f"/anexos/{anexo['id']}", headers=headers)
    assert resposta.status_code == 204

    # o anexo continua existindo (soft delete), só ativo=False
    resposta_obter = client.get(f"/anexos/{anexo['id']}", headers=headers)
    assert resposta_obter.status_code == 200
    assert resposta_obter.json()["ativo"] is False


def test_excluir_anexo_de_transacao_de_outro_usuario_retorna_404(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    conta_a = _criar_conta(client, headers_a)
    transacao_a = _criar_transacao(client, headers_a, conta_a["id"])
    anexo = _criar_anexo(client, headers_a, transacao_a["id"])

    headers_b = _registrar_e_logar(client, email="b@example.com")
    resposta = client.delete(f"/anexos/{anexo['id']}", headers=headers_b)
    assert resposta.status_code == 404


def test_excluir_anexo_inexistente_retorna_404(client):
    headers = _registrar_e_logar(client)
    resposta = client.delete("/anexos/999999", headers=headers)
    assert resposta.status_code == 404


# --- sem PATCH -------------------------------------------------------------

def test_patch_anexo_nao_e_uma_rota_valida(client):
    """Decisão confirmada explicitamente com o usuário antes da
    implementação: Anexo é create+read+soft-delete apenas."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])
    anexo = _criar_anexo(client, headers, transacao["id"])

    resposta = client.patch(f"/anexos/{anexo['id']}", json={"nome_original": "novo.pdf"}, headers=headers)
    assert resposta.status_code == 405


# --- cascade físico via exclusão de Transacao ------------------------------

def test_excluir_transacao_remove_seus_anexos_via_cascade(client):
    """Transacao usa hard delete (sem soft delete) - um Anexo órfão não faz
    sentido, então a exclusão física da Transacao remove os Anexos
    vinculados (ondelete=CASCADE + cascade=all,delete-orphan - ver
    docs/analise-arquitetural-anexo.md)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    transacao = _criar_transacao(client, headers, conta["id"])
    anexo = _criar_anexo(client, headers, transacao["id"])

    resposta_excluir = client.delete(f"/transacoes/{transacao['id']}", headers=headers)
    assert resposta_excluir.status_code == 204

    # a transacao nao existe mais -> obter o anexo tambem devolve 404,
    # porque a checagem de posse passa por TransacaoService.obter()
    resposta_anexo = client.get(f"/anexos/{anexo['id']}", headers=headers)
    assert resposta_anexo.status_code == 404
