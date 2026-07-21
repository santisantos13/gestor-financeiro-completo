"""Repository de Tag.

Além do CRUD genérico, expõe a listagem por usuário e a busca por nome
(usada por TagService para validar unicidade e para reativar uma tag
soft-deletada em vez de tentar criar uma linha duplicada - ver
TagService.criar).
"""
from typing import Sequence

from sqlalchemy import func, select

from app.models import Tag
from app.models.associations import transacao_tag
from app.repositories.base import SQLAlchemyRepository


class TagRepository(SQLAlchemyRepository[Tag]):
    model = Tag

    def listar_do_usuario(
        self, usuario_id: int, *, apenas_ativas: bool = True, skip: int = 0, limit: int = 100
    ) -> Sequence[Tag]:
        condicoes = [Tag.usuario_id == usuario_id]
        if apenas_ativas:
            condicoes.append(Tag.ativo.is_(True))
        stmt = select(Tag).where(*condicoes).order_by(Tag.nome).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def buscar_por_nome(self, usuario_id: int, nome: str) -> Tag | None:
        """Busca INDEPENDENTE de `ativo` (ativa ou desativada) - e exatamente
        por isso que serve tanto para checar unicidade quanto para achar a
        tag a reativar quando o nome colide com uma ja desativada."""
        stmt = select(Tag).where(Tag.usuario_id == usuario_id, Tag.nome == nome)
        return self.db.execute(stmt).scalar_one_or_none()

    def contar_transacoes_vinculadas(self, tag_id: int) -> int:
        """Só informativo - Tag NÃO bloqueia exclusão definitiva por uso
        (`docs/analise-arquitetural-exclusao.md`, seção 2.3: o vínculo N-N
        com Transacao é `ondelete=CASCADE` só na tabela de associação,
        excluir a tag nunca apaga uma transação). O número volta na
        resposta para o frontend avisar quantas transações perdem o
        rótulo, sem impedir a ação."""
        stmt = select(func.count()).select_from(transacao_tag).where(transacao_tag.c.tag_id == tag_id)
        return self.db.execute(stmt).scalar_one()
