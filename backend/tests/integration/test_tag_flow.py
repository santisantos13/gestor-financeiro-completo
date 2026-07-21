"""Testes de integração do CRUD de Tag: TestClient + banco real (SQLite em
memória). Cobre isolamento entre usuários, unicidade de nome, reativação
de tag soft-deletada e soft delete via HTTP real.
"""
from datetime import date
from decimal import Decimal

from app.models import Tag, Transacao
from app.models.enums import StatusTransacao, TipoTransacao


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _usuario_id(client, headers):
    resposta = client.get("/auth/me", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["id"]


def _criar_tag(client, headers, nome="viagem", cor=None):
    payload = {"nome": nome}
    if cor is not None:
        payload["cor"] = cor
    resposta = client.post("/tags", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_criar_tag_sem_autenticacao_retorna_401(client):
    resposta = client.post("/tags", json={"nome": "viagem"})
    assert resposta.status_code == 401


def test_criar_e_obter_tag(client):
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers, nome="viagem", cor="#00FF00")

    assert tag["nome"] == "viagem"
    assert tag["cor"] == "#00FF00"
    assert tag["ativo"] is True

    resposta = client.get(f"/tags/{tag['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == tag["id"]


def test_criar_tag_com_nome_vazio_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/tags", json={"nome": ""}, headers=headers)
    assert resposta.status_code == 422


def test_criar_tag_com_nome_so_espacos_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/tags", json={"nome": "   "}, headers=headers)
    assert resposta.status_code == 422


def test_criar_tag_normaliza_espacos_nas_pontas_do_nome(client):
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers, nome="  viagem  ")
    assert tag["nome"] == "viagem"


def test_criar_tag_com_cor_invalida_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/tags", json={"nome": "x", "cor": "azul"}, headers=headers)
    assert resposta.status_code == 422


def test_criar_tag_com_nome_duplicado_retorna_409(client):
    headers = _registrar_e_logar(client)
    _criar_tag(client, headers, nome="viagem")
    resposta = client.post("/tags", json={"nome": "viagem"}, headers=headers)
    assert resposta.status_code == 409


def test_criar_tag_com_mesmo_nome_em_usuarios_diferentes_e_permitido(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    tag_ana = _criar_tag(client, headers_ana, nome="viagem")
    tag_bruno = _criar_tag(client, headers_bruno, nome="viagem")
    assert tag_ana["id"] != tag_bruno["id"]


def test_criar_tag_com_nome_de_tag_desativada_reativa(client):
    headers = _registrar_e_logar(client)
    original = _criar_tag(client, headers, nome="viagem")
    client.delete(f"/tags/{original['id']}", headers=headers)

    recriada = _criar_tag(client, headers, nome="viagem", cor="#ABCDEF")

    assert recriada["id"] == original["id"]
    assert recriada["ativo"] is True
    assert recriada["cor"] == "#ABCDEF"


def test_listar_tags_retorna_apenas_as_do_usuario_autenticado(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    _criar_tag(client, headers_ana, nome="Tag da Ana")
    _criar_tag(client, headers_bruno, nome="Tag do Bruno")

    resposta = client.get("/tags", headers=headers_ana)
    nomes = [t["nome"] for t in resposta.json()]
    assert nomes == ["Tag da Ana"]


def test_obter_tag_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    tag_ana = _criar_tag(client, headers_ana)

    resposta = client.get(f"/tags/{tag_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_atualizar_tag_parcial(client):
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers, nome="Original")

    resposta = client.patch(f"/tags/{tag['id']}", json={"cor": "#111111"}, headers=headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Original"
    assert corpo["cor"] == "#111111"


def test_atualizar_tag_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    tag_ana = _criar_tag(client, headers_ana)

    resposta = client.patch(f"/tags/{tag_ana['id']}", json={"nome": "Hackeado"}, headers=headers_bruno)
    assert resposta.status_code == 404


def test_atualizar_nome_para_nome_ja_usado_retorna_409(client):
    headers = _registrar_e_logar(client)
    _criar_tag(client, headers, nome="viagem")
    trabalho = _criar_tag(client, headers, nome="trabalho")

    resposta = client.patch(f"/tags/{trabalho['id']}", json={"nome": "viagem"}, headers=headers)
    assert resposta.status_code == 409


def test_desativar_tag_e_soft_delete(client):
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers)

    resposta = client.delete(f"/tags/{tag['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/tags/{tag['id']}", headers=headers)
    assert resposta_get.status_code == 200
    assert resposta_get.json()["ativo"] is False

    resposta_listagem = client.get("/tags", headers=headers)
    assert resposta_listagem.json() == []

    resposta_todas = client.get("/tags?apenas_ativas=false", headers=headers)
    assert len(resposta_todas.json()) == 1


def test_desativar_tag_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    tag_ana = _criar_tag(client, headers_ana)

    resposta = client.delete(f"/tags/{tag_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_atualizar_renomeando_para_nome_de_tag_inativa_retorna_409(client):
    """Diferente de POST (que reativa), PATCH renomeando para um nome de
    tag ja desativada NAO mescla automaticamente - a tag sendo renomeada e
    outra linha, com historico proprio."""
    headers = _registrar_e_logar(client)
    inativa = _criar_tag(client, headers, nome="viagem")
    client.delete(f"/tags/{inativa['id']}", headers=headers)
    outra = _criar_tag(client, headers, nome="trabalho")

    resposta = client.patch(f"/tags/{outra['id']}", json={"nome": "viagem"}, headers=headers)
    assert resposta.status_code == 409


def test_atualizar_ativo_true_reativa_tag_diretamente(client):
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers)
    client.delete(f"/tags/{tag['id']}", headers=headers)

    resposta = client.patch(f"/tags/{tag['id']}", json={"ativo": True}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is True


# ---- Exclusão definitiva (hard delete) - Etapa F10 ----


def test_excluir_tag_permanente_sem_uso_apaga_a_linha(client):
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers)

    resposta = client.delete(f"/tags/{tag['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/tags/{tag['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_tag_permanente_em_uso_e_permitido_mesmo_assim(client, db_session):
    """Diferente de Conta/Categoria/Cartão: Tag NUNCA bloqueia por uso
    (seção 2.3) - o vínculo N-N é só removido da tabela de associação,
    nenhuma transação é apagada."""
    headers = _registrar_e_logar(client)
    tag = _criar_tag(client, headers)
    usuario_id = _usuario_id(client, headers)

    resposta_conta = client.post("/contas", json={"nome": "Conta"}, headers=headers)
    conta_id = resposta_conta.json()["id"]

    tag_orm = db_session.get(Tag, tag["id"])
    transacao = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("10.00"),
        data=date.today(),
        descricao="Compra qualquer",
        status=StatusTransacao.PAGO,
        conta_id=conta_id,
        tags=[tag_orm],
    )
    db_session.add(transacao)
    db_session.commit()

    resposta_uso = client.get(f"/tags/{tag['id']}/uso", headers=headers)
    assert resposta_uso.status_code == 200
    assert resposta_uso.json()["transacoes_vinculadas"] == 1

    resposta = client.delete(f"/tags/{tag['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/tags/{tag['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_tag_permanente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    tag_ana = _criar_tag(client, headers_ana)

    resposta = client.delete(f"/tags/{tag_ana['id']}/permanente", headers=headers_bruno)
    assert resposta.status_code == 404
