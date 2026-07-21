"""placeholder no-op (arquivo residual - mount nao permite exclusao)

Revision ID: 0fecbf64f7db
Revises: aaaa0000dummy
Create Date: 2026-07-14 18:26:16.170335

Mesmo caso de aaaa0000dummy.py (ver docstring la para o motivo completo):
arquivo residual gerado por um `alembic revision --autogenerate` de
verificacao de drift durante esta sessao (confirmou corretamente ZERO
diferenca de schema - por isso upgrade/downgrade sao no-op de verdade, nao
uma migration esquecida). Nao pode ser excluido neste ambiente, entao fica
como no-op documentado em vez de vazio (o que quebraria `alembic history`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fecbf64f7db'
down_revision: Union[str, None] = 'aaaa0000dummy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
