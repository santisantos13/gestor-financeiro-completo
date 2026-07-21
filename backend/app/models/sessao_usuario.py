"""Model SessaoUsuario - uma sessao de login ativa (ou ja encerrada), uma
por refresh token emitido.

Existe para dar suporte a multiplas sessoes simultaneas por usuario (ex:
logado no notebook e no celular ao mesmo tempo - cada um e uma linha aqui)
e para tornar logout/revogacao REAIS: um JWT sozinho e stateless e nao pode
ser "esquecido" pelo servidor antes de expirar - por isso o refresh token
nao e um JWT neste projeto (ver app/core/security.gerar_token_sessao),
e sim um segredo opaco cuja UNICA fonte de validade e esta tabela.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class SessaoUsuario(Base, TimestampMixin):
    __tablename__ = "sessoes_usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)

    # hash SHA-256 do refresh token (ver app/core/security.hash_token_sessao)
    # - o valor bruto do token nunca e armazenado, so o cliente o guarda.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    expira_em: Mapped[datetime] = mapped_column(DateTime)
    # nulo = sessao ainda ativa. Preenchido no logout (dessa sessao ou
    # global) ou quando o token e rotacionado no refresh (o token antigo e
    # revogado e um novo registro e criado para o novo token).
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # metadados opcionais da sessao, usados so para o usuario reconhecer
    # "qual dispositivo e esse" - nunca para decisao de seguranca.
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # 45 = tamanho maximo de um IPv6
    nome_dispositivo: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- relacionamentos ---
    usuario: Mapped["Usuario"] = relationship(back_populates="sessoes")
