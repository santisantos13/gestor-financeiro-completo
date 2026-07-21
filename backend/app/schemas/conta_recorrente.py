"""Schemas de ContaRecorrente: payloads de entrada e saída de
`app/api/routes/conta_recorrente.py`.

Diferente de Fatura/Parcelamento/Transferência, ContaRecorrente TEM um
`ContaRecorrenteUpdate` (PATCH) para os campos do template - editar o
template só afeta ocorrências FUTURAS (cada ocorrência já gerada é uma
Transacao independente, que nunca volta a ler o template depois de criada).

Expansão 2026-07-20 (docs/analise-arquitetural-conta-recorrente-expansao.md):
`dia_vencimento` virou opcional (só se aplica a frequências baseadas em
meses - a validação por família mora no Service, mesmo raciocínio de
sempre); `Read` expõe `status` (ATIVA/PAUSADA/ENCERRADA, substitui `ativo`)
e `proxima_execucao` (o cursor materializado - o frontend mostra "próxima
ocorrência" direto daqui, sem recalcular nada no cliente).

Validação estrutural (`conta_id` XOR `cartao_id`, dia_vencimento ×
frequência) não é feita aqui via `model_validator` - mora inteiramente em
`ContaRecorrenteService`, mesmo raciocínio já documentado em
`app/schemas/transacao.py`.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import FrequenciaRecorrencia, StatusRecorrencia, TipoTransacao
from app.schemas.base import OrmBaseModel


class ContaRecorrenteCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    valor: Decimal = Field(gt=0)
    tipo: TipoTransacao
    frequencia: FrequenciaRecorrencia = FrequenciaRecorrencia.MENSAL
    # Obrigatório para frequências baseadas em meses, proibido nas
    # baseadas em dias - validado no Service (erro claro nos 2 sentidos).
    dia_vencimento: int | None = Field(default=None, ge=1, le=31)

    categoria_id: int | None = None
    conta_id: int | None = None
    cartao_id: int | None = None

    data_inicio: date
    data_fim: date | None = None


class ContaRecorrenteUpdate(BaseModel):
    """Todos os campos opcionais - semântica de PATCH. Nunca retroage sobre
    ocorrências já geradas. `status`/`proxima_execucao` NUNCA são editáveis
    por aqui - transições de estado são ações de negócio explícitas
    (pausar/reativar/encerrar), e o cursor é 100% gerenciado pelo Service."""

    descricao: str | None = Field(default=None, min_length=1, max_length=200)
    valor: Decimal | None = Field(default=None, gt=0)
    tipo: TipoTransacao | None = None
    frequencia: FrequenciaRecorrencia | None = None
    dia_vencimento: int | None = Field(default=None, ge=1, le=31)

    categoria_id: int | None = None
    conta_id: int | None = None
    cartao_id: int | None = None

    data_inicio: date | None = None
    data_fim: date | None = None


class SincronizacaoRecorrentesResult(BaseModel):
    """Resposta de `POST /contas-recorrentes/sincronizar` - o frontend usa
    `geradas > 0` para decidir se invalida os caches (evita refetch em
    cascata a cada login sem novidade)."""

    geradas: int
    encerradas: int


class ContaRecorrenteRead(OrmBaseModel):
    id: int
    descricao: str
    valor: Decimal
    tipo: TipoTransacao
    frequencia: FrequenciaRecorrencia
    dia_vencimento: int | None
    status: StatusRecorrencia
    proxima_execucao: date

    categoria_id: int | None
    conta_id: int | None
    cartao_id: int | None

    data_inicio: date
    data_fim: date | None
