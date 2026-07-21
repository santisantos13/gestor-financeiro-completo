"""Schemas de Transferencia: payloads de entrada e saída de
`app/api/routes/transferencia.py`.

Sem `TransferenciaUpdate` - mesma decisão já usada em `Fatura`/`Parcelamento`:
`conta_origem_id`, `conta_destino_id`, `valor` e `data` são estruturais e
imutáveis após a criação (editar qualquer um exigiria refazer o cálculo de
saldo das contas envolvidas); a única transição válida é a ação `cancelar`
(`POST /transferencias/{id}/cancelar`), não uma edição de campo livre.

Validação estrutural (`conta_origem_id` != `conta_destino_id`) não é feita
aqui via `model_validator` - mora inteiramente em `TransferenciaService`,
mesmo raciocínio já documentado em `app/schemas/transacao.py`: evita
duplicar a regra em duas camadas (aqui é ainda mais direto, já que não
existe um `Update` que precisaria repetir a mesma checagem).
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.base import OrmBaseModel


class TransferenciaCreate(BaseModel):
    conta_origem_id: int
    conta_destino_id: int
    valor: Decimal = Field(gt=0)
    data: date
    descricao: str | None = Field(default=None, max_length=200)


class TransferenciaRead(OrmBaseModel):
    id: int
    conta_origem_id: int
    conta_destino_id: int
    valor: Decimal
    data: date
    descricao: str | None
    ativo: bool
