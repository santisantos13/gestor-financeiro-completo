"""Repository de Anexo.

Além do CRUD genérico, expõe a listagem por transação. Sem nenhuma
consulta que atravesse `usuario_id` - Anexo não tem essa coluna (posse é
transitiva via Transacao, validada em AnexoService reaproveitando
TransacaoService, nunca aqui - ver docs/analise-arquitetural-anexo.md).
"""
from typing import Sequence

from sqlalchemy import select

from app.models import Anexo
from app.repositories.base import SQLAlchemyRepository


class AnexoRepository(SQLAlchemyRepository[Anexo]):
    model = Anexo

    def listar_por_transacao(
        self, transacao_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Anexo]:
        condicoes = [Anexo.transacao_id == transacao_id]
        if apenas_ativos:
            condicoes.append(Anexo.ativo.is_(True))
        stmt = (
            select(Anexo)
            .where(*condicoes)
            .order_by(Anexo.data_upload)
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
