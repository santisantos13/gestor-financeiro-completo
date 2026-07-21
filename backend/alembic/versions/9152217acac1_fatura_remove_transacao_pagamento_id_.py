"""fatura: remove transacao_pagamento_id, adiciona fatura_paga_id em transacao

Revision ID: 9152217acac1
Revises: d6639c25b68c
Create Date: 2026-07-13 14:14:21.502592

Parte da modelagem de Fatura (ver docs/analise-arquitetural-fatura.md):
substitui `Fatura.transacao_pagamento_id` (FK singular, so suportava
pagamento total, e exigia use_alter=True por causa da dependencia ciclica
entre Fatura e Transacao) por `Transacao.fatura_paga_id` (varias
transacoes de pagamento podem apontar pra mesma fatura, suportando
pagamento parcial/multiplo - e elimina o ciclo, ja que agora as duas FKs
entre as tabelas apontam na mesma direcao: Transacao -> Fatura).

O enum StatusFatura ganhou PARCIALMENTE_PAGA como valor adicional no lado
Python (ja existiam ABERTA/FECHADA/PAGA/ATRASADA) - PARCIALMENTE_PAGA/PAGA/
ATRASADA sao sempre DERIVADOS por FaturaService a partir de valor_pago/
valor_total/data_vencimento, nunca gravados na coluna `status` (so
ABERTA/FECHADA sao realmente persistidas). Mesmo assim, o CHECK constraint
da coluna e ampliado aqui para incluir PARCIALMENTE_PAGA - nao porque o
valor seja gravado, mas para manter `alembic check` limpo (o tipo Python
e o CHECK do banco continuam refletindo o mesmo enum, evitando uma
divergencia de ferramenta permanente e sem necessidade).

Todas as operacoes usam `batch_alter_table`: SQLite nao suporta
`ALTER TABLE DROP CONSTRAINT`/`ADD CONSTRAINT` diretamente - o modo batch
recria a tabela por baixo dos panos (copy-and-move), mesma estrategia ja
usada na migration de nome unico de Cartao.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9152217acac1'
down_revision: Union[str, None] = 'd6639c25b68c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
    # o tipo nativo 'statusfatura' ja existe no Postgres desde a migration
    # inicial (criado via `create_table`, com ABERTA/FECHADA/PAGA/ATRASADA).
    # O `alter_column` abaixo so troca o tipo Python da coluna - como o nome
    # do tipo ('statusfatura') nao muda, o Postgres nao recria nem amplia o
    # tipo sozinho, entao o valor novo (PARCIALMENTE_PAGA) precisaria ser
    # adicionado explicitamente com ALTER TYPE ... ADD VALUE, ou qualquer
    # tentativa futura de gravar esse valor falharia com "invalid input
    # value for enum statusfatura" (confirmado rodando esta migration contra
    # um Postgres real). No SQLite, a coluna e VARCHAR simples (native_enum
    # nao se aplica), entao o guard de dialeto evita rodar um ALTER TYPE
    # que so existe no Postgres.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE statusfatura ADD VALUE IF NOT EXISTS 'PARCIALMENTE_PAGA'")

    with op.batch_alter_table('faturas') as batch_op:
        batch_op.drop_constraint('fk_faturas_transacao_pagamento_id', type_='foreignkey')
        batch_op.drop_column('transacao_pagamento_id')
        batch_op.alter_column(
            'status',
            existing_type=sa.VARCHAR(length=8),
            type_=sa.Enum('ABERTA', 'FECHADA', 'PARCIALMENTE_PAGA', 'PAGA', 'ATRASADA', name='statusfatura'),
            existing_nullable=False,
        )

    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.add_column(sa.Column('fatura_paga_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_transacoes_fatura_id', ['fatura_id'], unique=False)
        batch_op.create_index('ix_transacoes_fatura_paga_id', ['fatura_paga_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_transacoes_fatura_paga_id', 'faturas', ['fatura_paga_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_check_constraint(
            'ck_transacao_fatura_compra_xor_pagamento',
            'NOT (fatura_id IS NOT NULL AND fatura_paga_id IS NOT NULL)',
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('ck_transacao_fatura_compra_xor_pagamento', type_='check')
        batch_op.drop_constraint('fk_transacoes_fatura_paga_id', type_='foreignkey')
        batch_op.drop_index('ix_transacoes_fatura_paga_id')
        batch_op.drop_index('ix_transacoes_fatura_id')
        batch_op.drop_column('fatura_paga_id')

    with op.batch_alter_table('faturas') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum('ABERTA', 'FECHADA', 'PARCIALMENTE_PAGA', 'PAGA', 'ATRASADA', name='statusfatura'),
            type_=sa.VARCHAR(length=8),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column('transacao_pagamento_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_faturas_transacao_pagamento_id',
            'transacoes',
            ['transacao_pagamento_id'],
            ['id'],
            ondelete='SET NULL',
        )
