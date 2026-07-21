"""meta: unique constraint descricao

Revision ID: e91ffcf3761c
Revises: 8411c7918413
Create Date: 2026-07-15 10:45:37.490696

Parte da modelagem de Meta (ver docs/analise-arquitetural-meta.md): nova
UniqueConstraint(usuario_id, descricao) em Meta impede duas metas do mesmo
usuario reivindicarem a mesma descricao - mesma familia das constraints de
nome unico ja aplicadas em Tag/Cartao, so que numa entidade nova em vez de
Transacao.

batch_alter_table usado por consistencia com as demais migrations deste
projeto (SQLite nao suporta ADD CONSTRAINT fora de modo batch) - o
autogenerate original nao usava batch mode e falhava com
"NotImplementedError: No support for ALTER of constraints in SQLite
dialect", corrigido manualmente aqui.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e91ffcf3761c'
down_revision: Union[str, None] = '8411c7918413'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('metas') as batch_op:
        batch_op.create_unique_constraint('uq_meta_usuario_descricao', ['usuario_id', 'descricao'])


def downgrade() -> None:
    with op.batch_alter_table('metas') as batch_op:
        batch_op.drop_constraint('uq_meta_usuario_descricao', type_='unique')
