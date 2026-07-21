"""Mixins reutilizaveis entre os models do dominio.

Centraliza aqui campos que se repetem em mais de uma tabela, seguindo o
principio DRY: quem precisar deles so herda o mixin, em vez de redeclarar
as mesmas colunas em cada arquivo de model. Importante: um mixin aqui
compartilha DEFINICAO de coluna, nao comportamento/regra de negocio - isso
continua sendo responsabilidade de cada Service, nao do mixin.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enums import SistemaAmortizacao, StatusContratoCredito


class TimestampMixin:
    """Adiciona 'criado_em' e 'atualizado_em' preenchidos automaticamente."""

    # server_default=func.now() -> o proprio banco preenche a data na
    # insercao, nao depende do relogio da aplicacao.
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # onupdate=func.now() -> o SQLAlchemy atualiza este campo sozinho a
    # cada UPDATE feito na linha.
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ContratoCreditoMixin:
    """Campos comuns a qualquer contrato de credito formal (Financiamento e
    Emprestimo): dados do contrato em si, taxa/amortizacao e saldo devedor.

    Financiamento e Emprestimo tem a MESMA forma de contrato, mas relacoes
    diferentes com Transacao (emprestimo libera dinheiro na conta no
    desembolso, financiamento normalmente nao) e podem ganhar regras
    proprias no futuro (ex: margem consignavel so existe em emprestimo
    consignado) - por isso sao duas tabelas/Services separados em vez de
    uma so com um campo `tipo`, mesmo compartilhando estes campos aqui.
    """

    instituicao_financeira: Mapped[str] = mapped_column(String(120))
    numero_contrato: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # taxa de juros ao mes, ex: 0.0199 = 1,99% a.m.
    taxa_juros: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    sistema_amortizacao: Mapped[SistemaAmortizacao] = mapped_column(default=SistemaAmortizacao.PRICE)
    num_parcelas: Mapped[int] = mapped_column()

    # Custo Efetivo Total anual (%) - metrica regulatoria (Bacen) que resume
    # o custo total do credito (juros + tarifas + seguros); opcional porque
    # nem toda instituicao informa no momento do cadastro.
    cet: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)

    data_inicio: Mapped[date] = mapped_column(Date)

    # Diferente de Conta.saldo/Meta.progresso (sempre calculados, nunca
    # guardados), aqui o saldo devedor FICA armazenado e e atualizado pelo
    # Service a cada parcela paga. Motivo: com PRICE/SAC, saldo devedor nao
    # e "valor total menos soma das parcelas pagas" (parte de cada parcela
    # e juro, nao amortizacao) - recalcular exigiria rodar a formula de
    # amortizacao inteira a cada leitura. Guardar e manter atualizado
    # transacionalmente (mesma sessao do pagamento) e o mesmo trade-off que
    # sistemas bancarios reais fazem.
    saldo_devedor: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    permite_quitacao_antecipada: Mapped[bool] = mapped_column(default=True)
    status: Mapped[StatusContratoCredito] = mapped_column(default=StatusContratoCredito.ATIVO)

    # conta de onde saem as parcelas (e, no caso de Emprestimo, tambem pra
    # onde o valor liberado entra)
    conta_id: Mapped[int | None] = mapped_column(ForeignKey("contas.id"), nullable=True)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True
    )
