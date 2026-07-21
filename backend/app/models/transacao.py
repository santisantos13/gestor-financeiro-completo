"""Model Transacao - o coracao do sistema: toda entrada ou saida REAL de
dinheiro passa por aqui.

Em vez de tabelas separadas "Receita" e "Despesa", uma unica Transacao com
o campo `tipo` representa as duas coisas - "registrar um lancamento
financeiro" e uma unica responsabilidade, independente do sinal do valor.

Transferencias entre contas proprias do usuario NAO passam por aqui (ver
model Transferencia), para nao inflar relatorios de receita/despesa com
dinheiro que so mudou de lugar sem afetar o patrimonio total do usuario.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import transacao_tag
from app.models.enums import StatusTransacao, TipoTransacao
from app.models.meta import Meta  # noqa: F401 - necessario para resolver o forward ref "Meta | None" abaixo
from app.models.mixins import TimestampMixin


class Transacao(Base, TimestampMixin):
    __tablename__ = "transacoes"
    __table_args__ = (
        # uma transacao pertence a uma Conta OU a um Cartao, nunca aos dois
        # nem a nenhum dos dois. Garantido no nivel do banco (nao so na
        # aplicacao), para o dado nunca ficar inconsistente.
        CheckConstraint(
            "(conta_id IS NOT NULL AND cartao_id IS NULL) OR "
            "(conta_id IS NULL AND cartao_id IS NOT NULL)",
            name="ck_transacao_conta_xor_cartao",
        ),
        # uma parcela pertence a NO MAXIMO um "contrato" por vez - nunca
        # pode ser parcela de um Parcelamento E de um Financiamento ao
        # mesmo tempo, por exemplo. (conta como "0 ou 1 preenchido": soma
        # das flags de nulidade tem que ser >= 2 dos 3 campos nulos)
        CheckConstraint(
            "(CASE WHEN parcelamento_id IS NOT NULL THEN 1 ELSE 0 END + "
            " CASE WHEN financiamento_id IS NOT NULL THEN 1 ELSE 0 END + "
            " CASE WHEN emprestimo_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="ck_transacao_no_maximo_um_contrato",
        ),
        # uma transacao nunca e simultaneamente "uma compra que pertence a
        # um ciclo" (fatura_id) e "um pagamento que quita um ciclo"
        # (fatura_paga_id) - papeis mutuamente exclusivos. Ver
        # docs/analise-arquitetural-fatura.md.
        CheckConstraint(
            "NOT (fatura_id IS NOT NULL AND fatura_paga_id IS NOT NULL)",
            name="ck_transacao_fatura_compra_xor_pagamento",
        ),
        # numero_parcela so faz sentido (e so pode ser preenchido) quando a
        # transacao e de fato uma parcela de algum "contrato" (Parcelamento,
        # Financiamento ou Emprestimo) - nunca preenchido numa transacao
        # avulsa, nunca nulo numa transacao que pertence a um desses tres.
        # Ver docs/analise-arquitetural-transacao.md.
        CheckConstraint(
            "(CASE WHEN "
            "   (parcelamento_id IS NOT NULL OR financiamento_id IS NOT NULL OR emprestimo_id IS NOT NULL) "
            "  THEN numero_parcela IS NOT NULL "
            "  ELSE numero_parcela IS NULL "
            " END)",
            name="ck_transacao_numero_parcela_condiz_com_contrato",
        ),
        # duas parcelas do MESMO Parcelamento nunca podem reivindicar o
        # mesmo numero_parcela (ex: duas linhas "3 de 10") - achado da
        # analise arquitetural de Parcelamento. NULL nao colide consigo
        # mesmo (comportamento padrao de UNIQUE), entao nao afeta
        # transacoes sem parcelamento_id. Ver
        # docs/analise-arquitetural-parcelamento.md.
        UniqueConstraint(
            "parcelamento_id", "numero_parcela", name="uq_transacao_parcelamento_numero_parcela"
        ),
        # duas ocorrencias da MESMA ContaRecorrente nunca podem cair na
        # mesma data - mesma familia da constraint acima, mesma licao
        # aprendida na revisao tecnica de Parcelamento (o UniqueConstraint
        # do banco e a rede de seguranca; ContaRecorrenteService ja evita
        # gerar a duplicata antes de chegar aqui). NULL nao colide consigo
        # mesmo, entao transacoes sem origem_recorrente_id nao sao afetadas.
        # Ver docs/analise-arquitetural-conta-recorrente.md.
        UniqueConstraint(
            "origem_recorrente_id", "data", name="uq_transacao_origem_recorrente_data"
        ),
        # duas parcelas do MESMO Financiamento nunca podem reivindicar o
        # mesmo numero_parcela - mesma familia da constraint de
        # Parcelamento acima, aplicada proativamente (sem esperar
        # descobrir o mesmo bug de novo). NULL nao colide consigo mesmo,
        # entao transacoes sem financiamento_id nao sao afetadas. Ver
        # docs/analise-arquitetural-financiamento.md.
        UniqueConstraint(
            "financiamento_id", "numero_parcela", name="uq_transacao_financiamento_numero_parcela"
        ),
        # duas parcelas do MESMO Emprestimo nunca podem reivindicar o mesmo
        # numero_parcela - mesma familia das constraints acima, aplicada
        # proativamente. NULL nao colide consigo mesmo, entao transacoes
        # sem emprestimo_id nao sao afetadas. Ver
        # docs/analise-arquitetural-emprestimo.md.
        UniqueConstraint(
            "emprestimo_id", "numero_parcela", name="uq_transacao_emprestimo_numero_parcela"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    tipo: Mapped[TipoTransacao] = mapped_column()
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data: Mapped[date] = mapped_column(Date, index=True)
    descricao: Mapped[str] = mapped_column(String(200))
    status: Mapped[StatusTransacao] = mapped_column(default=StatusTransacao.PENDENTE)

    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)
    conta_id: Mapped[int | None] = mapped_column(ForeignKey("contas.id", ondelete="CASCADE"), nullable=True)
    cartao_id: Mapped[int | None] = mapped_column(ForeignKey("cartoes.id", ondelete="CASCADE"), nullable=True)

    # preenchido quando esta transacao e uma parcela concreta de um Parcelamento
    # (compra dividida, sem ser um contrato de credito formal)
    parcelamento_id: Mapped[int | None] = mapped_column(ForeignKey("parcelamentos.id", ondelete="SET NULL"), nullable=True)
    # preenchido quando e uma parcela de um Financiamento (contrato de credito
    # atrelado a um bem)
    financiamento_id: Mapped[int | None] = mapped_column(ForeignKey("financiamentos.id", ondelete="SET NULL"), nullable=True)
    # preenchido quando e uma parcela (ou o desembolso) de um Emprestimo
    emprestimo_id: Mapped[int | None] = mapped_column(ForeignKey("emprestimos.id", ondelete="SET NULL"), nullable=True)
    numero_parcela: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # preenchido quando esta transacao foi gerada automaticamente a partir
    # de uma ContaRecorrente (aluguel, assinatura, salario...)
    origem_recorrente_id: Mapped[int | None] = mapped_column(
        ForeignKey("contas_recorrentes.id", ondelete="SET NULL"), nullable=True
    )

    # preenchido quando esta transacao e um aporte/contribuicao para uma Meta
    meta_id: Mapped[int | None] = mapped_column(ForeignKey("metas.id", ondelete="SET NULL"), nullable=True)

    # preenchido quando a transacao foi feita no cartao: indica a QUAL
    # fatura (ciclo de fechamento) ela pertence - esta transacao e uma
    # COMPRA daquele ciclo.
    fatura_id: Mapped[int | None] = mapped_column(
        ForeignKey("faturas.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # preenchido quando esta transacao e um PAGAMENTO (total ou parcial) de
    # uma fatura - sempre uma despesa numa Conta (nunca num Cartao). Varias
    # transacoes podem apontar para a mesma fatura (pagamento parcial em
    # mais de uma vez). Mutuamente exclusivo com fatura_id (ver
    # CheckConstraint acima) - uma linha nunca e compra E pagamento ao
    # mesmo tempo.
    fatura_paga_id: Mapped[int | None] = mapped_column(
        ForeignKey("faturas.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # True somente para parcelas de Financiamento/Emprestimo geradas pelo
    # loop de onboarding "parcelas_ja_pagas" em
    # FinanciamentoService.criar()/EmprestimoService.criar() - representa
    # um pagamento que aconteceu ANTES do usuario comecar a usar o app
    # (dado historico "reconstituido", mesmo espirito de `Fatura.importada`).
    # Por isso NUNCA entra em `ContaRepository.somar_transacoes_pagas` (ver
    # docstring la): o usuario decide se a conta esta negativa ou nao a
    # partir de agora, sem deducao automatica de historico pre-app. Uma
    # parcela paga organicamente pelo botao "Pagar" da UI (mesmo depois,
    # inclusive numeros de parcela "atrasados") nunca tem este campo
    # marcado - so o loop de onboarding o marca, num unico lugar.
    importada: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="transacoes")
    categoria: Mapped["Categoria | None"] = relationship(back_populates="transacoes")
    conta: Mapped["Conta | None"] = relationship(back_populates="transacoes")
    cartao: Mapped["Cartao | None"] = relationship(back_populates="transacoes")
    parcelamento: Mapped["Parcelamento | None"] = relationship(back_populates="transacoes")
    financiamento: Mapped["Financiamento | None"] = relationship(back_populates="transacoes")
    emprestimo: Mapped["Emprestimo | None"] = relationship(back_populates="transacoes")
    origem_recorrente: Mapped["ContaRecorrente | None"] = relationship(back_populates="transacoes_geradas")
    meta: Mapped["Meta | None"] = relationship(back_populates="transacoes")

    # foreign_keys explicito: existe OUTRO caminho entre Transacao e Fatura
    # (fatura_paga_id logo acima), entao o SQLAlchemy precisa saber
    # exatamente qual coluna usar para cada relationship.
    fatura: Mapped["Fatura | None"] = relationship(back_populates="transacoes", foreign_keys=[fatura_id])

    tags: Mapped[list["Tag"]] = relationship(secondary=transacao_tag, back_populates="transacoes")

    # anexos (comprovantes, notas fiscais...) - Transacao e dona exclusiva:
    # cascade="all, delete-orphan" porque um Anexo nunca faz sentido sem a
    # Transacao que ele documenta, e Transacao usa hard delete (sem soft
    # delete) - ver docs/analise-arquitetural-anexo.md.
    anexos: Mapped[list["Anexo"]] = relationship(back_populates="transacao", cascade="all, delete-orphan")
