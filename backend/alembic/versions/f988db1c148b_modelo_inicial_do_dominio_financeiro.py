"""modelo inicial do dominio financeiro

Revision ID: f988db1c148b
Revises:
Create Date: 2026-07-12 10:51:25.608533

Observacao: a ordem das tabelas abaixo foi ajustada manualmente em relacao
ao que o --autogenerate produz por padrao. Faturas e Transacoes se
referenciam mutuamente (Transacao.fatura_id -> Fatura,
Fatura.transacao_pagamento_id -> Transacao), o que forma uma dependencia
ciclica que nenhum banco consegue resolver com CREATE TABLE simples. A
solucao e criar as duas tabelas primeiro (Fatura sem a FK de pagamento) e
so depois, com as duas ja existindo, adicionar essa FK especifica via
ALTER TABLE (op.create_foreign_key). O restante das tabelas segue a ordem
de dependencia normal (quem e referenciado nasce antes de quem referencia).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f988db1c148b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) tabelas sem dependencias de outras tabelas do dominio
    op.create_table('usuarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('senha_hash', sa.String(length=255), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)

    # 2) dependem so de usuarios (e de si mesmas, no caso de categorias)
    op.create_table('categorias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('categoria_pai_id', sa.Integer(), nullable=True),
    sa.Column('nome', sa.String(length=80), nullable=False),
    sa.Column('tipo', sa.Enum('RECEITA', 'DESPESA', 'AMBOS', name='tipocategoria'), nullable=False),
    sa.Column('cor', sa.String(length=7), nullable=True),
    sa.Column('icone', sa.String(length=40), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['categoria_pai_id'], ['categorias.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categorias_usuario_id'), 'categorias', ['usuario_id'], unique=False)

    op.create_table('contas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('tipo', sa.Enum('CORRENTE', 'POUPANCA', 'CARTEIRA', 'INVESTIMENTO', name='tipoconta'), nullable=False),
    sa.Column('saldo_inicial', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('instituicao', sa.String(length=120), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contas_usuario_id'), 'contas', ['usuario_id'], unique=False)

    op.create_table('tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=60), nullable=False),
    sa.Column('cor', sa.String(length=7), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('usuario_id', 'nome', name='uq_tag_usuario_nome')
    )
    op.create_index(op.f('ix_tags_usuario_id'), 'tags', ['usuario_id'], unique=False)

    op.create_table('alertas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('LIMITE_CARTAO', 'VENCIMENTO_FATURA', 'VENCIMENTO_CONTA_RECORRENTE', 'META_ATINGIDA', 'SALDO_BAIXO', name='tipoalerta'), nullable=False),
    sa.Column('entidade_tipo', sa.Enum('CONTA', 'CARTAO', 'FATURA', 'TRANSACAO', 'PARCELAMENTO', 'CONTA_RECORRENTE', 'META', name='tipoentidadereferenciavel'), nullable=True),
    sa.Column('entidade_id', sa.Integer(), nullable=True),
    sa.Column('condicao', sa.String(length=500), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('ultima_disparada_em', sa.DateTime(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alertas_usuario_id'), 'alertas', ['usuario_id'], unique=False)

    op.create_table('anexos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('entidade_tipo', sa.Enum('CONTA', 'CARTAO', 'FATURA', 'TRANSACAO', 'PARCELAMENTO', 'CONTA_RECORRENTE', 'META', name='tipoentidadereferenciavel'), nullable=False),
    sa.Column('entidade_id', sa.Integer(), nullable=False),
    sa.Column('nome_arquivo', sa.String(length=255), nullable=False),
    sa.Column('caminho_arquivo', sa.String(length=500), nullable=False),
    sa.Column('tipo_mime', sa.String(length=100), nullable=True),
    sa.Column('tamanho_bytes', sa.Integer(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anexos_usuario_id'), 'anexos', ['usuario_id'], unique=False)

    # 3) dependem de contas/usuarios
    op.create_table('cartoes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('conta_pagamento_id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('limite', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('dia_fechamento', sa.Integer(), nullable=False),
    sa.Column('dia_vencimento', sa.Integer(), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['conta_pagamento_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cartoes_usuario_id'), 'cartoes', ['usuario_id'], unique=False)

    op.create_table('metas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=False),
    sa.Column('valor_alvo', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('data_alvo', sa.Date(), nullable=True),
    sa.Column('conta_id', sa.Integer(), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metas_usuario_id'), 'metas', ['usuario_id'], unique=False)

    # 4) faturas depende de cartoes. A FK para transacoes (pagamento) e
    # adicionada mais abaixo via ALTER TABLE, depois que 'transacoes' existir.
    op.create_table('faturas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cartao_id', sa.Integer(), nullable=False),
    sa.Column('mes_referencia', sa.Date(), nullable=False),
    sa.Column('data_fechamento', sa.Date(), nullable=False),
    sa.Column('data_vencimento', sa.Date(), nullable=False),
    sa.Column('valor_total', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('status', sa.Enum('ABERTA', 'FECHADA', 'PAGA', 'ATRASADA', name='statusfatura'), nullable=False),
    sa.Column('transacao_pagamento_id', sa.Integer(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cartao_id', 'mes_referencia', name='uq_fatura_cartao_mes')
    )
    op.create_index(op.f('ix_faturas_cartao_id'), 'faturas', ['cartao_id'], unique=False)

    # 5) dependem de cartoes/categorias/contas/usuarios
    op.create_table('contas_recorrentes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=False),
    sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('tipo', sa.Enum('RECEITA', 'DESPESA', name='tipotransacao'), nullable=False),
    sa.Column('frequencia', sa.Enum('SEMANAL', 'MENSAL', 'ANUAL', name='frequenciarecorrencia'), nullable=False),
    sa.Column('dia_vencimento', sa.Integer(), nullable=False),
    sa.Column('categoria_id', sa.Integer(), nullable=True),
    sa.Column('conta_id', sa.Integer(), nullable=True),
    sa.Column('cartao_id', sa.Integer(), nullable=True),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('data_fim', sa.Date(), nullable=True),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contas_recorrentes_usuario_id'), 'contas_recorrentes', ['usuario_id'], unique=False)

    op.create_table('parcelamentos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('COMPRA_CARTAO', 'EMPRESTIMO', 'FINANCIAMENTO', 'OUTRO', name='tipoparcelamento'), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=False),
    sa.Column('valor_total', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('num_parcelas', sa.Integer(), nullable=False),
    sa.Column('taxa_juros', sa.Numeric(precision=6, scale=4), nullable=True),
    sa.Column('credor', sa.String(length=120), nullable=True),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.Column('cartao_id', sa.Integer(), nullable=True),
    sa.Column('conta_id', sa.Integer(), nullable=True),
    sa.Column('categoria_id', sa.Integer(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parcelamentos_usuario_id'), 'parcelamentos', ['usuario_id'], unique=False)

    # 6) transacoes: depende de praticamente tudo acima (usuarios, categorias,
    # contas, cartoes, parcelamentos, contas_recorrentes, metas, faturas)
    op.create_table('transacoes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('RECEITA', 'DESPESA', name='tipotransacao'), nullable=False),
    sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Enum('PENDENTE', 'PAGO', name='statustransacao'), nullable=False),
    sa.Column('categoria_id', sa.Integer(), nullable=True),
    sa.Column('conta_id', sa.Integer(), nullable=True),
    sa.Column('cartao_id', sa.Integer(), nullable=True),
    sa.Column('parcelamento_id', sa.Integer(), nullable=True),
    sa.Column('numero_parcela', sa.Integer(), nullable=True),
    sa.Column('origem_recorrente_id', sa.Integer(), nullable=True),
    sa.Column('meta_id', sa.Integer(), nullable=True),
    sa.Column('fatura_id', sa.Integer(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint('(conta_id IS NOT NULL AND cartao_id IS NULL) OR (conta_id IS NULL AND cartao_id IS NOT NULL)', name='ck_transacao_conta_xor_cartao'),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['fatura_id'], ['faturas.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['meta_id'], ['metas.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['origem_recorrente_id'], ['contas_recorrentes.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['parcelamento_id'], ['parcelamentos.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transacoes_data'), 'transacoes', ['data'], unique=False)
    op.create_index(op.f('ix_transacoes_usuario_id'), 'transacoes', ['usuario_id'], unique=False)

    # 7) agora que 'transacoes' existe, fecha o ciclo faturas <-> transacoes
    # com um ALTER TABLE (reflete o use_alter=True do model Fatura).
    # SQLite nao suporta ALTER TABLE ADD CONSTRAINT diretamente - o modo
    # "batch" do Alembic contorna isso recriando a tabela nos bastidores
    # com a constraint nova incluida (estrategia copy-and-move).
    with op.batch_alter_table('faturas') as batch_op:
        batch_op.create_foreign_key(
            'fk_faturas_transacao_pagamento_id',
            'transacoes',
            ['transacao_pagamento_id'], ['id'],
            ondelete='SET NULL',
        )

    # 8) tabelas que dependem de transacoes/tags/contas
    op.create_table('transacao_tag',
    sa.Column('transacao_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['transacao_id'], ['transacoes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('transacao_id', 'tag_id')
    )

    op.create_table('transferencias',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('conta_origem_id', sa.Integer(), nullable=False),
    sa.Column('conta_destino_id', sa.Integer(), nullable=False),
    sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('descricao', sa.String(length=200), nullable=True),
    sa.Column('criado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint('conta_origem_id != conta_destino_id', name='ck_transferencia_contas_distintas'),
    sa.ForeignKeyConstraint(['conta_destino_id'], ['contas.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['conta_origem_id'], ['contas.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transferencias_data'), 'transferencias', ['data'], unique=False)
    op.create_index(op.f('ix_transferencias_usuario_id'), 'transferencias', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transferencias_usuario_id'), table_name='transferencias')
    op.drop_index(op.f('ix_transferencias_data'), table_name='transferencias')
    op.drop_table('transferencias')
    op.drop_table('transacao_tag')

    # quebra o ciclo antes de derrubar faturas/transacoes, na ordem inversa da criacao
    with op.batch_alter_table('faturas') as batch_op:
        batch_op.drop_constraint('fk_faturas_transacao_pagamento_id', type_='foreignkey')

    op.drop_index(op.f('ix_transacoes_usuario_id'), table_name='transacoes')
    op.drop_index(op.f('ix_transacoes_data'), table_name='transacoes')
    op.drop_table('transacoes')

    op.drop_index(op.f('ix_parcelamentos_usuario_id'), table_name='parcelamentos')
    op.drop_table('parcelamentos')
    op.drop_index(op.f('ix_contas_recorrentes_usuario_id'), table_name='contas_recorrentes')
    op.drop_table('contas_recorrentes')

    op.drop_index(op.f('ix_faturas_cartao_id'), table_name='faturas')
    op.drop_table('faturas')

    op.drop_index(op.f('ix_metas_usuario_id'), table_name='metas')
    op.drop_table('metas')
    op.drop_index(op.f('ix_cartoes_usuario_id'), table_name='cartoes')
    op.drop_table('cartoes')

    op.drop_index(op.f('ix_anexos_usuario_id'), table_name='anexos')
    op.drop_table('anexos')
    op.drop_index(op.f('ix_alertas_usuario_id'), table_name='alertas')
    op.drop_table('alertas')
    op.drop_index(op.f('ix_tags_usuario_id'), table_name='tags')
    op.drop_table('tags')
    op.drop_index(op.f('ix_contas_usuario_id'), table_name='contas')
    op.drop_table('contas')
    op.drop_index(op.f('ix_categorias_usuario_id'), table_name='categorias')
    op.drop_table('categorias')

    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')
