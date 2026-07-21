"""cartao: instituicao, bandeira, ultimos_quatro_digitos, nome unico

Revision ID: d6639c25b68c
Revises: 75bf54bdf7ff
Create Date: 2026-07-13 13:39:23.248592

Adiciona os campos identificadores do cartao fisico (instituicao, bandeira,
ultimos 4 digitos) e a unicidade de nome por usuario. `server_default` nas
tres colunas NOT NULL novas garante que a migration rode mesmo se a tabela
ja tiver linhas (mesmo padrao ja usado em usuarios.papel e tags.ativo) -
os valores de fallback sao so placeholders para linhas pre-existentes,
nunca usados em uma criacao nova (o Schema Pydantic exige os tres campos).

A UniqueConstraint precisa de `batch_alter_table`: SQLite nao suporta
`ALTER TABLE ADD CONSTRAINT` diretamente (só ADD COLUMN simples) - o modo
batch do Alembic recria a tabela por baixo dos panos (copy-and-move) para
simular a operação. Mesma limitação documentada no uso de `use_alter=True`
em Fatura, mas resolvida de forma diferente aqui: lá o problema era
dependência cíclica entre tabelas, aqui é uma limitação de ALTER do SQLite.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6639c25b68c'
down_revision: Union[str, None] = '75bf54bdf7ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cartoes',
        sa.Column('instituicao', sa.String(length=120), nullable=False, server_default=''),
    )
    # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
    # `.create()` explicito - `op.add_column` sozinho nao cria o tipo nativo
    # no Postgres (so `create_table` faz isso). No-op no SQLite. Mesmo
    # ajuste de 7c04a41962ca (tipopapel).
    bandeira_enum = sa.Enum(
        'VISA', 'MASTERCARD', 'ELO', 'AMERICAN_EXPRESS', 'HIPERCARD', 'DINERS_CLUB', 'OUTRA', name='bandeira'
    )
    bandeira_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'cartoes',
        sa.Column(
            'bandeira',
            bandeira_enum,
            nullable=False,
            server_default='OUTRA',
        ),
    )
    op.add_column(
        'cartoes',
        sa.Column('ultimos_quatro_digitos', sa.String(length=4), nullable=False, server_default='0000'),
    )
    op.create_index(op.f('ix_cartoes_conta_pagamento_id'), 'cartoes', ['conta_pagamento_id'], unique=False)
    with op.batch_alter_table('cartoes') as batch_op:
        batch_op.create_unique_constraint('uq_cartao_usuario_nome', ['usuario_id', 'nome'])


def downgrade() -> None:
    with op.batch_alter_table('cartoes') as batch_op:
        batch_op.drop_constraint('uq_cartao_usuario_nome', type_='unique')
    op.drop_index(op.f('ix_cartoes_conta_pagamento_id'), table_name='cartoes')
    op.drop_column('cartoes', 'ultimos_quatro_digitos')
    op.drop_column('cartoes', 'bandeira')
    op.drop_column('cartoes', 'instituicao')
    sa.Enum(name='bandeira').drop(op.get_bind(), checkfirst=True)
