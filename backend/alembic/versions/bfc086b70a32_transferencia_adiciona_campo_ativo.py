"""transferencia: adiciona campo ativo

Revision ID: bfc086b70a32
Revises: fe8c7c77dbbf
Create Date: 2026-07-14 12:24:37.779090

Adiciona `transferencias.ativo` (soft delete) - decisão explícita do
usuário na implementação do CRUD de Transferência: a entidade continua
FORA de Transacao (nenhuma Transacao é gerada), então "cancelar" uma
transferência precisa de um jeito próprio de desfazer o efeito financeiro
preservando o histórico - mesmo padrão já usado em `tags.ativo`
(75bf54bdf7ff) e `cartoes.ativo`: `server_default` garante que a coluna
NOT NULL possa ser adicionada mesmo se a tabela já tiver linhas
(transferências existentes viram ativo=True, mesmo comportamento do
default Python da coluna para linhas novas).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfc086b70a32'
down_revision: Union[str, None] = 'fe8c7c77dbbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transferencias', sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column('transferencias', 'ativo')
