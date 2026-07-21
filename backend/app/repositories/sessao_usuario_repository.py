"""Repository de SessaoUsuario (sessoes de login / refresh tokens).

Alem do CRUD generico, adiciona buscas e uma operacao em lote proprias de
sessao: achar pelo hash do token (usado no refresh e no logout), listar as
sessoes ativas de um usuario, e revogar todas de uma vez (logout global)
sem carregar cada linha em Python e salvar uma por uma.
"""
from typing import Sequence

from sqlalchemy import select, update

from app.core.security import agora_utc_naive
from app.models import SessaoUsuario
from app.repositories.base import SQLAlchemyRepository


class SessaoUsuarioRepository(SQLAlchemyRepository[SessaoUsuario]):
    model = SessaoUsuario

    def buscar_por_token_hash(self, token_hash: str) -> SessaoUsuario | None:
        stmt = select(SessaoUsuario).where(SessaoUsuario.token_hash == token_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def listar_ativas_do_usuario(self, usuario_id: int) -> Sequence[SessaoUsuario]:
        stmt = select(SessaoUsuario).where(
            SessaoUsuario.usuario_id == usuario_id,
            SessaoUsuario.revogado_em.is_(None),
            SessaoUsuario.expira_em > agora_utc_naive(),
        )
        return self.db.execute(stmt).scalars().all()

    def revogar_todas_do_usuario(self, usuario_id: int) -> int:
        """Revoga em lote (um UPDATE só) todas as sessões ativas do usuário -
        usado no logout global. Evita N updates individuais quando o
        usuário tem várias sessões simultâneas."""
        stmt = (
            update(SessaoUsuario)
            .where(SessaoUsuario.usuario_id == usuario_id, SessaoUsuario.revogado_em.is_(None))
            .values(revogado_em=agora_utc_naive())
        )
        resultado = self.db.execute(stmt)
        self.db.flush()
        return resultado.rowcount
