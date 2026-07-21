"""placeholder no-op (arquivo residual - mount nao permite exclusao)

Revision ID: 8b100b274a2e
Revises: 0fecbf64f7db
Create Date: 2026-07-14 18:28:36.457805

Mesmo caso de aaaa0000dummy.py e 0fecbf64f7db_drift_check.py (ver
docstring de aaaa0000dummy.py para o motivo completo): segunda
verificacao de drift rodada apos a primeira, tambem confirmou ZERO
diferenca de schema (upgrade/downgrade genuinamente vazios, nao uma
migration esquecida). Arquivo residual que nao pode ser excluido neste
ambiente - mantido como no-op documentado para nao quebrar `alembic
history`. Nenhuma mudanca de schema real, aqui ou nos dois anteriores.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b100b274a2e'
down_revision: Union[str, None] = '0fecbf64f7db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
