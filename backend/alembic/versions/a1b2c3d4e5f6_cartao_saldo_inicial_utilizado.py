"""cartao: campo saldo_inicial_utilizado (Estado Inicial do Cartao)

Revision ID: a1b2c3d4e5f6
Revises: f2a5c8e1b3d7
Create Date: 2026-07-19 00:00:00.000000

Parte da Sprint de Refinamento Premium (ver
docs/analise-arquitetural-sprint-refinamento-premium.md, secao 1):
substitui o fluxo em que declarar "saldo ja utilizado" ao cadastrar um
cartao criava, nos bastidores, uma Fatura do mes corrente so para guardar
`Fatura.ajuste_manual` - confuso para o usuario ("virou uma fatura que o
sistema criou sozinho"). `cartoes.saldo_inicial_utilizado` e um valor
declarado direto no Cartao, sem nenhum ciclo/Fatura por tras, consumindo
`limite_disponivel` permanentemente ate o usuario editar/zerar.

`ajuste_manual` de Fatura continua existindo e intocado - segue valido
para ajustar um ciclo ja aberto especifico (uso diferente, nao mais usado
como mecanismo de "saldo inicial" do cartao).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f2a5c8e1b3d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('cartoes', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'saldo_inicial_utilizado',
                sa.Numeric(precision=12, scale=2),
                nullable=False,
                server_default='0',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('cartoes', schema=None) as batch_op:
        batch_op.drop_column('saldo_inicial_utilizado')
