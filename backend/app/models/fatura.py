"""Model Fatura - representa um ciclo de fechamento do cartao de credito.

Sem esta entidade, so daria pra saber "quanto foi gasto no cartao" somando
transacoes na hora de exibir a tela (calculo repetido, sem historico de
status). Com Fatura, cada ciclo mensal vira um registro com status proprio,
permitindo alertas de vencimento e reconciliacao de pagamento.

`data_fechamento`/`data_vencimento` nunca sao valores livres vindos do
cliente - sao sempre derivadas de `Cartao.dia_fechamento`/`dia_vencimento`
por `FaturaService.criar()` no momento em que o ciclo e criado.

Pagamento (total ou parcial) NAO usa uma FK aqui (`Fatura -> Transacao`) -
usa o caminho oposto: `Transacao.fatura_paga_id` (varias transacoes de
pagamento podem apontar para a mesma fatura, permitindo pagamento
parcial/multiplo). Isso elimina a dependencia ciclica que existia antes
entre Fatura e Transacao (nao precisa mais de `use_alter=True`/batch para
fechar o ciclo de FKs) - ver docs/analise-arquitetural-fatura.md.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StatusFatura
from app.models.mixins import TimestampMixin


class Fatura(Base, TimestampMixin):
    __tablename__ = "faturas"
    __table_args__ = (
        # nao pode existir duas faturas do mesmo cartao para o mesmo mes de referencia
        UniqueConstraint("cartao_id", "mes_referencia", name="uq_fatura_cartao_mes"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cartao_id: Mapped[int] = mapped_column(ForeignKey("cartoes.id", ondelete="CASCADE"), index=True)

    # primeiro dia do mes de referencia (ex: 2026-07-01 representa a fatura de julho/2026)
    mes_referencia: Mapped[date] = mapped_column(Date)
    data_fechamento: Mapped[date] = mapped_column(Date)
    data_vencimento: Mapped[date] = mapped_column(Date)

    # snapshot do total da fatura no momento do fechamento - permanece NULL
    # enquanto ABERTA (o "valor em aberto" nesse periodo e calculado por
    # FaturaService, nunca armazenado). Uma vez preenchido (no fechamento),
    # este valor e congelado para sempre - nunca mais recalculado, mesmo
    # que algo mudasse depois (documento financeiro historico, mesma
    # excecao ja aplicada a saldo_devedor em ContratoCreditoMixin).
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # so ABERTA/FECHADA sao gravadas de verdade aqui - ver docstring de
    # StatusFatura em app/models/enums.py.
    status: Mapped[StatusFatura] = mapped_column(default=StatusFatura.ABERTA)

    # True somente para faturas criadas via FaturaService.importar() - um
    # ciclo que ja aconteceu antes do usuario comecar a usar o app, com
    # valor_total informado diretamente (nunca derivado de Transacao real,
    # excecao deliberada - ver docstring de FaturaImportarCreate). Existe
    # so para o frontend poder comunicar "isto e um registro historico
    # reconstituido" (badge) - nao muda nenhum calculo de
    # FaturaService._com_valores_calculados, que ja trata valor_total
    # congelado da mesma forma em qualquer fatura nao-ABERTA.
    importada: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    # Valor que o usuario declara diretamente como "ja gasto neste ciclo",
    # SEM nenhuma Transacao por tras - pedido explicito do usuario:
    # "faltou a opcao do usuario poder informar o saldo ja utilizado do
    # cartao independentemente de transacoes". So faz sentido enquanto a
    # fatura esta ABERTA (FaturaService.ajustar_saldo_inicial bloqueia em
    # qualquer outro status - editar o "ponto de partida" de um ciclo ja
    # fechado/historico e o que FaturaImportarCreate ja resolve, de um
    # jeito diferente). Somado a soma real de Transacao em
    # FaturaService._com_valores_calculados (fatura ABERTA) e congelado
    # dentro de valor_total no fechamento (FaturaService.fechar) - depois
    # disso vira so parte do numero congelado, nunca mais lido
    # separadamente. Mesmo raciocinio de Conta.saldo_inicial: um numero
    # declarado pelo usuario, somado ao calculo real, nunca substituindo-o.
    ajuste_manual: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), server_default="0")

    # --- relacionamentos ---
    cartao: Mapped["Cartao"] = relationship(back_populates="faturas")

    # transacoes lancadas no cartao durante este ciclo (as compras em si).
    transacoes: Mapped[list["Transacao"]] = relationship(
        back_populates="fatura", foreign_keys="Transacao.fatura_id"
    )
