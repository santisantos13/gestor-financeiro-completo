"""conta: campo oculta; meta: cofrinho automatico obrigatorio

Revision ID: f2a5c8e1b3d7
Revises: e7c1a2b9d4f6
Create Date: 2026-07-18 23:50:00.000000

Parte do Refatoramento de Metas/Transferencias (ver
docs/analise-arquitetural-metas-transferencias.md): aportes/resgates
passam a ser Transferencia (nao mais Transacao DESPESA/RECEITA), o que
exige toda Meta ter uma Conta dedicada e oculta (o "cofrinho") para ser o
destino/origem dessas transferencias.

Duas partes:
1. Schema: `contas.oculta` (nova coluna, boolean, default False) e
   `metas.conta_id` passa de nullable para NOT NULL.
2. Dado: para CADA Meta ja existente (ativa ou desativada, com ou sem
   `conta_id` anterior - o vinculo antigo era so organizacional, nunca
   teve efeito em calculo algum, entao nao ha nada a preservar nele), cria
   uma Conta nova oculta e sobrescreve `metas.conta_id` para apontar pra
   ela. So depois disso a coluna vira NOT NULL - garantindo que a migration
   nunca falhe por causa de uma linha antiga sem conta_id.

Idempotente na parte de dado: se uma Meta ja tiver uma Conta com
`oculta=True` como `conta_id` (reexecucao desta migration), ela e pulada
em vez de ganhar um cofrinho duplicado.

batch_alter_table para o `alter_column` de `metas.conta_id`: SQLite nao
suporta ALTER de nullability diretamente, mesma limitacao/solucao ja usada
em outras migrations deste projeto (ver
d6639c25b68c_cartao_instituicao_bandeira_ultimos_.py).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2a5c8e1b3d7'
down_revision: Union[str, None] = 'e7c1a2b9d4f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contas', sa.Column('oculta', sa.Boolean(), nullable=False, server_default=sa.false()))

    conn = op.get_bind()

    metas = conn.execute(sa.text("SELECT id, usuario_id, descricao, conta_id FROM metas")).fetchall()
    for meta_id, usuario_id, descricao, conta_id_atual in metas:
        if conta_id_atual is not None:
            ja_e_cofrinho = conn.execute(
                sa.text("SELECT oculta FROM contas WHERE id = :id"), {"id": conta_id_atual}
            ).scalar()
            if ja_e_cofrinho:
                # Reexecucao desta migration - esta Meta ja tem seu
                # cofrinho, nao cria outro.
                continue

        # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
        # dois ajustes de portabilidade encontrados rodando esta migration
        # contra um Postgres real: (1) `RETURNING id` no lugar de
        # `SELECT last_insert_rowid()` (especifico do SQLite); (2)
        # `true`/`false` literais no lugar de `1`/`1` - o Postgres nao aceita
        # inteiro puro num literal de coluna boolean (SQLite trata boolean
        # como inteiro, entao isso nunca deu erro ali).
        cofrinho_id = conn.execute(
            sa.text(
                "INSERT INTO contas (usuario_id, nome, tipo, saldo_inicial, instituicao, ativo, oculta) "
                "VALUES (:usuario_id, :nome, 'CARTEIRA', 0, NULL, true, true) RETURNING id"
            ),
            {"usuario_id": usuario_id, "nome": f"Cofrinho — {descricao}"},
        ).scalar()
        conn.execute(
            sa.text("UPDATE metas SET conta_id = :conta_id WHERE id = :meta_id"),
            {"conta_id": cofrinho_id, "meta_id": meta_id},
        )

    with op.batch_alter_table('metas') as batch_op:
        batch_op.alter_column('conta_id', existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('metas') as batch_op:
        batch_op.alter_column('conta_id', existing_type=sa.Integer(), nullable=True)
    # Os cofrinhos criados pela parte de dado do upgrade() nao sao
    # removidos aqui de proposito: uma Meta pode ja ter recebido
    # aportes/resgates reais (Transferencia) contra o cofrinho antes de um
    # downgrade acontecer - apagar a Conta destruiria esse historico. Só a
    # tightening de schema é desfeita.
    op.drop_column('contas', 'oculta')
