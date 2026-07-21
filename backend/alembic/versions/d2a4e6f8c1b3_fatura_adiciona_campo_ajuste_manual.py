"""fatura: adiciona campo ajuste_manual

Revision ID: d2a4e6f8c1b3
Revises: c4d8e1a2f6b7
Create Date: 2026-07-18 00:00:00.000000

Adiciona `faturas.ajuste_manual` (Numeric(12,2), default 0) - pedido
explícito do usuário: "faltou a opção do usuário poder informar o saldo já
utilizado do cartão independentemente de transações". Mesmo raciocínio de
`contas.saldo_inicial`: um valor declarado diretamente pelo usuário, somado
ao cálculo real (soma de Transacao) em vez de substituí-lo, sem exigir
nenhuma Transacao por trás - diferente do botão "Registrar saldo já gasto
neste cartão" que já existia (esse cria uma Transacao real de ajuste).

Mesmo padrão de `server_default` já usado em `faturas.importada`/
`transacoes.importada`: garante que a coluna NOT NULL possa ser adicionada
com a tabela já tendo linhas (faturas existentes viram ajuste_manual=0).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2a4e6f8c1b3'
down_revision: Union[str, None] = 'c4d8e1a2f6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'faturas',
        sa.Column('ajuste_manual', sa.Numeric(12, 2), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('faturas', 'ajuste_manual')
