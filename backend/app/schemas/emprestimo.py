"""Schemas de Emprestimo: payloads de entrada e saída de
`app/api/routes/emprestimo.py`.

Sem `EmprestimoUpdate` - mesmo motivo de Financiamento: todo campo aqui é
estrutural e determina o cronograma de amortização inteiro, gerado de uma
vez na criação. A única transição de estado é a ação `pagar_parcela`
(`POST /emprestimos/{id}/parcelas/{numero_parcela}/pagar`). Ver
docs/analise-arquitetural-emprestimo.md.

Diferença de `FinanciamentoCreate`: `valor_liberado` é obrigatório (não há
"entrada" em empréstimo - o valor inteiro é sempre desembolsado na conta do
usuário), e não existe `valor_entrada`/`bem_financiado` (existe
`finalidade`, campo livre e opcional, só descritivo).

Validação estrutural (`conta_id` obrigatório) não é feita aqui via
`model_validator` - mora inteiramente em `EmprestimoService`, mesmo
raciocínio já documentado em `app/schemas/financiamento.py`.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import SistemaAmortizacao, StatusContratoCredito
from app.schemas.base import OrmBaseModel


class EmprestimoCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    instituicao_financeira: str = Field(min_length=1, max_length=120)
    numero_contrato: str | None = Field(default=None, max_length=60)

    valor_liberado: Decimal = Field(gt=0)
    finalidade: str | None = Field(default=None, max_length=120)

    taxa_juros: Decimal = Field(ge=0)
    sistema_amortizacao: SistemaAmortizacao = SistemaAmortizacao.PRICE
    num_parcelas: int = Field(ge=2)
    cet: Decimal | None = Field(default=None, ge=0)
    data_inicio: date

    permite_quitacao_antecipada: bool = True

    conta_id: int | None = None
    categoria_id: int | None = None

    # Etapa de Onboarding - mesmo campo/raciocínio de `FinanciamentoCreate`:
    # quantas parcelas já foram pagas antes de contratar este empréstimo no
    # app. Default 0 = comportamento de sempre. Validado e aplicado em
    # `EmprestimoService.criar` reaproveitando `pagar_parcela` em loop.
    parcelas_ja_pagas: int = Field(default=0, ge=0)


class EmprestimoRead(OrmBaseModel):
    id: int
    descricao: str
    instituicao_financeira: str
    numero_contrato: str | None

    valor_liberado: Decimal
    finalidade: str | None

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
