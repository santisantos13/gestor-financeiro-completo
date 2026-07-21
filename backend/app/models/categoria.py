"""Model Categoria - classificacao hierarquica de transacoes.

Suporta subcategorias via auto-relacionamento (categoria_pai_id -> aponta
para outra linha da mesma tabela). Categorias com usuario_id nulo sao
categorias padrao do sistema (seed, compartilhadas por todos os usuarios);
com usuario_id preenchido sao categorias customizadas criadas por aquele
usuario especificamente.
"""
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TipoCategoria
from app.models.mixins import TimestampMixin


class Categoria(Base, TimestampMixin):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    # nullable: None = categoria padrao do sistema, disponivel para todo mundo
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=True, index=True
    )
    categoria_pai_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id", ondelete="CASCADE"), nullable=True
    )

    nome: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[TipoCategoria] = mapped_column(default=TipoCategoria.AMBOS)
    cor: Mapped[str | None] = mapped_column(String(7), nullable=True)  # ex: "#FF5733", usado na UI
    icone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario | None"] = relationship(back_populates="categorias")

    # remote_side=[id] e o que diz ao SQLAlchemy "este e um relacionamento
    # da tabela consigo mesma": categoria_pai aponta pra "cima" na hierarquia,
    # subcategorias aponta pra "baixo".
    categoria_pai: Mapped["Categoria | None"] = relationship(remote_side=[id], back_populates="subcategorias")
    subcategorias: Mapped[list["Categoria"]] = relationship(back_populates="categoria_pai")

    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="categoria")
    parcelamentos: Mapped[list["Parcelamento"]] = relationship(back_populates="categoria")
    financiamentos: Mapped[list["Financiamento"]] = relationship(back_populates="categoria")
    emprestimos: Mapped[list["Emprestimo"]] = relationship(back_populates="categoria")
    contas_recorrentes: Mapped[list["ContaRecorrente"]] = relationship(back_populates="categoria")
