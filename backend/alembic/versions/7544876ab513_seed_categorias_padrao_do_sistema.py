"""seed categorias padrao do sistema

Revision ID: 7544876ab513
Revises: 5bf719e3a7a3
Create Date: 2026-07-17 15:00:00.000000

Migracao de DADO (nao de schema) - nenhuma coluna/tabela e alterada.
Insere as categorias "de sistema" (`usuario_id = NULL`) que o model
`Categoria` ja previa desde o inicio (ver docstring de
`app/models/categoria.py`), mas que nunca tinham sido populadas - conferido
por busca no projeto inteiro antes desta etapa
(docs/analise-arquitetural-refinamento-ux-dashboard-cartoes.md, secao 5).

Idempotente: se ja existir qualquer categoria com `usuario_id IS NULL`, a
migracao nao insere nada de novo (evita duplicar em bancos que rodarem esta
migracao mais de uma vez, ou que ja tenham sido semeados por outro caminho).
Usuarios continuam podendo editar/desativar/criar categorias proprias
normalmente depois disso - `CategoriaService._buscar_editavel` ja bloqueia
edicao das categorias de sistema, comportamento inalterado.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7544876ab513'
down_revision: Union[str, None] = '5bf719e3a7a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Cada entrada: (nome, tipo, cor, icone, [filhos])
# `icone` usa os ids curados de frontend/src/lib/icons.ts (registry unico,
# nenhum SVG/nome de componente arbitrario - so a convencao ja existente).
# `cor` usa hexadecimais da paleta de frontend/src/lib/color.ts.
CATEGORIAS_PADRAO: list[tuple[str, str, str, str, list[tuple[str, str, str]]]] = [
    ("Alimentação", "DESPESA", "#fb923c", "utensils-crossed", [
        ("Mercado", "#fb923c", "shopping-cart"),
        ("Delivery", "#fb923c", "package"),
        ("Restaurante", "#fb923c", "utensils-crossed"),
        ("Padaria", "#fb923c", "coffee"),
    ]),
    ("Transporte", "DESPESA", "#2563eb", "car", [
        ("Combustível", "#2563eb", "fuel"),
        ("Uber/Apps", "#2563eb", "car"),
        ("Estacionamento", "#2563eb", "parking-circle"),
        ("Pedágio", "#2563eb", "coins"),
        ("Manutenção", "#2563eb", "wrench"),
    ]),
    ("Moradia", "DESPESA", "#0d9488", "home", [
        ("Água", "#0d9488", "droplet"),
        ("Energia", "#0d9488", "zap"),
        ("Internet", "#0d9488", "wifi"),
        ("Condomínio", "#0d9488", "building-2"),
        ("Gás", "#0d9488", "flame"),
    ]),
    ("Saúde", "DESPESA", "#dc2626", "heart-pulse", [
        ("Consultas", "#dc2626", "stethoscope"),
        ("Farmácia", "#dc2626", "pill"),
        ("Plano de saúde", "#dc2626", "umbrella"),
    ]),
    ("Educação", "DESPESA", "#7c3aed", "graduation-cap", [
        ("Cursos", "#7c3aed", "graduation-cap"),
        ("Material", "#7c3aed", "book"),
        ("Mensalidade", "#7c3aed", "receipt"),
    ]),
    ("Lazer", "DESPESA", "#db2777", "sparkles", [
        ("Streaming", "#db2777", "headphones"),
        ("Viagens", "#db2777", "plane"),
        ("Hobbies", "#db2777", "gamepad-2"),
    ]),
    ("Compras", "DESPESA", "#ca8a04", "shopping-bag", [
        ("Vestuário", "#ca8a04", "shirt"),
        ("Eletrônicos", "#ca8a04", "smartphone"),
        ("Casa", "#ca8a04", "home"),
    ]),
    ("Pets", "DESPESA", "#16a34a", "paw-print", []),
    ("Assinaturas", "DESPESA", "#22d3ee", "receipt", []),
    ("Investimentos", "AMBOS", "#059669", "trending-up", []),
    ("Presentes", "DESPESA", "#f472b6", "gift", []),
    ("Trabalho", "AMBOS", "#60a5fa", "briefcase", []),
    ("Renda", "RECEITA", "#4ade80", "dollar-sign", [
        ("Salário", "#4ade80", "banknote"),
        ("Freelance", "#4ade80", "handshake"),
        ("Rendimentos", "#4ade80", "trending-up"),
    ]),
]


def upgrade() -> None:
    conn = op.get_bind()
    categorias = sa.table(
        "categorias",
        sa.column("id", sa.Integer),
        sa.column("usuario_id", sa.Integer),
        sa.column("nome", sa.String),
        sa.column("tipo", sa.String),
        sa.column("categoria_pai_id", sa.Integer),
        sa.column("cor", sa.String),
        sa.column("icone", sa.String),
        sa.column("ativo", sa.Boolean),
    )

    ja_existe = conn.execute(
        sa.text("SELECT 1 FROM categorias WHERE usuario_id IS NULL LIMIT 1")
    ).first()
    if ja_existe is not None:
        # Idempotente - alguem ja semeou categorias de sistema (ex: reexecucao
        # desta migracao em outro ambiente). Nao insere de novo.
        return

    for nome_pai, tipo, cor, icone, filhos in CATEGORIAS_PADRAO:
        # Deploy Postgres (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
        # trocado de `SELECT last_insert_rowid()` (especifico do SQLite) para
        # `.returning(...)`, suportado tanto por SQLite 3.35+ quanto por
        # Postgres - forma portavel de pegar o id que acabou de ser inserido
        # sem precisar declarar uma `sa.Table` completa so para isso.
        pai_id = conn.execute(
            sa.insert(categorias)
            .values(
                usuario_id=None,
                nome=nome_pai,
                tipo=tipo,
                categoria_pai_id=None,
                cor=cor,
                icone=icone,
                ativo=True,
            )
            .returning(categorias.c.id)
        ).scalar()

        for nome_filho, cor_filho, icone_filho in filhos:
            conn.execute(
                sa.insert(categorias).values(
                    usuario_id=None,
                    nome=nome_filho,
                    tipo=tipo,
                    categoria_pai_id=pai_id,
                    cor=cor_filho,
                    icone=icone_filho,
                    ativo=True,
                )
            )


def downgrade() -> None:
    # Remove so as categorias de sistema (usuario_id IS NULL) - nunca toca
    # em categorias criadas por usuarios reais.
    op.execute(sa.text("DELETE FROM categorias WHERE usuario_id IS NULL"))
