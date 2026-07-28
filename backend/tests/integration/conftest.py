"""Fixtures compartilhadas pelos testes de integração.

Diferente dos testes unitários (que usam Mock), aqui usamos um banco
SQLite REAL, em memória e recriado do zero a cada teste, para validar que
os models, o Repository genérico e a API inteira funcionam juntos de
verdade - não só em teoria.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 - garante que todas as tabelas sejam registradas em Base.metadata
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_session():
    """Banco SQLite em memória, recriado do zero em cada teste (isolamento
    total: nenhum dado de um teste vaza pro outro).

    StaticPool + check_same_thread=False: sem isso, cada nova conexão
    aberta pelo SQLAlchemy criaria um banco em memória DIFERENTE e vazio
    (peculiaridade do SQLite ":memory:"). Com StaticPool, todas as conexões
    da engine reusam a mesma conexão física, então o schema criado por
    `Base.metadata.create_all` é o mesmo que os testes enxergam depois.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient do FastAPI com o banco real substituído pelo de teste via
    dependency override - as rotas continuam usando `Depends(get_db)`
    normalmente, sem saber que estão sendo testadas.

    `limiter.reset()` (docs/analise-arquitetural-rate-limiting.md): o
    `Limiter` de `/auth/login`/`/auth/refresh` guarda contagem em memória
    do PRÓPRIO PROCESSO, e `app` (import de `app.main`) é o mesmo objeto
    reusado por toda a suíte - sem resetar aqui, o contador se acumularia
    entre testes (o `TestClient` sempre reporta o mesmo IP, "testclient")
    e um teste no meio da suíte estouraria o limite por causa de logins de
    testes ANTERIORES, não dos seus próprios. Reset ANTES de cada teste
    (não depois) garante que mesmo o primeiro teste comece limpo.
    """
    limiter.reset()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
