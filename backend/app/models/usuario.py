"""Model Usuario - dono de todos os dados financeiros do sistema.

O sistema e multi-usuario: cada Conta, Cartao, Transacao etc. pertence a
exatamente um Usuario. O isolamento entre usuarios (garantir que um usuario
nunca veja dado de outro) e responsabilidade da camada de servico/API, que
vai filtrar toda query por usuario_id - isso sera implementado na etapa de
endpoints, nao faz parte do model.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TipoPapel
from app.models.mixins import TimestampMixin


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    # unique=True -> nao pode haver dois usuarios com o mesmo e-mail (usado no login).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # hash da senha (bcrypt, ver app/core/security.py) - a senha em texto
    # puro NUNCA e armazenada nem passa perto de um log.
    senha_hash: Mapped[str] = mapped_column(String(255))
    # papel usado para autorizacao (ver exigir_papel em app/api/deps.py).
    # So existe TipoPapel.USER hoje - a coluna ja existe pronta pra quando
    # um segundo papel for adicionado.
    papel: Mapped[TipoPapel] = mapped_column(default=TipoPapel.USER)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- relacionamentos (apenas navegacao no Python, nao geram colunas) ---
    # cascade="all, delete-orphan": se um Usuario for excluido, todos os
    # dados financeiros dele somem junto - evita registros orfaos no banco.
    contas: Mapped[list["Conta"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    cartoes: Mapped[list["Cartao"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    categorias: Mapped[list["Categoria"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    transacoes: Mapped[list["Transacao"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    parcelamentos: Mapped[list["Parcelamento"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    financiamentos: Mapped[list["Financiamento"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    emprestimos: Mapped[list["Emprestimo"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    contas_recorrentes: Mapped[list["ContaRecorrente"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    transferencias: Mapped[list["Transferencia"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    metas: Mapped[list["Meta"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    alertas: Mapped[list["Alerta"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    # Anexo NAO tem relationship direta com Usuario - posse e sempre
    # transitiva via Transacao (decisao explicita do usuario nesta etapa,
    # ver docs/analise-arquitetural-anexo.md). "Todos os anexos do usuario"
    # exigiria um JOIN com Transacao, fora do escopo pedido (YAGNI).
    sessoes: Mapped[list["SessaoUsuario"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
