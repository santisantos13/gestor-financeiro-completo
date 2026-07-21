"""Agrega todos os models do dominio financeiro.

O Alembic (em alembic/env.py) importa este pacote inteiro para que TODAS as
tabelas estejam registradas em Base.metadata antes de rodar --autogenerate.
Se um novo model for criado e nao for importado aqui, o Alembic simplesmente
nao vai enxerga-lo e nenhuma migration sera gerada pra ele.
"""
from app.models.usuario import Usuario
from app.models.conta import Conta
from app.models.cartao import Cartao
from app.models.fatura import Fatura
from app.models.categoria import Categoria
from app.models.categoria_oculta_usuario import CategoriaOcultaUsuario
from app.models.tag import Tag
from app.models.parcelamento import Parcelamento
from app.models.financiamento import Financiamento
from app.models.emprestimo import Emprestimo
from app.models.conta_recorrente import ContaRecorrente
from app.models.transferencia import Transferencia
from app.models.meta import Meta
from app.models.transacao import Transacao
from app.models.alerta import Alerta
from app.models.anexo import Anexo
from app.models.sessao_usuario import SessaoUsuario

__all__ = [
    "Usuario",
    "Conta",
    "Cartao",
    "Fatura",
    "Categoria",
    "CategoriaOcultaUsuario",
    "Tag",
    "Transacao",
    "Parcelamento",
    "Financiamento",
    "Emprestimo",
    "ContaRecorrente",
    "Transferencia",
    "Meta",
    "Alerta",
    "Anexo",
    "SessaoUsuario",
]
