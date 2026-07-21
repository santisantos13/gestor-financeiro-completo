"""Schemas de Fatura: payloads de entrada e saída de `app/api/routes/fatura.py`.

`valor_total` e `status` em `FaturaRead` são sempre CALCULADOS por
`FaturaService` (nunca lidos direto das colunas `Fatura.valor_total`/
`Fatura.status` sem passar pelo Service) - ver docs/analise-arquitetural-fatura.md.
Por isso os dois usam `validation_alias` apontando para atributos
transientes (`valor_total_calculado`/`status_calculado`) que o Service
anexa ao objeto ORM antes de serializar - o mesmo princípio de
`ContaRead.saldo_atual`/`CartaoRead.limite_disponivel`, mas com um cuidado
a mais aqui: como `valor_total`/`status` já são colunas REAIS do model,
usar o mesmo nome do atributo transiente faria `setattr` sobrescrever o
valor rastreado pelo SQLAlchemy (risco real de commitar um `status`
derivado, tipo PARCIALMENTE_PAGA, que nunca deveria ir para o banco). Os
nomes diferentes evitam esse risco por construção.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import StatusFatura
from app.schemas.base import OrmBaseModel


class FaturaCreate(BaseModel):
    cartao_id: int
    # primeiro dia do mes de referencia (ex: 2026-07-01). data_fechamento/
    # data_vencimento NUNCA sao aceitas do cliente - sempre derivadas de
    # Cartao.dia_fechamento/dia_vencimento por FaturaService.criar().
    mes_referencia: date

    @field_validator("mes_referencia")
    @classmethod
    def _validar_primeiro_dia_do_mes(cls, valor: date) -> date:
        if valor.day != 1:
            raise ValueError("mes_referencia deve ser o primeiro dia do mês (ex: 2026-07-01).")
        return valor


class FaturaImportarCreate(BaseModel):
    """Import de uma fatura HISTÓRICA - um ciclo que já aconteceu (e já foi
    total ou parcialmente pago) antes do usuário começar a usar o app.
    Pedido do usuário: "não quero tantas restrições, só o valor da fatura
    que ele já pagou antes" - recriar cada compra individualmente só para
    conseguir fechar/pagar a fatura seria o oposto disso.

    Diferente de `FaturaCreate` (sempre nasce ABERTA; `valor_total` sempre
    DERIVADO de `Transacao` reais, nunca aceito do cliente - ver
    docstring do módulo), aqui a fatura já nasce FECHADA e `valor_total` é
    informado diretamente. Exceção deliberada e explícita ao invariante
    "valor_total nunca vem do cliente" - só para este fluxo de import, que
    representa um documento que já existia fora do app; qualquer fatura
    criada por `POST /faturas` continua 100% derivada como sempre.

    Depois de importada, use `POST /faturas/{id}/pagamentos` (já aceita
    `data` no passado, nenhuma mudança necessária lá) para registrar
    quanto já foi pago, se for o caso - sem isso, a fatura fica FECHADA
    com saldo em aberto, como qualquer fatura fechada e ainda não paga."""

    cartao_id: int
    mes_referencia: date
    valor_total: Decimal = Field(gt=0)

    @field_validator("mes_referencia")
    @classmethod
    def _validar_primeiro_dia_do_mes(cls, valor: date) -> date:
        if valor.day != 1:
            raise ValueError("mes_referencia deve ser o primeiro dia do mês (ex: 2026-07-01).")
        return valor


class FaturaPagamentoCreate(BaseModel):
    valor: Decimal = Field(gt=0)
    data: date
    descricao: str | None = Field(default=None, max_length=200)


class FaturaAjusteManualUpdate(BaseModel):
    """Declara o "saldo já utilizado" do ciclo ABERTO diretamente, sem
    nenhuma Transacao por trás - pedido explícito do usuário ("...
    independentemente de transações"). `ge=0`: é um valor já gasto, nunca
    negativo (para "descontar" um valor errado, o usuário reduz este mesmo
    número - editar sempre define o total, nunca soma/subtrai em cima do
    que já estava salvo, mesmo padrão de PATCH em qualquer outro cadastro
    do projeto). Só aceito com a fatura ABERTA - ver
    `FaturaService.ajustar_saldo_inicial`."""

    ajuste_manual: Decimal = Field(ge=0)


class FaturaAjustePosFechamentoCreate(BaseModel):
    """Soma um valor esquecido ao total de uma fatura JÁ FECHADA (ou paga/
    atrasada/parcialmente paga) - pedido explícito do usuário (2026-07-20):
    "quero adicionar uma transação em uma fatura que já foi fechada e
    paga, porém tinha esquecido dela antes". Entre as opções oferecidas, o
    usuário escolheu a mais simples: só ajustar o número, sem criar uma
    Transacao de verdade (sem categoria/tags, não aparece em Transações) -
    ver `FaturaService.ajustar_valor_pos_fechamento`.

    Diferente de `FaturaAjusteManualUpdate` (SUBSTITUI o valor, só
    enquanto ABERTA), este SOMA ao que já estava ajustado - o usuário
    informa só o valor esquecido, sem precisar saber/recalcular o total já
    congelado. `gt=0`: sempre um valor a mais (para corrigir um valor a
    menos, o caminho é excluir a fatura ou reabrir uma discussão manual -
    este endpoint não cobre remover valor de uma fatura já fechada)."""

    valor: Decimal = Field(gt=0)


class FaturaPagamentoEmLoteCreate(BaseModel):
    """Pedido explícito do usuário (2026-07-20): "seria interessante poder
    pagar todas selecionadas" — até então só existia `POST
    /faturas/{id}/pagamentos`, uma fatura por vez. Diferente de
    `FaturaPagamentoCreate`, não recebe `valor`: cada fatura selecionada é
    paga pelo seu próprio RESTANTE (`valor_total_calculado - valor_pago`),
    nunca um valor único digitado para todas — faturas diferentes quase
    sempre têm saldos diferentes (ver `FaturaService.pagar_em_lote`). Uma
    única `data` se aplica a todos os pagamentos do lote (mesma data real
    de pagamento, ex.: um boleto único que quitou várias faturas do
    mesmo cartão)."""

    fatura_ids: list[int] = Field(min_length=1)
    data: date


class FaturaPagamentoEmLoteResult(BaseModel):
    """Quantas faturas do lote foram de fato pagas — pode ser menor que
    `len(fatura_ids)` porque faturas ABERTAS ou já totalmente quitadas são
    puladas silenciosamente (ver docstring de
    `FaturaService.pagar_em_lote`). O frontend usa essa diferença para
    avisar o usuário quando nem tudo que ele selecionou foi processado."""

    pagas: int


class FaturaExclusaoEmLote(BaseModel):
    """Pedido explícito do usuário: "quero poder selecionar várias faturas
    para excluir" - até então só existia `DELETE /faturas/{id}`, uma por
    vez. `min_length=1` rejeita uma lista vazia (nada pra fazer) antes de
    chegar no Service. Sem limite superior - mesmo raciocínio de
    `CartaoService._LIMITE_CASCATA_EXCLUSAO`/`ContaService`: nenhum usuário
    real teria uma lista grande o bastante pra precisar de um teto
    artificial aqui."""

    fatura_ids: list[int] = Field(min_length=1)


class FaturaRead(OrmBaseModel):
    id: int
    cartao_id: int
    mes_referencia: date
    data_fechamento: date
    data_vencimento: date
    valor_pago: Decimal
    valor_total: Decimal = Field(validation_alias="valor_total_calculado")
    status: StatusFatura = Field(validation_alias="status_calculado")
    importada: bool
    ajuste_manual: Decimal
