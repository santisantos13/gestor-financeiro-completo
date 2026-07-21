"""Schemas de autenticação: payloads de entrada e saída dos endpoints de
`app/api/routes/auth.py`.

Seguem a convenção já estabelecida (`<Entidade>Create`/`<Entidade>Read`) e
nunca expõem `senha_hash` nem qualquer token além do que o próprio fluxo
exige devolver ao cliente que o pediu.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import TipoPapel
from app.schemas.base import OrmBaseModel


class UsuarioCreate(BaseModel):
    """Payload de registro. `max_length=72` não é um número arbitrário: é o
    limite de bytes que o bcrypt suporta (ver app/core/security.py) -
    validado aqui, na borda da API, para o cliente receber um erro 422
    claro em vez de uma falha interna na hora do hash."""

    nome: str = Field(min_length=1, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)


class UsuarioRead(OrmBaseModel):
    """O que a API devolve sobre um usuário - nunca `senha_hash`."""

    id: int
    nome: str
    email: EmailStr
    papel: TipoPapel
    ativo: bool
    criado_em: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    """Resposta de login e de refresh - sempre o par de tokens novo."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expira_em_segundos: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout da sessão atual precisa saber QUAL sessão - por isso recebe o
    refresh_token. Logout global (todas as sessões) não usa este schema,
    só precisa do usuário autenticado (ver AuthService.logout_todas)."""

    refresh_token: str
