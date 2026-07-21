"""Model Financiamento - contrato de credito atrelado a aquisicao de um bem
(imovel, veiculo...), geralmente com o proprio bem como garantia.

Diferenca chave em relacao a Emprestimo: o valor financiado normalmente NAO
passa pela conta do usuario no desembolso (vai direto pro vendedor/
financeira) - so a entrada (se houver) e as parcelas mensais geram
Transacao. Por isso e uma entidade separada de Emprestimo, apesar de
compartilhar os campos de contrato de credito (ver ContratoCreditoMixin).
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import ContratoCreditoMixin, TimestampMixin


class Financiamento(Base, TimestampMixin, ContratoCreditoMixin):
    __tablename__ = "financiamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    descricao: Mapped[str] = mapped_column(String(200))
    # valor do bem sendo financiado (base do contrato, antes da entrada)
    valor_financiado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    valor_entrada: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # ex: "Apartamento Rua X", "Veiculo ABC-1234" - livre, so descritivo
    bem_financiado: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- relacionamentos ---
    # conta_id/categoria_id vem do ContratoCreditoMixin
    usuario: Mapped["Usuario"] = relationship(back_populates="financiamentos")
    conta: Mapped["Conta | None"] = relationship(back_populates="financiamentos")
    categoria: Mapped["Categoria | None"] = relationship(back_populates="financiamentos")

    # parcelas concretas pagas (uma Transacao por parcela, via financiamento_id)
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="financiamento")
