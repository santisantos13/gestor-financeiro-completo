"""Repository de Usuario.

Alem do CRUD generico herdado de SQLAlchemyRepository, adiciona a busca
por e-mail - necessaria pra login e pra checar duplicidade no registro.
Nao faz sentido esse metodo estar no repository generico (nem toda
entidade tem um campo "email" pra buscar por ele).
"""
from sqlalchemy import select

from app.models import Usuario
from app.repositories.base import SQLAlchemyRepository


class UsuarioRepository(SQLAlchemyRepository[Usuario]):
    model = Usuario

    def buscar_por_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        return self.db.execute(stmt).scalar_one_or_none()
