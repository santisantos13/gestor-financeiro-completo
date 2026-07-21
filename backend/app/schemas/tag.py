"""Schemas de Tag: payloads de entrada e saída de
`app/api/routes/tag.py`.
"""
from pydantic import BaseModel, Field, field_validator

from app.schemas.base import OrmBaseModel

_PADRAO_COR_HEX = r"^#[0-9A-Fa-f]{6}$"


class TagCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    cor: str | None = Field(default=None, pattern=_PADRAO_COR_HEX)

    @field_validator("nome", mode="before")
    @classmethod
    def _remover_espacos_nas_pontas(cls, nome: str) -> str:
        # mode="before": roda ANTES do min_length ser conferido, senao um
        # nome so de espacos (" ") passaria a checagem (tamanho 1) e so
        # viraria vazio depois - min_length nunca pegaria esse caso. Sem a
        # normalizacao, "viagem" e "viagem " tambem seriam nomes DIFERENTES
        # pro UniqueConstraint(usuario_id, nome), esvaziando na pratica a
        # regra de "nome unico por usuario".
        return nome.strip() if isinstance(nome, str) else nome


class TagUpdate(BaseModel):
    """Todos os campos opcionais - semântica de PATCH. `usuario_id` nunca
    aparece aqui: posse não se atualiza via payload."""

    nome: str | None = Field(default=None, min_length=1, max_length=60)
    cor: str | None = Field(default=None, pattern=_PADRAO_COR_HEX)
    ativo: bool | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def _remover_espacos_nas_pontas(cls, nome: str | None) -> str | None:
        return nome.strip() if isinstance(nome, str) else nome


class TagRead(OrmBaseModel):
    id: int
    nome: str
    cor: str | None
    ativo: bool


class TagUso(BaseModel):
    """Resposta de `GET /tags/{id}/uso` - Etapa F10 (Exclusão definitiva,
    `docs/analise-arquitetural-exclusao.md`, seção 2.3). Só informativo:
    Tag nunca bloqueia exclusão por uso, este número existe só para o
    frontend avisar o usuário antes de confirmar."""

    transacoes_vinculadas: int
