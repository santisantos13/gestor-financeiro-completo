"""Schemas de Parcelamento: payloads de entrada e saída de
`app/api/routes/parcelamento.py`.

Sem `ParcelamentoUpdate` - não existe `PATCH` genérico para esta entidade
(mesma decisão de `Fatura`, por um motivo ainda mais forte aqui):
`valor_total`, `num_parcelas`, `data_inicio`, `cartao_id`/`conta_id` são
estruturais e imutáveis após a criação (mudar qualquer um exigiria
regenerar/renumerar parcelas já existentes); a única transição válida é a
ação `cancelar` (`POST /parcelamentos/{id}/cancelar`), não uma edição de
campo livre.

Validação estrutural (`cartao_id` XOR `conta_id`) não é feita aqui via
`model_validator` - mora inteiramente em `ParcelamentoService`, mesmo
raciocínio já documentado em `app/schemas/transacao.py`: evita duplicar a
regra em duas camadas.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.base import OrmBaseModel


class ParcelamentoCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    valor_total: Decimal = Field(gt=0)
    num_parcelas: int = Field(ge=2)
    taxa_juros: Decimal | None = Field(default=None, ge=0)
    data_inicio: date

    # Opcional - Pydantic-only, NÃO é uma coluna do model (não precisou de
    # migration): quando informado, cada uma das N parcelas nasce com
    # exatamente este valor (sem a última absorver resto de arredondamento,
    # diferente do comportamento padrão) em vez de `valor_total` dividido
    # igualmente. Existe para o caso real em que a loja/operadora já cobra
    # um valor de parcela fixo que embute juros (ou desconto à vista) e não
    # bate com uma divisão exata de `valor_total` - ver
    # `ParcelamentoService._gerar_parcelas`. `valor_total` continua sendo
    # sempre gravado como está (o preço "de referência" da compra), mesmo
    # quando a soma das parcelas não fecha exatamente nele.
    valor_parcela: Decimal | None = Field(default=None, gt=0)

    categoria_id: int | None = None
    cartao_id: int | None = None
    conta_id: int | None = None


class ParcelamentoRead(OrmBaseModel):
    id: int
    descricao: str
    valor_total: Decimal
    num_parcelas: int
    taxa_juros: Decimal | None
    data_inicio: date
    ativo: bool

    categoria_id: int | None
    cartao_id: int | None
    conta_id: int | None
