"""transacao: adiciona campo importada

Revision ID: c4d8e1a2f6b7
Revises: b3a7f0c1d9e2
Create Date: 2026-07-18 00:00:00.000000

Adiciona `transacoes.importada` (bool, default False) - resolve o bug
relatado pelo usuário: o saldo de uma Conta aparecia negativo por causa de
parcelas de um Financiamento/Empréstimo que já existia ANTES do usuário
começar a usar o app (registradas via "parcelas_ja_pagas" no onboarding,
`FinanciamentoService.criar()`/`EmprestimoService.criar()`). Instrução
explícita do usuário: "deixe por conta do usuário decidir se ele tá com
saldo negativo ou não, evite deduções com base em informações resgatadas
do passado financeiro antes do uso do app".

Mesmo padrão de `faturas.importada` (b3a7f0c1d9e2) e de `server_default`
usado em `transferencias.ativo`/`tags.ativo`: garante que a coluna NOT NULL
possa ser adicionada com a tabela já tendo linhas (transações existentes
viram importada=False por padrão).

Esta migração também faz o BACKFILL único necessário para os dados reais
já existentes: qualquer parcela de Financiamento/Empréstimo que já está
PAGA hoje (antes desta coluna existir) foi paga pelo loop de onboarding
"parcelas_ja_pagas" — essa funcionalidade acabou de ser criada nesta mesma
sessão de trabalho, então nenhuma parcela PAGA de contrato de crédito
existente no banco até este momento pode ter vindo de um clique real no
botão "Pagar" da UI (esse botão também acabou de ser criado). Por isso é
seguro marcar todas elas como `importada=True` de uma vez, sem precisar
adivinhar registro por registro.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d8e1a2f6b7'
down_revision: Union[str, None] = 'b3a7f0c1d9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transacoes', sa.Column('importada', sa.Boolean(), nullable=False, server_default=sa.false()))

    # Backfill único: parcelas de Financiamento/Empréstimo já PAGAS antes
    # desta coluna existir vieram do onboarding, nunca de um pagamento
    # feito organicamente pela UI (ver docstring acima do motivo).
    # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
    # `true` no lugar de `1` - Postgres nao aceita inteiro puro atribuido a
    # coluna boolean via SQL cru (SQLite trata boolean como inteiro, entao
    # isso nunca deu erro ali).
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE transacoes SET importada = true "
            "WHERE status = 'PAGO' "
            "AND (financiamento_id IS NOT NULL OR emprestimo_id IS NOT NULL)"
        )
    )


def downgrade() -> None:
    op.drop_column('transacoes', 'importada')
