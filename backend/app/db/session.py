"""Configuração da engine e da sessão do SQLAlchemy.

Isolado em seu próprio módulo para que futuras trocas de banco (ex.: SQLite -> Postgres)
não afetem o resto da aplicação (princípio da inversão de dependência).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# SQLite, por padrao, so permite que a thread que abriu a conexao a use.
# O FastAPI pode atender requests em threads diferentes, entao
# check_same_thread=False desativa essa trava (seguro aqui porque cada
# request abre e fecha sua propria sessao, sem compartilhar conexao entre threads).
# Esse ajuste NAO se aplica a outros bancos (Postgres, MySQL...), por isso o if.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# engine: gerencia o pool de conexoes reais com o banco. Criado uma unica vez
# quando o modulo e importado (nao a cada request).
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# fabrica de sessoes: cada chamada a SessionLocal() cria uma sessao nova.
# autocommit=False / autoflush=False: controle explicito de quando os dados
# vao pro banco, em vez de comportamento implicito do SQLAlchemy.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency do FastAPI: abre uma sessão no início do request e a
    fecha no final, sempre.

    Esta função também é a nossa "unidade de trabalho" (Unit of Work): a
    MESMA sessão é compartilhada por todos os Repositories usados dentro de
    um Service durante um único request, então tudo que ele fizer (criar,
    atualizar, deletar em uma ou mais tabelas) faz parte de uma unica
    transacao. Ela e confirmada (`commit`) só se o request inteiro
    terminar sem exceção; se qualquer Service levantar uma exceção de
    domínio (ver app/core/exceptions.py) ou qualquer outro erro acontecer,
    tudo é desfeito (`rollback`) - nunca fica meio salvo.

    Repositories (app/repositories/base.py) nunca chamam commit/rollback -
    só essa função, no nível do request, decide isso. Uso típico numa rota:

        def minha_rota(db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
