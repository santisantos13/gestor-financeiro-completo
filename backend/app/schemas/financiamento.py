"""Schemas de Financiamento: payloads de entrada e saída de
`app/api/routes/financiamento.py`.

Sem `FinanciamentoUpdate` - mesmo motivo de Parcelamento/Fatura: todo campo
aqui (`valor_financiado`, `valor_entrada`, `taxa_juros`, `sistema_amortizacao`,
`num_parcelas`, `data_inicio`) é estrutural e determina o cronograma de
amortização inteiro, gerado de uma vez na criação - editar qualquer um
depois desincronizaria as parcelas já geradas e o `saldo_devedor`. A única
transição de estado é a ação `pagar_parcela`
(`POST /financiamentos/{id}/parcelas/{numero_parcela}/pagar`), nunca uma
edição de campo livre. Ver docs/analise-arquitetural-financiamento.md.

Validação estrutural (`conta_id` obrigatório) não é feita aqui via
`model_validator` - mora inteiramente em `FinanciamentoService`, mesmo
raciocínio já documentado em `app/schemas/transacao.py` e
`app/schemas/parcelamento.py`. `parcelas_ja_pagas` segue o mesmo
raciocínio: o limite (`<= num_parcelas`) depende de outro campo do mesmo
schema, então também é validado no Service, não aqui.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import SistemaAmortizacao, StatusContratoCredito
from app.schemas.base import OrmBaseModel


class FinanciamentoCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    instituicao_financeira: str = Field(min_length=1, max_length=120)
    numero_contrato: str | None = Field(default=None, max_length=60)

    valor_financiado: Decimal = Field(gt=0)
    valor_entrada: Decimal | None = Field(default=None, gt=0)
    bem_financiado: str | None = Field(default=None, max_length=200)

    taxa_juros: Decimal = Field(ge=0)
    sistema_amortizacao: SistemaAmortizacao = SistemaAmortizacao.PRICE
    num_parcelas: int = Field(ge=2)
    cet: Decimal | None = Field(default=None, ge=0)
    data_inicio: date

    permite_quitacao_antecipada: bool = True

    conta_id: int | None = None
    categoria_id: int | None = None

    # Etapa de Onboarding (pedido do usuário: "vamos ajudar os usuários a
    # organizar uma vida financeira que provavelmente está bagunçada"):
    # quantas parcelas já foram pagas ANTES de contratar este financiamento
    # no app - ex. um financiamento de carro que já está na parcela 7/48.
    # Default 0 = comportamento de sempre (contrato novo, nenhuma parcela
    # paga ainda). Validado (`<= num_parcelas`) e aplicado em
    # `FinanciamentoService.criar` reaproveitando `pagar_parcela` em loop -
    # nenhuma lógica de decremento de `saldo_devedor`/transição de status
    # duplicada aqui.
    parcelas_ja_pagas: int = Field(default=0, ge=0)


class FinanciamentoRead(OrmBaseModel):
    id: int
    descricao: str
    instituicao_financeira: str
    numero_contrato: str | None

    valor_financiado: Decimal
    valor_entrada: Decimal | None
    bem_financiado: str | None

    taxa_juros: Decimal
    sistema_amortizacao: SistemaAmortizacao
    num_parcelas: int
    cet: Decimal | None
    data_inicio: date

    saldo_devedor: Decimal
    permite_quitacao_antecipada: bool
    status: StatusContratoCredito

    conta_id: int | None
    categoria_id: int | None
