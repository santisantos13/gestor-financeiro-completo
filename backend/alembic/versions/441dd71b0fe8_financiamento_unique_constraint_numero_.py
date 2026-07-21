"""financiamento: unique constraint numero_parcela

Revision ID: 441dd71b0fe8
Revises: a1f3c9d02b4e
Create Date: 2026-07-14 18:25:21.675148

Parte da modelagem de Financiamento (ver
docs/analise-arquitetural-financiamento.md): mesma correcao proativa ja
aplicada duas vezes (Parcelamento em fe8c7c77dbbf, ContaRecorrente em
a1f3c9d02b4e) - nova UniqueConstraint(financiamento_id, numero_parcela)
em Transacao impede duas parcelas do mesmo Financiamento reivindicarem o
mesmo numero. NULL nao colide consigo mesmo, entao transacoes sem
financiamento_id nao sao afetadas.

Detectada automaticamente pelo autogenerate; batch_alter_table usado por
consistencia com as demais migrations deste projeto (SQLite nao suporta
ADD CONSTRAINT fora de modo batch).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441dd71b0fe8'
down_revision: Union[str, None] = 'a1f3c9d02b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.create_unique_constraint(
            'uq_transacao_financiamento_numero_parcela', ['financiamento_id', 'numero_parcela']
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('uq_transacao_financiamento_numero_parcela', type_='unique')
