"""emprestimo: unique constraint numero_parcela

Revision ID: 8411c7918413
Revises: 8b100b274a2e
Create Date: 2026-07-15 08:44:32.035947

Parte da modelagem de Emprestimo (ver docs/analise-arquitetural-emprestimo.md):
mesma correcao proativa ja aplicada tres vezes (Parcelamento em
fe8c7c77dbbf, ContaRecorrente em a1f3c9d02b4e, Financiamento em
441dd71b0fe8) - nova UniqueConstraint(emprestimo_id, numero_parcela) em
Transacao impede duas parcelas do mesmo Emprestimo reivindicarem o mesmo
numero. NULL nao colide consigo mesmo, entao transacoes sem emprestimo_id
nao sao afetadas.

Detectada automaticamente pelo autogenerate; batch_alter_table usado por
consistencia com as demais migrations deste projeto (SQLite nao suporta
ADD CONSTRAINT fora de modo batch).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8411c7918413'
down_revision: Union[str, None] = '8b100b274a2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.create_unique_constraint(
            'uq_transacao_emprestimo_numero_parcela', ['emprestimo_id', 'numero_parcela']
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('uq_transacao_emprestimo_numero_parcela', type_='unique')
