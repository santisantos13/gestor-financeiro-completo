"""Model Emprestimo - contrato de credito de proposito geral (pessoal,
consignado, capital de giro...), sem estar atrelado a compra de um bem
especifico.

Diferenca chave em relacao a Financiamento: o valor liberado ENTRA na
conta do usuario no desembolso (vira uma Transacao de RECEITA), alem das
parcelas mensais que saem depois. Por isso e uma entidade separada de
Financiamento, apesar de compartilhar os campos de contrato de credito
(ver ContratoCreditoMixin).
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import ContratoCreditoMixin, TimestampMixin


class Emprestimo(Base, TimestampMixin, ContratoCreditoMixin):
    __tablename__ = "emprestimos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    descricao: Mapped[str] = mapped_column(String(200))
    # valor efetivamente liberado/recebido pelo usuario no desembolso
    valor_liberado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # ex: "consignado", "capital de giro", "pessoal" - livre, so descritivo
    finalidade: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- relacionamentos ---
    # conta_id/categoria_id vem do ContratoCreditoMixin
    usuario: Mapped["Usuario"] = relationship(back_populates="emprestimos")
    conta: Mapped["Conta | None"] = relationship(back_populates="emprestimos")
    categoria: Mapped["Categoria | None"] = relationship(back_populates="emprestimos")

    # parcelas concretas pagas (uma Transacao por parcela, via emprestimo_id).
    # a Transacao de desembolso (entrada do valor liberado) NAO usa esse
    # relacionamento - ela e uma Transacao normal, avulsa, que o Service
    # cria no momento da contratacao (fora do escopo desta etapa de modelagem).
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="emprestimo")
