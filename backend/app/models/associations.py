"""Tabelas de associacao (many-to-many) puras, sem colunas proprias alem
das chaves estrangeiras.

Ficam centralizadas aqui para nao misturar a definicao de uma tabela de
juncao com a logica de um model "de verdade" (responsabilidade unica por
arquivo). Se um relacionamento N-N precisar de atributos proprios no
futuro (ex: "aplicada_em" numa tag), ele deixa de ser uma Table simples e
vira uma classe de model normal, com sua propria chave primaria.
"""
from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import Base

# liga Transacao <-> Tag (uma transacao pode ter varias tags, uma tag pode
# estar em varias transacoes). ondelete="CASCADE": se a transacao ou a tag
# forem excluidas, o vinculo na tabela de associacao some junto.
transacao_tag = Table(
    "transacao_tag",
    Base.metadata,
    Column("transacao_id", Integer, ForeignKey("transacoes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)
