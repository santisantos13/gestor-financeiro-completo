"""Testes de integração do fluxo de autenticação completo: sobem a
aplicação FastAPI real (banco de teste no lugar do real) e fazem
requisições HTTP de verdade via TestClient - registro, login, acesso
protegido, refresh com rotation, logout escopado e logout global.
"""
from sqlalchemy import select

from app.models import SessaoUsuario


def _registrar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post(
        "/auth/registrar",
        json={"nome": "Ana", "email": email, "senha": senha},
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _login(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _auth_header(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_registrar_login_e_acessar_rota_protegida(client):
    _registrar(client)
    tokens = _login(client)

    resposta = client.get("/auth/me", headers=_auth_header(tokens))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["email"] == "ana@example.com"
    assert corpo["papel"] == "USER"
    assert "senha_hash" not in corpo
    assert "senha" not in corpo


def test_registrar_com_email_duplicado_retorna_409(client):
    _registrar(client)
    resposta = client.post(
        "/auth/registrar",
        json={"nome": "Outra Ana", "email": "ana@example.com", "senha": "87654321"},
    )
    assert resposta.status_code == 409


def test_login_com_senha_errada_retorna_401(client):
    _registrar(client)
    resposta = client.post("/auth/login", json={"email": "ana@example.com", "senha": "senhaerrada"})
    assert resposta.status_code == 401
    assert resposta.headers.get("www-authenticate") == "Bearer"


def test_acessar_rota_protegida_sem_token_retorna_401(client):
    resposta = client.get("/auth/me")
    assert resposta.status_code == 401


def test_acessar_rota_protegida_com_token_invalido_retorna_401(client):
    resposta = client.get("/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resposta.status_code == 401


def test_refresh_emite_novo_par_e_rotaciona_o_token_antigo(client):
    _registrar(client)
    tokens = _login(client)

    resposta = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resposta.status_code == 200
    novos_tokens = resposta.json()
    assert novos_tokens["refresh_token"] != tokens["refresh_token"]

    # o access token novo funciona numa rota protegida
    resposta_me = client.get("/auth/me", headers=_auth_header(novos_tokens))
    assert resposta_me.status_code == 200

    # o refresh token antigo, ja usado, nao serve mais (rotation)
    resposta_refresh_repetido = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resposta_refresh_repetido.status_code == 401


def test_refresh_grava_o_user_agent_da_requisicao_de_refresh_e_nao_o_do_login(client, db_session):
    """Regressao: a sessao criada pelo refresh deve refletir de onde a
    requisicao de refresh atual veio, nunca o contexto (ip/user_agent) do
    login original que a originou."""
    _registrar(client)
    resposta_login = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "senha": "12345678"},
        headers={"User-Agent": "dispositivo-A"},
    )
    tokens = resposta_login.json()

    client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"User-Agent": "dispositivo-B"},
    )

    sessao_ativa = db_session.execute(
        select(SessaoUsuario).where(SessaoUsuario.revogado_em.is_(None))
    ).scalar_one()
    assert sessao_ativa.user_agent == "dispositivo-B"


def test_refresh_com_token_invalido_retorna_401(client):
    resposta = client.post("/auth/refresh", json={"refresh_token": "nunca-existiu"})
    assert resposta.status_code == 401


def test_logout_encerra_apenas_a_sessao_daquele_token(client):
    _registrar(client)
    tokens_sessao_1 = _login(client)
    tokens_sessao_2 = _login(client)

    resposta = client.post(
        "/auth/logout",
        json={"refresh_token": tokens_sessao_1["refresh_token"]},
        headers=_auth_header(tokens_sessao_1),
    )
    assert resposta.status_code == 204

    # sessao 1 nao renova mais...
    resposta_refresh_1 = client.post("/auth/refresh", json={"refresh_token": tokens_sessao_1["refresh_token"]})
    assert resposta_refresh_1.status_code == 401

    # ...mas a sessao 2 (outro "dispositivo") continua ativa
    resposta_refresh_2 = client.post("/auth/refresh", json={"refresh_token": tokens_sessao_2["refresh_token"]})
    assert resposta_refresh_2.status_code == 200


def test_logout_todas_encerra_todas_as_sessoes_do_usuario(client):
    _registrar(client)
    tokens_sessao_1 = _login(client)
    tokens_sessao_2 = _login(client)

    resposta = client.post("/auth/logout-todas", headers=_auth_header(tokens_sessao_1))
    assert resposta.status_code == 204

    assert client.post("/auth/refresh", json={"refresh_token": tokens_sessao_1["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": tokens_sessao_2["refresh_token"]}).status_code == 401


def test_logout_de_sessao_de_outro_usuario_retorna_403(client):
    _registrar(client, email="ana@example.com")
    _registrar(client, email="bruno@example.com")
    tokens_ana = _login(client, email="ana@example.com")
    tokens_bruno = _login(client, email="bruno@example.com")

    resposta = client.post(
        "/auth/logout",
        json={"refresh_token": tokens_ana["refresh_token"]},
        headers=_auth_header(tokens_bruno),
    )
    assert resposta.status_code == 403


def test_registro_rejeita_senha_curta(client):
    resposta = client.post(
        "/auth/registrar",
        json={"nome": "Ana", "email": "ana@example.com", "senha": "123"},
    )
    assert resposta.status_code == 422


def test_registro_rejeita_email_invalido(client):
    resposta = client.post(
        "/auth/registrar",
        json={"nome": "Ana", "email": "nao-e-um-email", "senha": "12345678"},
    )
    assert resposta.status_code == 422


def test_atualizar_perfil_troca_nome_e_email(client):
    _registrar(client)
    tokens = _login(client)

    resposta = client.patch(
        "/auth/me",
        json={"nome": "Ana Paula", "email": "ana.paula@example.com"},
        headers=_auth_header(tokens),
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["nome"] == "Ana Paula"
    assert corpo["email"] == "ana.paula@example.com"

    # login com o e-mail novo funciona (a troca foi persistida de verdade)
    _login(client, email="ana.paula@example.com")


def test_atualizar_perfil_com_email_ja_usado_por_outro_usuario_retorna_409(client):
    _registrar(client, email="ana@example.com")
    _registrar(client, email="bruno@example.com")
    tokens_bruno = _login(client, email="bruno@example.com")

    resposta = client.patch(
        "/auth/me",
        json={"email": "ana@example.com"},
        headers=_auth_header(tokens_bruno),
    )
    assert resposta.status_code == 409


def test_atualizar_perfil_sem_token_retorna_401(client):
    resposta = client.patch("/auth/me", json={"nome": "Qualquer"})
    assert resposta.status_code == 401


def test_trocar_senha_com_senha_atual_correta(client):
    _registrar(client)
    tokens = _login(client)

    resposta = client.post(
        "/auth/trocar-senha",
        json={"senha_atual": "12345678", "senha_nova": "novaSenha123"},
        headers=_auth_header(tokens),
    )
    assert resposta.status_code == 204

    # login com a senha antiga nao funciona mais...
    resposta_login_antiga = client.post("/auth/login", json={"email": "ana@example.com", "senha": "12345678"})
    assert resposta_login_antiga.status_code == 401
    # ...mas com a senha nova sim
    _login(client, senha="novaSenha123")


def test_trocar_senha_com_senha_atual_incorreta_retorna_401(client):
    _registrar(client)
    tokens = _login(client)

    resposta = client.post(
        "/auth/trocar-senha",
        json={"senha_atual": "errada123", "senha_nova": "novaSenha123"},
        headers=_auth_header(tokens),
    )
    assert resposta.status_code == 401
