"""Model CategoriaOcultaUsuario - "ocultar categoria de sistema para mim".

Sprint de Refinamento Premium, item 4 (docs/analise-arquitetural-sprint-
refinamento-premium.md, secao 4): categoria de sistema (`usuario_id IS
NULL`) e uma UNICA LINHA global, compartilhada por todos os usuarios -
`desativar()`/`excluir()` continuam bloqueando 100% para ela (nenhuma
mudanca ali). Esta tabela nao e uma exclusao de verdade: e so o registro
de "este usuario pediu para nao ver mais esta categoria de sistema nas
suas listas" - a linha de `Categoria` permanece intocada para todo mundo.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoriaOcultaUsuario(Base):
    __tablename__ = "categorias_ocultas_usuario"
    __table_args__ = (UniqueConstraint("usuario_id", "categoria_id", name="uq_categoria_oculta_usuario"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id", ondelete="CASCADE"), index=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
