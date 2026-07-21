"""tag soft delete

Revision ID: 75bf54bdf7ff
Revises: 7c04a41962ca
Create Date: 2026-07-13 11:04:02.339573

Adiciona `tags.ativo` (soft delete) - a Tag ainda nao tinha essa coluna
quando o modelo inicial foi criado. `server_default` garante que a coluna
NOT NULL possa ser adicionada mesmo se a tabela ja tiver linhas (tags
existentes viram ativo=True, mesmo comportamento do default Python da
coluna para linhas novas).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75bf54bdf7ff'
down_revision: Union[str, None] = '7c04a41962ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tags', sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column('tags', 'ativo')
