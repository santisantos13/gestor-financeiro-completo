"""Model ContaRecorrente - "template" de lancamento que se repete
periodicamente: aluguel, salario, assinaturas (Netflix, academia...).

Nao e ela mesma um lancamento de caixa: ela e o TEMPLATE, e a Transacao
gerada para cada ocorrencia (marcando `origem_recorrente_id`) e quem
carrega o efeito financeiro de verdade - fonte da verdade de saldo e
relatorios continua sendo exclusivamente Transacao, exatamente como
Parcelamento (ver docs/analise-arquitetural-conta-recorrente.md).

Geracao e SEMPRE sob demanda (lazy), nunca por scheduler/cron/job: uma
ocorrencia so e gerada quando `ContaRecorrenteService` e chamado
explicitamente (na criacao do template, via
`POST /contas-recorrentes/{id}/gerar-ocorrencias-pendentes`, ou pela
sincronizacao global `POST /contas-recorrentes/sincronizar`), e apenas para
datas ja vencidas (<= hoje).

Expansao 2026-07-20 (docs/analise-arquitetural-conta-recorrente-expansao.md,
aprovada pelo usuario): todas as 8 frequencias suportadas via
`app/core/datas.avancar_data` (funcao unica); `proxima_execucao` e o cursor
MATERIALIZADO de geracao (substitui derivar a proxima data da ultima
Transacao gerada - que recriava ocorrencias excluidas de proposito e
explodia em catch-up ao reativar uma pausa); `status`
(ATIVA/PAUSADA/ENCERRADA) substitui o booleano `ativo`; `dia_vencimento`
virou opcional (so se aplica a frequencias baseadas em meses - nas
baseadas em dias a ancora e a propria `data_inicio`).
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FrequenciaRecorrencia, StatusRecorrencia, TipoTransacao
from app.models.mixins import TimestampMixin


class ContaRecorrente(Base, TimestampMixin):
    __tablename__ = "contas_recorrentes"
    __table_args__ = (
        # mesma familia do ck_parcelamento_cartao_xor_conta: uma recorrencia
        # pertence a uma Conta OU a um Cartao, nunca aos dois nem a nenhum -
        # lacuna de modelagem encontrada na analise arquitetural (o model
        # original nao tinha nenhuma exclusao mutua garantida no banco).
        CheckConstraint(
            "(conta_id IS NOT NULL AND cartao_id IS NULL) OR "
            "(conta_id IS NULL AND cartao_id IS NOT NULL)",
            name="ck_conta_recorrente_cartao_xor_conta",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    descricao: Mapped[str] = mapped_column(String(200))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tipo: Mapped[TipoTransacao] = mapped_column()
    frequencia: Mapped[FrequenciaRecorrencia] = mapped_column(default=FrequenciaRecorrencia.MENSAL)
    # dia do mes (1-31). So se aplica a frequencias baseadas em MESES
    # (MENSAL/BIMESTRAL/TRIMESTRAL/SEMESTRAL/ANUAL) - nulo obrigatorio nas
    # baseadas em dias (DIARIA/SEMANAL/QUINZENAL), onde a ancora e a
    # propria data_inicio. Validado por familia no Service.
    dia_vencimento: Mapped[int | None] = mapped_column(Integer, nullable=True)

    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True)
    conta_id: Mapped[int | None] = mapped_column(ForeignKey("contas.id"), nullable=True)
    cartao_id: Mapped[int | None] = mapped_column(ForeignKey("cartoes.id"), nullable=True)

    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)  # nulo = sem data de termino

    # Cursor MATERIALIZADO de geracao: a proxima data que AINDA NAO virou
    # Transacao. Avanca a cada geracao (via `avancar_data`), nunca olha
    # para tras - excluir uma ocorrencia gerada nao a ressuscita, e
    # reativar uma pausa pula o periodo pausado em vez de gerar retroativos
    # (decisoes do usuario, 2026-07-20). Tambem e o indice natural de
    # lembretes futuros ("o que vence ate D+N" = query por esta coluna).
    proxima_execucao: Mapped[date] = mapped_column(Date)

    # ATIVA/PAUSADA/ENCERRADA - substitui o booleano `ativo` (que
    # conflacionava pausa e encerramento). ENCERRADA e terminal.
    status: Mapped[StatusRecorrencia] = mapped_column(default=StatusRecorrencia.ATIVA)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="contas_recorrentes")
    categoria: Mapped["Categoria | None"] = relationship(back_populates="contas_recorrentes")
    conta: Mapped["Conta | None"] = relationship(back_populates="contas_recorrentes")
    cartao: Mapped["Cartao | None"] = relationship(back_populates="contas_recorrentes")

    # ocorrencias ja geradas como Transacao concreta
    transacoes_geradas: Mapped[list["Transacao"]] = relationship(back_populates="origem_recorrente")
