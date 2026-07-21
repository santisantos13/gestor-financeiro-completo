"""Testa a camada Repository contra um banco SQLite real (fixture
`db_session` em conftest.py). Usa o model Usuario, que já existe, só para
provar que create/get/list/update/delete do SQLAlchemyRepository genérico
funcionam de ponta a ponta com um banco de verdade - nenhuma regra de
negócio de nenhuma entidade é testada aqui (isso vem com os Services, na
etapa de implementação dos CRUDs).
"""
from app.models import Usuario
from app.repositories.base import SQLAlchemyRepository


class UsuarioRepository(SQLAlchemyRepository[Usuario]):
    model = Usuario


def test_create_e_get(db_session):
    repo = UsuarioRepository(db_session)
    usuario = repo.create(Usuario(nome="Ana", email="ana@example.com", senha_hash="hash"))

    encontrado = repo.get(usuario.id)

    assert encontrado is not None
    assert encontrado.email == "ana@example.com"


def test_list_retorna_todos_os_criados(db_session):
    repo = UsuarioRepository(db_session)
    repo.create(Usuario(nome="Ana", email="ana@example.com", senha_hash="x"))
    repo.create(Usuario(nome="Bia", email="bia@example.com", senha_hash="x"))

    resultado = repo.list()

    assert len(resultado) == 2


def test_update_persiste_mudanca(db_session):
    repo = UsuarioRepository(db_session)
    usuario = repo.create(Usuario(nome="Ana", email="ana@example.com", senha_hash="x"))

    usuario.nome = "Ana Paula"
    repo.update(usuario)
    db_session.expire_all()  # força reler do banco em vez do cache da sessão

    encontrado = repo.get(usuario.id)
    assert encontrado.nome == "Ana Paula"


def test_delete_remove_do_banco(db_session):
    repo = UsuarioRepository(db_session)
    usuario = repo.create(Usuario(nome="Ana", email="ana@example.com", senha_hash="x"))
    usuario_id = usuario.id

    repo.delete(usuario)

    assert repo.get(usuario_id) is None
