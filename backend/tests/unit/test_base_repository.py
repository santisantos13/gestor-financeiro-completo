"""Testes unitários da camada Repository.

Não tocam em banco de dados nenhum: a sessão do SQLAlchemy é substituída
por um Mock. O objetivo aqui não é testar se o SQL funciona (isso é
responsabilidade de tests/integration/) e sim se SQLAlchemyRepository chama
os métodos certos da sessão, na ordem certa - por isso um Mock basta e o
teste roda em milissegundos, sem precisar de banco nenhum.
"""
from unittest.mock import MagicMock

from app.models import Usuario
from app.repositories.base import SQLAlchemyRepository


class UsuarioRepository(SQLAlchemyRepository[Usuario]):
    """Repository concreto minimo, só pra ter um `model` definido - o
    mesmo padrão que cada entidade real vai seguir na etapa dos CRUDs.
    """

    model = Usuario


def test_get_busca_pelo_id_usando_session_get():
    db = MagicMock()
    db.get.return_value = Usuario(id=1, nome="Ana", email="ana@example.com", senha_hash="x")
    repo = UsuarioRepository(db)

    resultado = repo.get(1)

    db.get.assert_called_once_with(Usuario, 1)
    assert resultado.nome == "Ana"


def test_create_adiciona_e_da_flush_na_sessao():
    db = MagicMock()
    repo = UsuarioRepository(db)
    novo = Usuario(nome="Bia", email="bia@example.com", senha_hash="x")

    resultado = repo.create(novo)

    db.add.assert_called_once_with(novo)
    db.flush.assert_called_once()
    assert resultado is novo


def test_create_nao_chama_commit():
    # Regra de arquitetura: Repository nunca decide quando commitar - isso
    # é responsabilidade da sessão do request (app/db/session.py). Se um
    # Repository chamasse commit, uma operação de Service que mexe em duas
    # tabelas (ex: Transferencia) deixaria de ser atômica.
    db = MagicMock()
    repo = UsuarioRepository(db)

    repo.create(Usuario(nome="Bia", email="bia@example.com", senha_hash="x"))

    db.commit.assert_not_called()


def test_delete_remove_e_da_flush_na_sessao():
    db = MagicMock()
    repo = UsuarioRepository(db)
    usuario = Usuario(id=1, nome="Ana", email="ana@example.com", senha_hash="x")

    repo.delete(usuario)

    db.delete.assert_called_once_with(usuario)
    db.flush.assert_called_once()


def test_list_executa_select_com_skip_e_limit():
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = []
    repo = UsuarioRepository(db)

    resultado = repo.list(skip=10, limit=5)

    assert db.execute.called
    assert resultado == []
