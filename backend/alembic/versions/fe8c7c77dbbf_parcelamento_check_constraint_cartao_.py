"""parcelamento: check constraint cartao xor conta, unique numero_parcela

Revision ID: fe8c7c77dbbf
Revises: 21b14915e6fe
Create Date: 2026-07-14 11:20:23.655295

Parte da modelagem de Parcelamento (ver
docs/analise-arquitetural-parcelamento.md): dois achados da analise
arquitetural corrigidos antes da implementacao do CRUD.

1. `Parcelamento.cartao_id`/`conta_id` nao tinham nenhuma exclusao mutua
   garantida no banco (diferente de `Transacao`, que ja tem
   `ck_transacao_conta_xor_cartao`) - novo `CheckConstraint`
   `ck_parcelamento_cartao_xor_conta` fecha essa lacuna.
2. Nova `UniqueConstraint(parcelamento_id, numero_parcela)` em `Transacao`
   impede duas linhas reivindicando a mesma parcela do mesmo Parcelamento
   (ex: duas linhas "3 de 10"). NULL nao colide consigo mesmo (comportamento
   padrao de UNIQUE), entao transacoes sem parcelamento_id nao sao afetadas.

O `CheckConstraint` foi adicionado a mao (autogenerate nao compara
CheckConstraint, mesma limitacao ja observada nas migrations anteriores);
a `UniqueConstraint` foi detectada automaticamente. Ambas as operacoes
usam `batch_alter_table` (SQLite nao suporta ADD CONSTRAINT fora de modo
batch), mesma estrategia das migrations de Cartao/Fatura/Transacao.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe8c7c77dbbf'
down_revision: Union[str, None] = '21b14915e6fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('parcelamentos') as batch_op:
        batch_op.create_check_constraint(
            'ck_parcelamento_cartao_xor_conta',
            "(cartao_id IS NOT NULL AND conta_id IS NULL) OR "
            "(cartao_id IS NULL AND conta_id IS NOT NULL)",
        )

    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.create_unique_constraint(
            'uq_transacao_parcelamento_numero_parcela', ['parcelamento_id', 'numero_parcela']
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('uq_transacao_parcelamento_numero_parcela', type_='unique')

    with op.batch_alter_table('parcelamentos') as batch_op:
        batch_op.drop_constraint('ck_parcelamento_cartao_xor_conta', type_='check')
