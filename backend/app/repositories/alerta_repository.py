"""Repository de Alerta.

Além do CRUD genérico, expõe a listagem por usuário — a única query extra
necessária: diferente de Meta/Tag, Alerta não tem busca por nome (não faz
sentido reativar/deduplicar por "descrição", cada regra é livre para se
repetir).
"""
from typing import Sequence

from sqlalchemy import select

from app.models import Alerta
from app.repositories.base import SQLAlchemyRepository


class AlertaRepository(SQLAlchemyRepository[Alerta]):
    model = Alerta

    def listar_do_usuario(self, usuario_id: int, *, apenas_ativos: bool = False) -> Sequence[Alerta]:
        condicoes = [Alerta.usuario_id == usuario_id]
        if apenas_ativos:
            condicoes.append(Alerta.ativo.is_(True))
        stmt = select(Alerta).where(*condicoes).order_by(Alerta.criado_em.desc())
        return self.db.execute(stmt).scalars().all()
