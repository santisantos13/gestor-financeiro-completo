"""Model Transferencia - movimentacao de dinheiro entre duas Contas do MESMO
usuario (ex: da conta corrente para a poupanca).

Fica FORA de Transacao DE PROPOSITO, decisao arquitetural deliberada e
reafirmada explicitamente na implementacao do CRUD (ver
docs/revisao-tecnica-transferencia.md): uma transferencia nao e receita nem
despesa (o patrimonio total do usuario nao muda, o dinheiro so troca de
lugar). Se fosse modelada como duas Transacoes (uma DESPESA, uma RECEITA),
relatorios de "quanto eu gastei no mes", categorias e metas - que so somam
Transacao - ficariam inflados/errados por dinheiro que nunca saiu do
patrimonio do usuario. Por isso NUNCA gera Transacao nenhuma: Transferencia
e, ela mesma, a fonte da verdade do proprio efeito financeiro (ver
`ContaRepository.somar_transferencias`, somada a `somar_transacoes_pagas`
em `ContaService._com_saldo` - duas fontes independentes, sem sobreposicao).

`ativo` (soft delete, mesmo padrao de Conta/Cartao/Tag) e o que permite
"cancelar" uma transferencia: a linha nunca e apagada (preserva o
historico), so some do calculo de saldo (`somar_transferencias` filtra
`ativo=True`) e da listagem padrao.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Transferencia(Base, TimestampMixin):
    __tablename__ = "transferencias"
    __table_args__ = (
        CheckConstraint("conta_origem_id != conta_destino_id", name="ck_transferencia_contas_distintas"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    conta_origem_id: Mapped[int] = mapped_column(ForeignKey("contas.id", ondelete="CASCADE"))
    conta_destino_id: Mapped[int] = mapped_column(ForeignKey("contas.id", ondelete="CASCADE"))

    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data: Mapped[date] = mapped_column(Date, index=True)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # True = transferencia em vigor (conta no calculo de saldo); False =
    # cancelada (TransferenciaService.cancelar) - preserva a linha para
    # historico, mas deixa de afetar saldo_atual das duas contas.
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="transferencias")

    # foreign_keys explicito: existem DUAS FKs para "contas" nesta tabela
    # (origem e destino) - o SQLAlchemy nao consegue adivinhar sozinho qual
    # usar em cada relationship sem essa indicacao.
    conta_origem: Mapped["Conta"] = relationship(foreign_keys=[conta_origem_id], back_populates="transferencias_enviadas")
    conta_destino: Mapped["Conta"] = relationship(foreign_keys=[conta_destino_id], back_populates="transferencias_recebidas")
