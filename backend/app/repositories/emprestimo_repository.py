"""Repository de Emprestimo.

Espelha `FinanciamentoRepository` (mesmo `ContratoCreditoMixin`, mesma
semântica de `apenas_ativos` = `status != QUITADO`) - ver
docs/analise-arquitetural-emprestimo.md.
"""
from typing import Sequence

from sqlalchemy import select

from app.models import Emprestimo
from app.models.enums import StatusContratoCredito
from app.repositories.base import SQLAlchemyRepository


class EmprestimoRepository(SQLAlchemyRepository[Emprestimo]):
    model = Emprestimo

    def listar_do_usuario(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Emprestimo]:
        condicoes = [Emprestimo.usuario_id == usuario_id]
        if apenas_ativos:
            condicoes.append(Emprestimo.status != StatusContratoCredito.QUITADO)
        stmt = (
            select(Emprestimo)
            .where(*condicoes)
            .order_by(Emprestimo.data_inicio.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
