"""Model Alerta - regra de notificacao configurada pelo usuario
(ex: "avise quando o cartao passar de 90% do limite").

`entidade_tipo` + `entidade_id` formam uma referencia POLIMORFICA leve: em
vez de uma coluna de FK opcional para CADA tabela que pode gerar um alerta
(cartao_id, meta_id, conta_recorrente_id, ...), guardamos o nome da
entidade e o id dela. Nao e uma ForeignKey de verdade no banco (SQL nao
suporta FK para "tabela variavel"), entao a integridade referencial aqui e
garantida pela camada de servico, nao pelo schema - e uma troca deliberada
de rigidez por flexibilidade/extensibilidade (novos tipos de alerta nao
exigem migration nem coluna nova).
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TipoAlerta, TipoEntidadeReferenciavel
from app.models.mixins import TimestampMixin


class Alerta(Base, TimestampMixin):
    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    tipo: Mapped[TipoAlerta] = mapped_column()

    # referencia polimorfica opcional: alguns tipos de alerta (ex: SALDO_BAIXO
    # considerando todas as contas) nao precisam apontar pra uma entidade especifica.
    entidade_tipo: Mapped[TipoEntidadeReferenciavel | None] = mapped_column(nullable=True)
    entidade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # parametro do gatilho, formato depende do `tipo` (ex: um JSON serializado
    # como texto: '{"limite_percentual": 90}' para LIMITE_CARTAO). Guardado
    # como string simples aqui; o parse/validacao fica na camada de servico.
    condicao: Mapped[str | None] = mapped_column(String(500), nullable=True)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultima_disparada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="alertas")
