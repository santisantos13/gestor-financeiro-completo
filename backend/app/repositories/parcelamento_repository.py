"""Repository de Parcelamento.

Além do CRUD genérico, expõe a listagem por usuário. Sem nenhuma
agregação/soma aqui (diferente de Conta/Cartão/Fatura) - Parcelamento não
tem nenhum valor calculado a partir de Transacao; `valor_total` é um
campo fixo, definido na criação (ver docs/analise-arquitetural-parcelamento.md).
"""
from typing import Sequence

from sqlalchemy import select

from app.models import Parcelamento
from app.repositories.base import SQLAlchemyRepository


class ParcelamentoRepository(SQLAlchemyRepository[Parcelamento]):
    model = Parcelamento

    def listar_do_usuario(
        self, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Parcelamento]:
        condicoes = [Parcelamento.usuario_id == usuario_id]
        if apenas_ativos:
            condicoes.append(Parcelamento.ativo.is_(True))
        stmt = (
            select(Parcelamento)
            .where(*condicoes)
            .order_by(Parcelamento.data_inicio.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
