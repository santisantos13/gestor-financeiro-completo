"""meta: adiciona frequencia_contribuicao e concluida_em

Revision ID: e7c1a2b9d4f6
Revises: d2a4e6f8c1b3
Create Date: 2026-07-19 00:00:00.000000

Refinamento de Metas (docs/analise-arquitetural-metas-refinamento.md):

- `metas.frequencia_contribuicao` (enum DIARIA/SEMANAL/QUINZENAL/MENSAL,
  nullable) - escolha opcional do usuário na criação/edição, usada só para
  calcular a contribuição sugerida por período (nunca valida/bloqueia
  nada).
- `metas.concluida_em` (Date, nullable) - data em que `percentual` cruzou
  100% pela primeira vez, gravada lazily por `MetaService._com_progresso`
  na primeira leitura em que a transição é observada. Nunca desfeita
  depois.

Ambas nullable, sem `server_default`: metas existentes simplesmente não
têm frequência escolhida nem data de conclusão registrada ainda - nenhum
backfill necessário (a segunda é preenchida sozinha na próxima leitura de
cada meta já concluída).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7c1a2b9d4f6'
down_revision: Union[str, None] = 'd2a4e6f8c1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
    # `.create()` explicito - `op.add_column` sozinho nao cria o tipo nativo
    # no Postgres (so `create_table` faz isso). No-op no SQLite. Mesmo
    # ajuste de 7c04a41962ca (tipopapel) e d6639c25b68c (bandeira).
    frequencia_enum = sa.Enum('DIARIA', 'SEMANAL', 'QUINZENAL', 'MENSAL', name='frequenciacontribuicao')
    frequencia_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'metas',
        sa.Column(
            'frequencia_contribuicao',
            frequencia_enum,
            nullable=True,
        ),
    )
    op.add_column('metas', sa.Column('concluida_em', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('metas', 'concluida_em')
    op.drop_column('metas', 'frequencia_contribuicao')
    sa.Enum(name='frequenciacontribuicao').drop(op.get_bind(), checkfirst=True)
