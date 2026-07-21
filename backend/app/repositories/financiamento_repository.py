"""Repository de Financiamento.

Além do CRUD genérico, expõe a listagem por usuário. Diferente de
Parcelamento/ContaRecorrente, o filtro padrão não é um booleano `ativo` -
Financiamento não tem esse campo, usa `StatusContratoCredito` (ver
app/models/mixins.py). `apenas_ativos=True` filtra `status != QUITADO`
(mantém ATIVO e INADIMPLENTE visíveis, oculta só o que já foi encerrado) -
ver docs/analise-arquitetural-financiamento.md.
"""
from typing import Sequence

from sqlalchemy import select

from app.models import Financiamento
from app.models.enums import StatusContratoCredito
from app.repositories.base import SQLAlchemyRepository


class FinanciamentoRepository(SQLAlchemyRepository[Financiamento]):
    model = Financiamento

    def listar_do_usuario(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Financiamento]:
        condicoes = [Financiamento.usuario_id == usuario_id]
        if apenas_ativos:
            condicoes.append(Financiamento.status != StatusContratoCredito.QUITADO)
        stmt = (
            select(Financiamento)
            .where(*condicoes)
            .order_by(Financiamento.data_inicio.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
