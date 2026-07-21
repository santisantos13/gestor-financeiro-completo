"""Schemas de Anexo: payloads de entrada e saída de `app/api/routes/anexo.py`.

Sem `AnexoUpdate` - decisão confirmada explicitamente com o usuário antes da
implementação: Anexo é create + read + soft-delete apenas, sem PATCH (mesmo
raciocínio de Financiamento/Empréstimo - ver
docs/analise-arquitetural-anexo.md).
"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import OrmBaseModel


class AnexoCreate(BaseModel):
    transacao_id: int
    nome_original: str = Field(min_length=1, max_length=255)
    caminho_arquivo: str = Field(min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=100)
    tamanho_bytes: int | None = Field(default=None, ge=0)

    @field_validator("nome_original", "caminho_arquivo", mode="before")
    @classmethod
    def _remover_espacos_nas_pontas(cls, valor: str) -> str:
        # mode="before": mesmo raciocínio já usado em Tag/Cartão/Meta - roda
        # ANTES do min_length ser conferido, senão um valor só de espaços
        # passaria a checagem de tamanho e só viraria vazio depois.
        return valor.strip() if isinstance(valor, str) else valor


class AnexoRead(OrmBaseModel):
    id: int
    transacao_id: int
    nome_original: str
    caminho_arquivo: str
    mime_type: str | None
    tamanho_bytes: int | None
    data_upload: datetime
    ativo: bool
