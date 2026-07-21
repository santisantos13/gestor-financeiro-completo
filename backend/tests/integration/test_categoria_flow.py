"""Testes de integração do CRUD de Categoria: TestClient + banco real
(SQLite em memória). Categorias do sistema não têm mecanismo de seed nesta
etapa - inseridas direto via `db_session` para simular o que uma migration
de seed faria no futuro.
"""
from app.models import Categoria


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_categoria(client, headers, nome="Alimentação", categoria_pai_id=None):
    payload = {"nome": nome}
    if categoria_pai_id is not None:
        payload["categoria_pai_id"] = categoria_pai_id
    resposta = client.post("/categorias", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_categoria_sistema(db_session, nome="Moradia"):
    categoria = Categoria(nome=nome, usuario_id=None, ativo=True)
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)
    return categoria


def test_criar_categoria_sem_autenticacao_retorna_401(client):
    resposta = client.post("/categorias", json={"nome": "Alimentação"})
    assert resposta.status_code == 401


def test_criar_e_obter_categoria(client):
    headers = _registrar_e_logar(client)
    categoria = _criar_categoria(client, headers, nome="Lazer")

    assert categoria["nome"] == "Lazer"
    assert categoria["tipo"] == "AMBOS"
    assert categoria["ativo"] is True
    assert categoria["e_do_sistema"] is False

    resposta = client.get(f"/categorias/{categoria['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == categoria["id"]


def test_criar_categoria_com_nome_vazio_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/categorias", json={"nome": ""}, headers=headers)
    assert resposta.status_code == 422


def test_criar_categoria_com_cor_invalida_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/categorias", json={"nome": "X", "cor": "vermelho"}, headers=headers)
    assert resposta.status_code == 422


def test_criar_categoria_com_cor_valida_e_aceita(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/categorias", json={"nome": "X", "cor": "#FF5733"}, headers=headers)
    assert resposta.status_code == 201
    assert resposta.json()["cor"] == "#FF5733"


def test_criar_subcategoria_com_pai_valido(client):
    headers = _registrar_e_logar(client)
    pai = _criar_categoria(client, headers, nome="Transporte")
    filha = _criar_categoria(client, headers, nome="Combustível", categoria_pai_id=pai["id"])
    assert filha["categoria_pai_id"] == pai["id"]


def test_criar_categoria_com_pai_inexistente_retorna_404(client):
    headers = _registrar_e_logar(client)
    resposta = client.post(
        "/categorias", json={"nome": "Filha", "categoria_pai_id": 999}, headers=headers
    )
    assert resposta.status_code == 404


def test_criar_categoria_com_pai_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    categoria_bruno = _criar_categoria(client, headers_bruno, nome="Categoria do Bruno")

    resposta = client.post(
        "/categorias",
        json={"nome": "Filha", "categoria_pai_id": categoria_bruno["id"]},
        headers=headers_ana,
    )
    assert resposta.status_code == 404


def test_listar_inclui_categorias_do_sistema_e_proprias_mas_nao_de_outro_usuario(client, db_session):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    _criar_categoria_sistema(db_session, nome="Moradia")
    _criar_categoria(client, headers_ana, nome="Categoria da Ana")
    _criar_categoria(client, headers_bruno, nome="Categoria do Bruno")

    resposta = client.get("/categorias", headers=headers_ana)
    nomes = {c["nome"] for c in resposta.json()}
    assert nomes == {"Moradia", "Categoria da Ana"}


def test_obter_categoria_do_sistema_e_permitido_para_qualquer_usuario(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)

    resposta = client.get(f"/categorias/{sistema.id}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["e_do_sistema"] is True


def test_atualizar_categoria_do_sistema_retorna_200(client, db_session):
    """Tarefa #111 - edição livre: conteúdo de categoria de sistema agora é
    editável por qualquer usuário autenticado."""
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)

    resposta = client.patch(f"/categorias/{sistema.id}", json={"nome": "Renomeada"}, headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Renomeada"


def test_atualizar_categoria_do_sistema_com_ativo_false_retorna_403(client, db_session):
    """Desativar (ativo:false) uma categoria de sistema continua bloqueado -
    tiraria a categoria de todos os usuários, não só de quem editou."""
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)

    resposta = client.patch(f"/categorias/{sistema.id}", json={"ativo": False}, headers=headers)
    assert resposta.status_code == 403


def test_atualizar_categoria_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    categoria_ana = _criar_categoria(client, headers_ana)

    resposta = client.patch(
        f"/categorias/{categoria_ana['id']}", json={"nome": "Hackeado"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


def test_atualizar_categoria_parcial(client):
    headers = _registrar_e_logar(client)
    categoria = _criar_categoria(client, headers, nome="Original")

    resposta = client.patch(f"/categorias/{categoria['id']}", json={"cor": "#000000"}, headers=headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Original"  # nao enviado, preservado
    assert corpo["cor"] == "#000000"


def test_atualizar_categoria_pai_dela_mesma_retorna_422(client):
    headers = _registrar_e_logar(client)
    categoria = _criar_categoria(client, headers)

    resposta = client.patch(
        f"/categorias/{categoria['id']}",
        json={"categoria_pai_id": categoria["id"]},
        headers=headers,
    )
    assert resposta.status_code == 422


def test_atualizar_criando_ciclo_retorna_422(client):
    headers = _registrar_e_logar(client)
    a = _criar_categoria(client, headers, nome="A")
    b = _criar_categoria(client, headers, nome="B", categoria_pai_id=a["id"])

    resposta = client.patch(
        f"/categorias/{a['id']}", json={"categoria_pai_id": b["id"]}, headers=headers
    )
    assert resposta.status_code == 422


def test_desativar_categoria_com_subcategoria_ativa_retorna_422(client):
    headers = _registrar_e_logar(client)
    pai = _criar_categoria(client, headers, nome="Pai")
    _criar_categoria(client, headers, nome="Filha", categoria_pai_id=pai["id"])

    resposta = client.delete(f"/categorias/{pai['id']}", headers=headers)
    assert resposta.status_code == 422


def test_desativar_categoria_sem_subcategoria_ativa_funciona(client):
    headers = _registrar_e_logar(client)
    categoria = _criar_categoria(client, headers)

    resposta = client.delete(f"/categorias/{categoria['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/categorias/{categoria['id']}", headers=headers)
    assert resposta_get.json()["ativo"] is False


def test_desativar_categoria_do_sistema_retorna_403(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)

    resposta = client.delete(f"/categorias/{sistema.id}", headers=headers)
    assert resposta.status_code == 403


def test_desativar_categoria_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    categoria_ana = _criar_categoria(client, headers_ana)

    resposta = client.delete(f"/categorias/{categoria_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_patch_ativo_false_nao_contorna_bloqueio_de_subcategoria_ativa(client):
    """Regressao: PATCH {"ativo": false} tem que respeitar a mesma regra de
    DELETE (nao desativar com subcategoria ativa)."""
    headers = _registrar_e_logar(client)
    pai = _criar_categoria(client, headers, nome="Pai")
    _criar_categoria(client, headers, nome="Filha", categoria_pai_id=pai["id"])

    resposta = client.patch(f"/categorias/{pai['id']}", json={"ativo": False}, headers=headers)
    assert resposta.status_code == 422


# ---- Exclusão definitiva (hard delete) - Etapa F10 ----


def test_excluir_categoria_permanente_sem_vinculo_apaga_a_linha(client):
    headers = _registrar_e_logar(client)
    categoria = _criar_categoria(client, headers)

    resposta = client.delete(f"/categorias/{categoria['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/categorias/{categoria['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_categoria_permanente_com_subcategoria_inativa_retorna_422(client):
    """Mais rigido que a desativacao (que so olha filha ATIVA): aqui
    qualquer subcategoria, mesmo desativada, ja bloqueia (auto-FK com
    ondelete=CASCADE)."""
    headers = _registrar_e_logar(client)
    pai = _criar_categoria(client, headers, nome="Pai")
    filha = _criar_categoria(client, headers, nome="Filha", categoria_pai_id=pai["id"])
    client.delete(f"/categorias/{filha['id']}", headers=headers)  # desativa a filha

    resposta = client.delete(f"/categorias/{pai['id']}/permanente", headers=headers)
    assert resposta.status_code == 422


def test_excluir_categoria_permanente_do_sistema_retorna_403(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)

    resposta = client.delete(f"/categorias/{sistema.id}/permanente", headers=headers)
    assert resposta.status_code == 403


def test_excluir_categoria_permanente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    categoria_ana = _criar_categoria(client, headers_ana)

    resposta = client.delete(f"/categorias/{categoria_ana['id']}/permanente", headers=headers_bruno)
    assert resposta.status_code == 404


# ---- Ocultar/reexibir por usuário (Sprint de Refinamento Premium, item 4) --


def test_ocultar_categoria_do_sistema_some_da_listagem_do_usuario(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)

    resposta = client.delete(f"/categorias/{sistema.id}/ocultar", headers=headers)
    assert resposta.status_code == 204

    resposta_listar = client.get("/categorias", headers=headers)
    assert sistema.id not in {c["id"] for c in resposta_listar.json()}


def test_ocultar_categoria_nao_afeta_outro_usuario(client, db_session):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    sistema = _criar_categoria_sistema(db_session)

    client.delete(f"/categorias/{sistema.id}/ocultar", headers=headers_ana)

    resposta_bruno = client.get("/categorias", headers=headers_bruno)
    assert sistema.id in {c["id"] for c in resposta_bruno.json()}

    resposta_get_bruno = client.get(f"/categorias/{sistema.id}", headers=headers_bruno)
    assert resposta_get_bruno.status_code == 200
    assert resposta_get_bruno.json()["oculta_para_mim"] is False


def test_ocultar_categoria_propria_retorna_422(client):
    headers = _registrar_e_logar(client)
    categoria = _criar_categoria(client, headers)

    resposta = client.delete(f"/categorias/{categoria['id']}/ocultar", headers=headers)
    assert resposta.status_code == 422


def test_ocultar_categoria_de_outro_usuario_privada_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    categoria_ana = _criar_categoria(client, headers_ana)

    resposta = client.delete(f"/categorias/{categoria_ana['id']}/ocultar", headers=headers_bruno)
    assert resposta.status_code == 404


def test_ocultar_categoria_com_transacao_vinculada_retorna_422(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)
    conta = client.post("/contas", json={"nome": "Conta"}, headers=headers).json()
    resposta_transacao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "50.00",
            "data": "2026-07-03",
            "descricao": "Compra",
            "conta_id": conta["id"],
            "categoria_id": sistema.id,
        },
        headers=headers,
    )
    assert resposta_transacao.status_code == 201, resposta_transacao.text

    resposta = client.delete(f"/categorias/{sistema.id}/ocultar", headers=headers)
    assert resposta.status_code == 422


def test_reexibir_categoria_oculta_volta_a_aparecer(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)
    client.delete(f"/categorias/{sistema.id}/ocultar", headers=headers)

    resposta = client.post(f"/categorias/{sistema.id}/reexibir", headers=headers)
    assert resposta.status_code == 204

    resposta_listar = client.get("/categorias", headers=headers)
    assert sistema.id in {c["id"] for c in resposta_listar.json()}


def test_listar_incluir_ocultas_devolve_categoria_oculta(client, db_session):
    headers = _registrar_e_logar(client)
    sistema = _criar_categoria_sistema(db_session)
    client.delete(f"/categorias/{sistema.id}/ocultar", headers=headers)

    resposta = client.get("/categorias", params={"incluir_ocultas": True}, headers=headers)
    categorias_por_id = {c["id"]: c for c in resposta.json()}
    assert sistema.id in categorias_por_id
    assert categorias_por_id[sistema.id]["oculta_para_mim"] is True
