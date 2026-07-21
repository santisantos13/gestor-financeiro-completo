"""anexo: redesenho para posse transitiva via transacao

Revision ID: 5bf719e3a7a3
Revises: e91ffcf3761c
Create Date: 2026-07-15 11:35:44.951553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bf719e3a7a3'
down_revision: Union[str, None] = 'e91ffcf3761c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table: SQLite nao suporta DROP COLUMN/DROP CONSTRAINT
    # diretamente - o dialeto recria a tabela por baixo dos panos. Mesma
    # necessidade manual de sempre nas migrations deste projeto (autogenerate
    # nao usa batch mode por padrao). Anexo NUNCA teve CRUD/dado real
    # persistido nesta tabela ate agora (ver docs/analise-arquitetural-anexo.md),
    # entao nao ha necessidade de backfill para as colunas NOT NULL novas.
    with op.batch_alter_table('anexos') as batch_op:
        batch_op.add_column(sa.Column('transacao_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('nome_original', sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column('mime_type', sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column('data_upload', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False)
        )
        batch_op.add_column(sa.Column('ativo', sa.Boolean(), nullable=False))
        batch_op.drop_index('ix_anexos_usuario_id')
        batch_op.create_index(batch_op.f('ix_anexos_transacao_id'), ['transacao_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_anexos_transacao_id_transacoes', 'transacoes', ['transacao_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_column('entidade_tipo')
        batch_op.drop_column('entidade_id')
        batch_op.drop_column('criado_em')
        batch_op.drop_column('tipo_mime')
        # dropar usuario_id remove tambem a antiga ForeignKeyConstraint
        # (sem nome explicito na migration inicial - o dialeto SQLite nao
        # permite dropar essa constraint por nome de forma confiavel via
        # batch mode; dropar a coluna que ela referencia e suficiente e
        # mais seguro).
        batch_op.drop_column('usuario_id')
        batch_op.drop_column('nome_arquivo')


def downgrade() -> None:
    with op.batch_alter_table('anexos') as batch_op:
        batch_op.add_column(sa.Column('nome_arquivo', sa.VARCHAR(length=255), nullable=False))
        batch_op.add_column(sa.Column('usuario_id', sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column('tipo_mime', sa.VARCHAR(length=100), nullable=True))
        batch_op.add_column(
            sa.Column('criado_em', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False)
        )
        batch_op.add_column(sa.Column('entidade_id', sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column('entidade_tipo', sa.VARCHAR(length=16), nullable=False))
        batch_op.create_foreign_key(
            'fk_anexos_usuario_id_usuarios', 'usuarios', ['usuario_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.drop_index(batch_op.f('ix_anexos_transacao_id'))
        batch_op.create_index('ix_anexos_usuario_id', ['usuario_id'], unique=False)
        batch_op.drop_column('ativo')
        batch_op.drop_column('data_upload')
        batch_op.drop_column('mime_type')
        batch_op.drop_column('nome_original')
        # dropar transacao_id remove tambem a ForeignKeyConstraint criada
        # no upgrade (mesmo raciocinio do upgrade acima).
        batch_op.drop_column('transacao_id')
