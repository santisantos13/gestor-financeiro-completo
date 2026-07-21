"""placeholder no-op (arquivo residual - mount nao permite exclusao)

Revision ID: aaaa0000dummy
Revises: 441dd71b0fe8
Create Date: 2026-07-14 18:27:00.000000

Este arquivo foi criado por engano durante a validacao de migration desta
sessao (um teste descartavel via bash) e nao corresponde a nenhuma mudanca
real de modelagem. O ambiente de execucao usado nesta sessao nao permite
excluir arquivos do mount sincronizado (rm/os.remove/mv falham com
"Operation not permitted" mesmo com permissao de dono, uma limitacao do
proprio mount, nao do projeto) - a unica forma segura de neutralizar o
arquivo sem quebrar `alembic history` (que exige `revision` valido em todo
.py de versions/) foi transforma-lo num no-op explicito e documentado, em
vez de deixa-lo vazio (o que quebra o carregamento do Alembic) ou apagado
(impossivel neste ambiente). Nao representa nenhuma alteracao de schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aaaa0000dummy'
down_revision: Union[str, None] = '441dd71b0fe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
