"""Model Parcelamento - compra dividida em parcelas (cartao de credito ou
parcelamento direto com o lojista), SEM ser um contrato de credito formal.

Financiamento e Emprestimo (contratos de credito, com instituicao
financeira, CET, sistema de amortizacao e saldo devedor proprios) sao
entidades separadas - ver app/models/financiamento.py e
app/models/emprestimo.py. Um Parcelamento nao tem nada disso: e so "esse
valor foi dividido em N vezes iguais", igual comprar em 10x no cartao.

Cada parcela concreta (com data e valor propios) e uma linha em Transacao
com `parcelamento_id` preenchido - o Parcelamento em si e so o "cabecalho"
que agrupa as parcelas para relatorios e para saber o total ainda devido.
Ver docs/analise-arquitetural-parcelamento.md para o desenho completo.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Parcelamento(Base, TimestampMixin):
    __tablename__ = "parcelamentos"
    __table_args__ = (
        # um parcelamento pertence a um Cartao OU a uma Conta, nunca aos
        # dois nem a nenhum dos dois - mesmo raciocinio (e mesmo formato)
        # do ck_transacao_conta_xor_cartao ja existente em Transacao. Achado
        # da analise arquitetural: essa exclusao mutua nunca tinha sido
        # garantida no banco antes desta etapa.
        CheckConstraint(
            "(cartao_id IS NOT NULL AND conta_id IS NULL) OR "
            "(cartao_id IS NULL AND conta_id IS NOT NULL)",
            name="ck_parcelamento_cartao_xor_conta",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    descricao: Mapped[str] = mapped_column(String(200))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    num_parcelas: Mapped[int] = mapped_column(Integer)
    # juros simples eventualmente embutido pelo lojista/cartao (parcelamento
    # "com juros"), nao um contrato de credito - por isso opcional e sem os
    # campos de CET/amortizacao que Financiamento/Emprestimo tem. Puramente
    # informativo: valor_total ja e o valor final a pagar, nenhum calculo
    # deste projeto deriva nada a partir de taxa_juros.
    taxa_juros: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    data_inicio: Mapped[date] = mapped_column(Date)
    # True = parcelamento em vigor (tem parcelas futuras esperadas);
    # False = cancelado (ParcelamentoService.cancelar) - nunca reaproveitado
    # para representar "quitado", que e um estado derivado, nao gravado
    # (mesmo raciocinio de StatusFatura: so o que e evento real vira coluna).
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    cartao_id: Mapped[int | None] = mapped_column(ForeignKey("cartoes.id"), nullable=True)
    conta_id: Mapped[int | None] = mapped_column(ForeignKey("contas.id"), nullable=True)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="parcelamentos")
    cartao: Mapped["Cartao | None"] = relationship(back_populates="parcelamentos")
    conta: Mapped["Conta | None"] = relationship(back_populates="parcelamentos")
    categoria: Mapped["Categoria | None"] = relationship(back_populates="parcelamentos")

    # todas as parcelas concretas (uma Transacao por parcela)
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="parcelamento")
