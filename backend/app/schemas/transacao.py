"""Schemas de Transacao: payloads de entrada e saída de
`app/api/routes/transacao.py`.

Validação de FORMATO (tipos, tamanhos, `valor > 0`) fica aqui, no Pydantic.
Validação ESTRUTURAL entre campos (conta_id XOR cartao_id, no máximo um
contrato, numero_parcela condizente com o contrato) mora inteiramente em
`TransacaoService` - não duplicada aqui - porque a mesma regra precisa
valer tanto na criação (payload completo) quanto no PATCH (payload
parcial, `exclude_unset`), e só o Service consegue enxergar o estado FINAL
mesclado nos dois casos. Ver docs/analise-arquitetural-transacao.md.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import StatusTransacao, TipoTransacao
from app.schemas.base import OrmBaseModel
from app.schemas.tag import TagRead


class TransacaoCreate(BaseModel):
    tipo: TipoTransacao
    valor: Decimal = Field(gt=0)
    data: date
    descricao: str = Field(min_length=1, max_length=200)

    # so relevante para transacao de CONTA - PENDENTE se omitido. Ignorado
    # (sempre forcado para PAGO) numa transacao de CARTAO, ver
    # StatusTransacao em app/models/enums.py.
    status: StatusTransacao | None = None

    categoria_id: int | None = None
    conta_id: int | None = None
    cartao_id: int | None = None

    # vinculo manual e opcional a um "contrato" existente - sem validacao
    # de posse nesta etapa (nenhum dos tres tem CRUD/Repository proprio
    # ainda, decisao YAGNI aprovada em docs/analise-arquitetural-transacao.md)
    parcelamento_id: int | None = None
    financiamento_id: int | None = None
    emprestimo_id: int | None = None
    numero_parcela: int | None = Field(default=None, ge=1)

    origem_recorrente_id: int | None = None

    tag_ids: list[int] = Field(default_factory=list)


class TransacaoUpdate(BaseModel):
    """Todos os campos opcionais - semântica de PATCH. `usuario_id`,
    `conta_id` e `cartao_id` nunca aparecem aqui: posse não se atualiza via
    payload, e a identidade estrutural conta-vs-cartão é imutável após a
    criação (trocar exigiria reabrir toda a resolução de fatura - mais
    simples excluir e recriar, mesmo raciocínio de `Fatura.cartao_id`)."""

    tipo: TipoTransacao | None = None
    valor: Decimal | None = Field(default=None, gt=0)
    data: date | None = None
    descricao: str | None = Field(default=None, min_length=1, max_length=200)
    status: StatusTransacao | None = None

    categoria_id: int | None = None
    parcelamento_id: int | None = None
    financiamento_id: int | None = None
    emprestimo_id: int | None = None
    numero_parcela: int | None = Field(default=None, ge=1)

    origem_recorrente_id: int | None = None

    tag_ids: list[int] | None = None


class TransacaoRead(OrmBaseModel):
    id: int
    tipo: TipoTransacao
    valor: Decimal
    data: date
    descricao: str
    status: StatusTransacao

    categoria_id: int | None
    conta_id: int | None
    cartao_id: int | None

    parcelamento_id: int | None
    financiamento_id: int | None
    emprestimo_id: int | None
    numero_parcela: int | None

    origem_recorrente_id: int | None
    # Só LEITURA - `meta_id` não existe mais em `TransacaoCreate`/
    # `TransacaoUpdate` (Refatoramento de Metas/Transferências: aportes/
    # resgates viram `Transferencia`, não `Transacao`). Continua aqui só
    # para expor o histórico legado (transações antigas já marcadas com
    # uma Meta, congeladas - nunca reescritas). Ver
    # docs/analise-arquitetural-metas-transferencias.md, seção 6.
    meta_id: int | None

    fatura_id: int | None
    fatura_paga_id: int | None

    # True somente para parcelas de Financiamento/Empréstimo importadas no
    # onboarding ("parcelas_ja_pagas") - dinheiro que já tinha saído da
    # vida financeira do usuário antes dele começar a usar o app. Exposto
    # aqui só para o frontend poder comunicar isso visualmente, mesmo
    # espírito de `Fatura.importada`; não muda nenhum cálculo do lado do
    # cliente.
    importada: bool

    tags: list[TagRead] = Field(default_factory=list)
