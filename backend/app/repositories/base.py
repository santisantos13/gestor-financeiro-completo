"""Repository genérico: implementa as operações de CRUD comuns a qualquer
entidade, para não reescrever get/list/create/update/delete em cada
Repository especifico (principio DRY).

IRepository e um Protocol (interface estrutural do Python) - Services vao
depender DESSA interface, nao da classe concreta SQLAlchemyRepository. Isso
e o "D" do SOLID (Dependency Inversion): a camada de cima (Service) depende
de uma abstracao, nao de um detalhe de implementacao. Na pratica, isso
permite testar um Service com um repository FALSO (uma lista em memoria,
por exemplo) sem precisar de banco de dados nenhum - e exatamente o que
tests/unit faz.
"""
from typing import Generic, Protocol, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

# TypeVar amarrada a Base: um Repository so pode operar sobre um model
# SQLAlchemy de verdade, nunca um tipo qualquer.
ModelType = TypeVar("ModelType", bound=Base)


class IRepository(Protocol[ModelType]):
    """Contrato que todo repository (real ou de teste) deve cumprir.

    Um Service que dependa de IRepository (em vez de SQLAlchemyRepository
    diretamente) pode receber, em producao, um SQLAlchemyRepository, e em
    teste unitario, uma implementacao falsa - sem mudar uma linha do Service.
    """

    def get(self, id: int) -> ModelType | None: ...

    def list(self, *, skip: int = 0, limit: int = 100) -> Sequence[ModelType]: ...

    def create(self, obj: ModelType) -> ModelType: ...

    def update(self, obj: ModelType) -> ModelType: ...

    def delete(self, obj: ModelType) -> None: ...


class SQLAlchemyRepository(Generic[ModelType]):
    """Implementação concreta de IRepository usando o ORM do SQLAlchemy.

    Uso típico numa entidade especifica:

        class ContaRepository(SQLAlchemyRepository[Conta]):
            model = Conta

            # metodos extras especificos de Conta entram aqui, ex:
            def listar_ativas_do_usuario(self, usuario_id: int) -> Sequence[Conta]:
                stmt = select(Conta).where(Conta.usuario_id == usuario_id, Conta.ativo.is_(True))
                return self.db.execute(stmt).scalars().all()

    Importante sobre transacoes: os metodos abaixo usam `flush`, NUNCA
    `commit`. Flush envia o SQL pro banco (preenche o `id` de um objeto
    novo, por exemplo) mas nao fecha a transacao. Quem decide QUANDO
    confirmar (commit) e a sessao do request como um todo (ver
    app/db/session.py) - nao o Repository. Isso garante que um Service que
    precise mexer em mais de uma tabela numa unica operacao (ex:
    Transferencia debitando uma conta e creditando outra) sempre tenha
    tudo dentro da MESMA transacao atomica: ou tudo e salvo, ou nada e.
    """

    model: type[ModelType]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id: int) -> ModelType | None:
        return self.db.get(self.model, id)

    def list(self, *, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, obj: ModelType) -> ModelType:
        # o objeto ja esta "attached" a sessao (veio de um get() anterior),
        # entao so precisamos garantir que as mudancas nele sejam enviadas.
        self.db.flush()
        return obj

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.flush()
