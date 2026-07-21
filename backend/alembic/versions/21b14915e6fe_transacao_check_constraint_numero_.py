"""transacao: check constraint numero_parcela condiz com contrato

Revision ID: 21b14915e6fe
Revises: 9152217acac1
Create Date: 2026-07-14 10:36:58.570631

Parte da modelagem de Transacao (ver docs/analise-arquitetural-transacao.md):
`numero_parcela` so faz sentido quando a transacao e de fato uma parcela de
algum "contrato" (Parcelamento, Financiamento ou Emprestimo) - nada
garantia essa consistencia no banco ate agora. Novo CheckConstraint exige
`numero_parcela IS NOT NULL` sse pelo menos um entre `parcelamento_id`,
`financiamento_id`, `emprestimo_id` estiver preenchido, e `numero_parcela
IS NULL` caso contrario.

Alembic autogenerate nao detecta mudanca de CheckConstraint sozinho (mesma
limitacao ja observada nas migrations anteriores) - upgrade/downgrade
escritos a mao, usando batch_alter_table (SQLite nao suporta
ADD/DROP CONSTRAINT fora de modo batch), mesma estrategia das migrations
de Cartao e Fatura.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21b14915e6fe'
down_revision: Union[str, None] = '9152217acac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.create_check_constraint(
            'ck_transacao_numero_parcela_condiz_com_contrato',
            "(CASE WHEN "
            "   (parcelamento_id IS NOT NULL OR financiamento_id IS NOT NULL OR emprestimo_id IS NOT NULL) "
            "  THEN numero_parcela IS NOT NULL "
            "  ELSE numero_parcela IS NULL "
            " END)",
        )


def downgrade() -> None:
    with op.batch_alter_table('transacoes') as batch_op:
        batch_op.drop_constraint('ck_transacao_numero_parcela_condiz_com_contrato', type_='check')
