"""Schemas de Alerta: payloads de entrada e saída de `app/api/routes/alerta.py`.

`entidade_tipo` NÃO aparece em `AlertaCreate` - é DERIVADO do `tipo` pelo
Service (`AlertaService._ENTIDADE_DO_TIPO`), nunca escolhido pelo cliente.
Deixar o cliente enviar os dois abriria a possibilidade de um par
inconsistente (ex: `tipo=LIMITE_CARTAO` com `entidade_tipo=META`), que só
seria pego tarde (na hora de avaliar a condição, com um erro confuso) em
vez de na borda da API.

`condicao` é sempre um `dict` aqui (nunca a string JSON crua que a coluna
`Alerta.condicao` guarda) - na ENTRADA (`AlertaCreate`/`AlertaUpdate`),
`AlertaService._normalizar_condicao` valida e serializa para string antes
de gravar; na SAÍDA (`AlertaRead`), o `field_validator` abaixo desserializa
de volta para `dict` na borda do schema (nunca escrito de volta no
atributo do objeto ORM - mutar um campo mapeado fora de um `create`/
`update` arriscaria o SQLAlchemy tentar persistir um dict na próxima
flush). O formato de cada `tipo` é documentado no Service
(`_normalizar_condicao`), não aqui, para não duplicar a regra em dois
lugares.
"""
import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import TipoAlerta
from app.schemas.base import OrmBaseModel


class AlertaCreate(BaseModel):
    tipo: TipoAlerta
    entidade_id: int = Field(description="Id da entidade (Cartão/Conta/Meta/Conta Recorrente) que este alerta monitora.")
    condicao: dict | None = None


class AlertaUpdate(BaseModel):
    """Só `condicao`/`ativo` são editáveis - `tipo`/`entidade_id` são
    imutáveis após a criação (mudar o alvo de um alerta é, na prática, um
    alerta diferente: exclua e crie outro)."""

    condicao: dict | None = None
    ativo: bool | None = None


class AlertaRead(OrmBaseModel):
    id: int
    tipo: TipoAlerta
    entidade_id: int | None
    condicao: dict | None
    ativo: bool
    ultima_disparada_em: datetime | None
    criado_em: datetime

    # --- Campos CALCULADOS pela avaliação em tempo real (nunca persistidos
    # como um log de notificações - o model Alerta é a REGRA configurada,
    # não um histórico de disparos, ver docstring de `models/alerta.py`).
    # `None` quando o alerta está desativado (não avaliado).
    disparado: bool | None = None
    mensagem: str | None = None

    @field_validator("condicao", mode="before")
    @classmethod
    def _desserializar_condicao(cls, valor):
        """A coluna `Alerta.condicao` guarda a string JSON crua (ver
        docstring do model) - o Service nunca sobrescreve esse atributo do
        objeto ORM (mutar um campo mapeado in-place fora de um fluxo de
        `create`/`update` arriscaria o SQLAlchemy tentar persistir um dict
        na próxima flush, quebrando a coluna `String(500)`). A
        desserialização para o formato de saída (`dict`) acontece aqui, na
        borda do schema, único lugar que precisa dela."""
        if isinstance(valor, str):
            return json.loads(valor)
        return valor
