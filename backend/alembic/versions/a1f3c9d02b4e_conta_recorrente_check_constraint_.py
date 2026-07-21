"""conta recorrente: check constraint cartao xor conta, unique origem_recorrente+data

Revision ID: a1f3c9d02b4e
Revises: bfc086b70a32
Create Date: 2026-07-14 17:20:23.777015

Parte da modelagem de ContaRecorrente (ver
docs/analise-arquitetural-conta-recorrente.md): dois achados da analise
arquitetural corrigidos antes da implementacao do CRUD, mesmo par de
correcoes ja aplicado para Parcelamento (fe8c7c77dbbf).

1. `ContaRecorrente.conta_id`/`cartao_id` nao tinham nenhuma exclusao mutua
   garantida no banco - novo `CheckConstraint`
   `ck_conta_recorrente_cartao_xor_conta` fecha essa lacuna.
2. Nova `UniqueConstraint(origem_recorrente_id, data)` em `Transacao` impede
   duas ocorrencias geradas para a mesma data da mesma ContaRecorrente. NULL
   nao colide consigo mesmo, entao transacoes sem origem_recorrente_id nao
   sao afetadas.

O `CheckConstraint` foi adicionado a mao (autogenerate nao compara
CheckConstraint); a `UniqueConstraint` foi detectada automaticamente. Ambas
usam `batch_alter_table` (SQLite nao suporta ADD CONSTRAINT fora de modo
batch), mesma estrategia de fe8c7c77dbbf.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f3c9d02b4e'
down_revision: Union[str, None] = 'bfc086b70a32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('contas_recorrentes') as batch_op:
        batch_op.create_check_constraint(
            'ck_conta_recorrente_cartao_xor_conta',
            "(conta_id IS NOT NULL AND cartao_id IS NULL) OR "
            "(conta_id IS NULL AND cartao_id IS NOT NULL)",
        )

    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.create_unique_constraint(
            'uq_transacao_origem_recorrente_data', ['origem_recorrente_id', 'data']
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('uq_transacao_origem_recorrente_data', type_='unique')

    with op.batch_alter_table('contas_recorrentes') as batch_op:
        batch_op.drop_constraint('ck_conta_recorrente_cartao_xor_conta', type_='check')
