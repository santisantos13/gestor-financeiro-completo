"""conta_recorrente: cursor proxima_execucao, status explicito, dia_vencimento opcional

Revision ID: c8d1e4f7a2b5
Revises: b2c3d4e5f6a7
Create Date: 2026-07-20 17:00:00.000000

Expansao do modulo de Contas Recorrentes
(docs/analise-arquitetural-conta-recorrente-expansao.md, aprovada pelo
usuario em 2026-07-20):

1. `proxima_execucao` (Date, NOT NULL): cursor materializado de geracao -
   substitui derivar a proxima data da ultima Transacao gerada. Backfill
   por template: a partir da ultima ocorrencia ja gerada (avancada um
   periodo), ou da primeira data do template se nada foi gerado. Todo dado
   pre-existente e MENSAL por construcao (o Service rejeitava qualquer
   outra frequencia), entao o backfill so precisa da aritmetica mensal.
2. `status` (ATIVA/PAUSADA/ENCERRADA): substitui o booleano `ativo`.
   Backfill: ativo=True -> ATIVA, ativo=False -> PAUSADA (a semantica
   antiga de "desativada" era reativavel em tese - PAUSADA e o mapeamento
   fiel; ENCERRADA so nasce das novas acoes explicitas).
3. `dia_vencimento` vira nullable (frequencias baseadas em dias nao o
   usam). Nenhuma linha existente e afetada (todas MENSAL, todas com dia).

batch_alter_table por causa do SQLite (mesma limitacao/solucao das
migrations anteriores).
"""
import calendar
from datetime import date, timedelta
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8d1e4f7a2b5'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dia_valido(ano: int, mes: int, dia: int) -> date:
    return date(ano, mes, min(dia, calendar.monthrange(ano, mes)[1]))


def _proximo_mes(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def upgrade() -> None:
    # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
    # o tipo nativo 'frequenciarecorrencia' existe no Postgres desde a
    # migration inicial com so 3 valores (SEMANAL/MENSAL/ANUAL) - esta
    # expansao (docs/analise-arquitetural-conta-recorrente-expansao.md)
    # ampliou o enum Python para 8 valores, mas nenhuma migration ate agora
    # tinha replicado isso no tipo nativo do Postgres. No SQLite isso nunca
    # deu erro porque a coluna e VARCHAR simples (sem CHECK, native_enum nao
    # se aplica) - so o Postgres tem um tipo de fato restrito, e gravar
    # DIARIA/QUINZENAL/BIMESTRAL/TRIMESTRAL/SEMESTRAL falharia com "invalid
    # input value for enum frequenciarecorrencia" (gap encontrado ao validar
    # esta migration contra um Postgres real antes do deploy).
    if op.get_bind().dialect.name == "postgresql":
        for valor in ("DIARIA", "QUINZENAL", "BIMESTRAL", "TRIMESTRAL", "SEMESTRAL"):
            op.execute(f"ALTER TYPE frequenciarecorrencia ADD VALUE IF NOT EXISTS '{valor}'")

    op.add_column(
        'contas_recorrentes',
        # server_default temporario so para a coluna nascer NOT NULL em
        # tabela com linhas - o backfill logo abaixo grava o valor real.
        sa.Column('proxima_execucao', sa.Date(), nullable=False, server_default='1970-01-01'),
    )
    op.add_column(
        'contas_recorrentes',
        sa.Column('status', sa.String(length=10), nullable=False, server_default='ATIVA'),
    )

    conn = op.get_bind()

    templates = conn.execute(
        sa.text("SELECT id, dia_vencimento, data_inicio, ativo FROM contas_recorrentes")
    ).fetchall()
    for template_id, dia_vencimento, data_inicio, ativo in templates:
        if isinstance(data_inicio, str):
            data_inicio = date.fromisoformat(data_inicio)

        ultima = conn.execute(
            sa.text(
                "SELECT MAX(data) FROM transacoes WHERE origem_recorrente_id = :id"
            ),
            {"id": template_id},
        ).scalar()

        if ultima is not None:
            if isinstance(ultima, str):
                ultima = date.fromisoformat(ultima)
            ano, mes = _proximo_mes(ultima.year, ultima.month)
            proxima = _dia_valido(ano, mes, dia_vencimento)
        else:
            proxima = _dia_valido(data_inicio.year, data_inicio.month, dia_vencimento)
            if proxima < data_inicio:
                ano, mes = _proximo_mes(proxima.year, proxima.month)
                proxima = _dia_valido(ano, mes, dia_vencimento)

        conn.execute(
            sa.text(
                "UPDATE contas_recorrentes SET proxima_execucao = :proxima, "
                "status = :status WHERE id = :id"
            ),
            {
                "proxima": proxima.isoformat(),
                "status": "ATIVA" if ativo else "PAUSADA",
                "id": template_id,
            },
        )

    with op.batch_alter_table('contas_recorrentes') as batch_op:
        batch_op.alter_column('dia_vencimento', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('proxima_execucao', server_default=None)
        batch_op.alter_column('status', server_default=None)
        batch_op.drop_column('ativo')


def downgrade() -> None:
    op.add_column(
        'contas_recorrentes',
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE contas_recorrentes SET ativo = CASE WHEN status = 'ATIVA' THEN true ELSE false END")
    )
    with op.batch_alter_table('contas_recorrentes') as batch_op:
        batch_op.alter_column('ativo', server_default=None)
        batch_op.drop_column('status')
        batch_op.drop_column('proxima_execucao')
        batch_op.alter_column('dia_vencimento', existing_type=sa.Integer(), nullable=False)
