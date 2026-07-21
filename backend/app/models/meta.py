"""Model Meta - objetivo de economia definido pelo usuario
(ex: "Viagem para o Japao - R$ 15.000 ate dezembro/2027").

Nao guarda `valor_atual` como coluna: o progresso e sempre calculado pela
camada de servico. Duas fontes somadas (ver `MetaService._com_progresso`):
(1) `Transacao.valor` onde `meta_id` aponta pra essa Meta - o mecanismo
ORIGINAL, hoje CONGELADO (nenhuma Transacao nova pode mais ser marcada
assim, so as antigas continuam contando, ver
docs/analise-arquitetural-metas-transferencias.md, secao 6); (2) o saldo do
"cofrinho" - a Conta dedicada e oculta apontada por `conta_id` - via
`Transferencia`, o mecanismo NOVO (Refinamento de Metas: aportes/resgates).

`conta_id` deixou de ser opcional/organizacional (decisao original em
docs/analise-arquitetural-meta.md): toda Meta agora tem, sempre, uma Conta
dedicada e oculta, criada automaticamente por `MetaService.criar` - o
usuario nunca escolhe nem ve essa conta diretamente. Ver
docs/analise-arquitetural-metas-transferencias.md, secao 2.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FrequenciaContribuicao
from app.models.mixins import TimestampMixin


class Meta(Base, TimestampMixin):
    __tablename__ = "metas"
    __table_args__ = (
        # o mesmo usuario nao pode ter duas metas com a mesma descricao.
        # Vale inclusive para metas desativadas - o Service resolve esse
        # caso reativando a meta existente em vez de tentar inserir uma
        # linha nova (ver MetaService.criar), mesmo padrao de
        # Tag/Cartao - a constraint nunca chega a ser violada por um fluxo
        # normal de "recriar" uma meta apagada.
        UniqueConstraint("usuario_id", "descricao", name="uq_meta_usuario_descricao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    descricao: Mapped[str] = mapped_column(String(200))
    valor_alvo: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data_alvo: Mapped[date | None] = mapped_column(Date, nullable=True)
    # conta "cofrinho" dedicada a essa meta - SEMPRE preenchida (auto-
    # provisionada por MetaService.criar), nunca escolhida pelo usuario.
    conta_id: Mapped[int] = mapped_column(ForeignKey("contas.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Periodicidade de contribuição planejada, opcional - ver
    # docs/analise-arquitetural-metas-refinamento.md, seção 1.1. Só
    # alimenta `MetaService`/`contribuicao_sugerida_por_periodo`; nunca
    # valida/bloqueia nada, mesmo raciocínio de `conta_id` (referência
    # organizacional, sem regra de negócio presa a ela).
    frequencia_contribuicao: Mapped[FrequenciaContribuicao | None] = mapped_column(
        Enum(FrequenciaContribuicao), nullable=True
    )

    # Data em que `percentual` cruzou 100% PELA PRIMEIRA VEZ - nunca
    # desfeito depois, mesmo que uma retirada derrube o percentual de
    # volta (é um fato histórico: "essa meta já foi concluída uma vez").
    # Gravado lazily por `MetaService._com_progresso` na primeira leitura
    # em que a transição é observada (Meta não tem uma ação explícita de
    # "concluir" vinda do usuário - ver docs/analise-arquitetural-metas-refinamento.md,
    # seção 4.1, para o raciocínio completo desse gatilho).
    concluida_em: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="metas")
    conta: Mapped["Conta"] = relationship(back_populates="metas")

    # aportes: transacoes marcadas com meta_id = esta meta
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="meta")
