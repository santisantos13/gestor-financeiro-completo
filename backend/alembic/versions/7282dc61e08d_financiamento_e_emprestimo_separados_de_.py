"""financiamento e emprestimo separados de parcelamento

Revision ID: 7282dc61e08d
Revises: f988db1c148b
Create Date: 2026-07-12 18:25:26.960806

Contexto: Financiamento e Emprestimo deixam de ser um `tipo` dentro de
Parcelamento e viram tabelas proprias (contrato de credito formal, com
instituicao financeira, CET, sistema de amortizacao e saldo devedor).
Parcelamento passa a representar so compra dividida (cartao/lojista), por
isso perde as colunas `tipo` e `credor`. Transacao ganha `financiamento_id`
e `emprestimo_id`, e uma CHECK constraint nova garante que uma transacao
pertence a no maximo um "contrato" (parcelamento OU financiamento OU
emprestimo, nunca mais de um).

Observacao tecnica: SQLite nao suporta ALTER TABLE ADD CONSTRAINT nem
DROP COLUMN em todos os casos de forma direta - por isso as mudancas em
`transacoes` e `parcelamentos` usam o modo batch do Alembic (recria a
tabela nos bastidores com as colunas/constraints corretas).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7282dc61e08d'
down_revision: Union[str, None] = 'f988db1c148b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) novas tabelas de contrato de credito - nao tem dependencia ciclica
    # nenhuma, entao nascem antes de mexer em transacoes.
    op.create_table('emprestimos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=False),
    sa.Column('valor_liberado', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('finalidade', sa.String(length=120), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('instituicao_financeira', sa.String(length=120), nullable=False),
    sa.Column('numero_contrato', sa.String(length=60), nullable=True),
    sa.Column('taxa_juros', sa.Numeric(precision=6, scale=4), nullable=False),
    sa.Column('sistema_amortizacao', sa.Enum('PRICE', 'SAC', name='sistemaamortizacao'), nullable=False),
    sa.Column('num_parcelas', sa.Integer(), nullable=False),
    sa.Column('cet', sa.Numeric(precision=6, scale=4), nullable=True),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('saldo_devedor', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('permite_quitacao_antecipada', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('ATIVO', 'QUITADO', 'INADIMPLENTE', name='statuscontratocredito'), nullable=False),
    sa.Column('conta_id', sa.Integer(), nullable=True),
    sa.Column('categoria_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_emprestimos_usuario_id'), 'emprestimos', ['usuario_id'], unique=False)

    op.create_table('financiamentos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=False),
    sa.Column('valor_financiado', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('valor_entrada', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('bem_financiado', sa.String(length=200), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('instituicao_financeira', sa.String(length=120), nullable=False),
    sa.Column('numero_contrato', sa.String(length=60), nullable=True),
    sa.Column('taxa_juros', sa.Numeric(precision=6, scale=4), nullable=False),
    sa.Column('sistema_amortizacao', sa.Enum('PRICE', 'SAC', name='sistemaamortizacao'), nullable=False),
    sa.Column('num_parcelas', sa.Integer(), nullable=False),
    sa.Column('cet', sa.Numeric(precision=6, scale=4), nullable=True),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('saldo_devedor', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('permite_quitacao_antecipada', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('ATIVO', 'QUITADO', 'INADIMPLENTE', name='statuscontratocredito'), nullable=False),
    sa.Column('conta_id', sa.Integer(), nullable=True),
    sa.Column('categoria_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_financiamentos_usuario_id'), 'financiamentos', ['usuario_id'], unique=False)

    # 2) parcelamentos perde 'tipo' e 'credor' - modo batch porque SQLite
    # nao suporta DROP COLUMN combinado com o resto de forma direta em
    # todas as versoes.
    with op.batch_alter_table('parcelamentos') as batch_op:
        batch_op.drop_column('credor')
        batch_op.drop_column('tipo')

    # 3) transacoes ganha financiamento_id/emprestimo_id + a nova CHECK de
    # "no maximo um contrato por transacao". Tudo num unico batch pra
    # recriar a tabela uma vez so, nao uma vez por mudanca.
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.add_column(sa.Column('financiamento_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('emprestimo_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_transacoes_financiamento_id', 'financiamentos', ['financiamento_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_transacoes_emprestimo_id', 'emprestimos', ['emprestimo_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_check_constraint(
            'ck_transacao_no_maximo_um_contrato',
            "(CASE WHEN parcelamento_id IS NOT NULL THEN 1 ELSE 0 END + "
            " CASE WHEN financiamento_id IS NOT NULL THEN 1 ELSE 0 END + "
            " CASE WHEN emprestimo_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('ck_transacao_no_maximo_um_contrato', type_='check')
        batch_op.drop_constraint('fk_transacoes_emprestimo_id', type_='foreignkey')
        batch_op.drop_constraint('fk_transacoes_financiamento_id', type_='foreignkey')
        batch_op.drop_column('emprestimo_id')
        batch_op.drop_column('financiamento_id')

    with op.batch_alter_table('parcelamentos') as batch_op:
        # nullable=True aqui (mesmo o model original tendo 'tipo' NOT NULL)
        # porque um downgrade sobre uma tabela ja com dados nao teria valor
        # nenhum pra preencher a coluna nova - fica a cargo de quem reverter
        # a migration decidir o que fazer com linhas existentes.
        batch_op.add_column(sa.Column('tipo', sa.VARCHAR(length=13), nullable=True))
        batch_op.add_column(sa.Column('credor', sa.VARCHAR(length=120), nullable=True))

    op.drop_index(op.f('ix_financiamentos_usuario_id'), table_name='financiamentos')
    op.drop_table('financiamentos')
    op.drop_index(op.f('ix_emprestimos_usuario_id'), table_name='emprestimos')
    op.drop_table('emprestimos')
