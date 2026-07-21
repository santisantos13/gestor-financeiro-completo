"""Model Tag - classificacao complementar e livre, ortogonal a Categoria.

Enquanto uma Transacao tem no MAXIMO uma Categoria (hierarquica, estruturada
pelo sistema), ela pode ter VARIAS Tags (plano, criado livremente pelo
usuario) - ex: uma compra pode estar na categoria "Alimentacao" e ter as
tags "viagem-europa-2026" e "reembolsavel" ao mesmo tempo.
"""
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import transacao_tag
from app.models.mixins import TimestampMixin


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (
        # o mesmo usuario nao pode ter duas tags com o mesmo nome. Vale
        # inclusive para tags desativadas (ativo=False) - o Service resolve
        # esse caso reativando a tag existente em vez de tentar inserir uma
        # linha nova (ver TagService.criar), entao a constraint nunca chega
        # a ser violada por um fluxo normal de "recriar" uma tag apagada.
        UniqueConstraint("usuario_id", "nome", name="uq_tag_usuario_nome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    nome: Mapped[str] = mapped_column(String(60))
    cor: Mapped[str | None] = mapped_column(String(7), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="tags")

    # secondary=transacao_tag -> relacionamento N-N atraves da tabela de associacao.
    # Soft delete (ativo=False) nao mexe nessa associacao: uma tag desativada
    # some das listas de novas selecoes, mas transacoes que ja a usavam
    # continuam vinculadas - o historico nao e afetado.
    transacoes: Mapped[list["Transacao"]] = relationship(secondary=transacao_tag, back_populates="tags")
