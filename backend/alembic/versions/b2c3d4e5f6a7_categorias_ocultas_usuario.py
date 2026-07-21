"""categorias_ocultas_usuario: ocultar categoria de sistema por usuario

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-19 04:00:00.000000

Parte da Sprint de Refinamento Premium (ver
docs/analise-arquitetural-sprint-refinamento-premium.md, secao 4): categoria
de sistema (usuario_id nulo) e uma UNICA LINHA global, compartilhada por
todos os usuarios - nao pode ganhar um campo booleano simples de "oculta"
sem afetar todo mundo. Esta tabela nova registra, por usuario, quais
categorias de sistema ele pediu para nao ver mais - a linha de `categorias`
permanece intocada para todos os outros usuarios.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'categorias_ocultas_usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('categoria_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usuario_id', 'categoria_id', name='uq_categoria_oculta_usuario'),
    )
    with op.batch_alter_table('categorias_ocultas_usuario', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_categorias_ocultas_usuario_usuario_id'), ['usuario_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_categorias_ocultas_usuario_categoria_id'), ['categoria_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('categorias_ocultas_usuario', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categorias_ocultas_usuario_categoria_id'))
        batch_op.drop_index(batch_op.f('ix_categorias_ocultas_usuario_usuario_id'))
    op.drop_table('categorias_ocultas_usuario')
