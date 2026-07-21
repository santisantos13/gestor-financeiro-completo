"""Repository de ContaRecorrente.

Além do CRUD genérico, expõe a listagem por usuário. Sem nenhuma
agregação/soma aqui (mesma família de ParcelamentoRepository) - a fonte da
verdade de saldo/relatórios são as Transacoes geradas, nunca o template.
"""
from typing import Sequence

from sqlalchemy import select

from app.models import ContaRecorrente
from app.models.enums import StatusRecorrencia
from app.repositories.base import SQLAlchemyRepository


class ContaRecorrenteRepository(SQLAlchemyRepository[ContaRecorrente]):
    model = ContaRecorrente

    def listar_do_usuario(
        self,
        usuario_id: int,
        *,
        status: StatusRecorrencia | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ContaRecorrente]:
        """`status=None` lista tudo (inclusive ENCERRADAS - histórico);
        filtro por um status específico substitui o antigo booleano
        `apenas_ativas` (expansão 2026-07-20, `ativo` → `status`)."""
        condicoes = [ContaRecorrente.usuario_id == usuario_id]
        if status is not None:
            condicoes.append(ContaRecorrente.status == status)
        stmt = (
            select(ContaRecorrente)
            .where(*condicoes)
            .order_by(ContaRecorrente.data_inicio.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
