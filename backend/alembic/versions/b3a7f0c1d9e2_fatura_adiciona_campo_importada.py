"""fatura: adiciona campo importada

Revision ID: b3a7f0c1d9e2
Revises: 7544876ab513
Create Date: 2026-07-17 00:00:00.000000

Adiciona `faturas.importada` (bool, default False) - suporte à importação
de faturas HISTÓRICAS (um ciclo que já aconteceu e já foi pago antes do
usuário começar a usar o app), via novo `FaturaService.importar()`/
`POST /faturas/importar`. Diferente da criação normal (sempre ABERTA,
`valor_total` sempre derivado de Transacao reais), a fatura importada
nasce já FECHADA com um `valor_total` informado diretamente pelo usuário -
essa coluna existe só para o frontend distinguir visualmente ("registro
histórico reconstituído") um documento importado de um fechado
organicamente pelo fluxo normal. Mesmo padrão de `server_default` já usado
em `transferencias.ativo` (bfc086b70a32) e `tags.ativo` (75bf54bdf7ff):
garante que a coluna NOT NULL possa ser adicionada com a tabela já tendo
linhas (faturas existentes viram importada=False).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a7f0c1d9e2'
down_revision: Union[str, None] = '7544876ab513'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('faturas', sa.Column('importada', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('faturas', 'importada')
