"""Cronograma de amortização PRICE/SAC - função pura, sem estado, sem
efeitos colaterais.

Extraído para cá durante a implementação de Emprestimo (ver
docs/analise-arquitetural-emprestimo.md) para não copiar/colar a mesma
matemática de FinanciamentoService pela segunda vez - mesmo raciocínio já
usado em app/core/datas.py (rollover de datas compartilhado entre
Parcelamento/Financiamento/ContaRecorrente). `FinanciamentoService` e
`EmprestimoService` chamam `gerar_cronograma()` a partir dos campos
imutáveis de cada contrato (`ContratoCreditoMixin`) - nenhuma coluna nova
de juros/amortização por parcela precisa existir, o cronograma é sempre
recalculado quando necessário (criação, pagamento).
"""
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import SistemaAmortizacao

_DUAS_CASAS = Decimal("0.01")


def gerar_cronograma(
    principal: Decimal, taxa_juros: Decimal, num_parcelas: int, sistema: SistemaAmortizacao
) -> list[tuple[Decimal, Decimal]]:
    """Retorna `[(valor_parcela, amortizacao), ...]`, uma tupla por parcela
    (1..num_parcelas, na ordem). A ÚLTIMA parcela sempre quita o saldo
    residual, garantindo que a soma das amortizações bate exatamente com
    `principal` (nenhuma sobra/falta de centavo por arredondamento) - mesma
    técnica de `ParcelamentoService._dividir_valor`."""
    if sistema == SistemaAmortizacao.SAC:
        return _gerar_cronograma_sac(principal, taxa_juros, num_parcelas)
    return _gerar_cronograma_price(principal, taxa_juros, num_parcelas)


def _gerar_cronograma_price(
    principal: Decimal, taxa_juros: Decimal, num_parcelas: int
) -> list[tuple[Decimal, Decimal]]:
    """PRICE / Tabela Price / Sistema Francês: parcela fixa
    `PMT = principal * i / (1 - (1+i)^-n)`; cada parcela decompõe em
    `juros = saldo * i` e `amortizacao = PMT - juros`, saldo decrescente.
    Com `i == 0`, degenera para divisão simples."""
    cronograma: list[tuple[Decimal, Decimal]] = []
    saldo = principal
    if taxa_juros == 0:
        parcela_fixa = (principal / num_parcelas).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)
    else:
        fator = (Decimal("1") + taxa_juros) ** num_parcelas
        parcela_fixa = (principal * taxa_juros * fator / (fator - Decimal("1"))).quantize(
            _DUAS_CASAS, rounding=ROUND_HALF_UP
        )

    for indice in range(num_parcelas):
        juros = (saldo * taxa_juros).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)
        if indice == num_parcelas - 1:
            amortizacao = saldo
        else:
            amortizacao = parcela_fixa - juros
        valor_parcela = amortizacao + juros
        cronograma.append((valor_parcela, amortizacao))
        saldo -= amortizacao
    return cronograma


def _gerar_cronograma_sac(
    principal: Decimal, taxa_juros: Decimal, num_parcelas: int
) -> list[tuple[Decimal, Decimal]]:
    """SAC / Sistema de Amortização Constante: `amortizacao = principal / n`
    fixa em todas as parcelas (exceto a última, que absorve o resto do
    arredondamento); `juros = saldo * i` decrescente junto com o saldo -
    por isso a parcela é sempre decrescente ao longo do contrato."""
    cronograma: list[tuple[Decimal, Decimal]] = []
    saldo = principal
    amortizacao_constante = (principal / num_parcelas).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)

    for indice in range(num_parcelas):
        amortizacao = saldo if indice == num_parcelas - 1 else amortizacao_constante
        juros = (saldo * taxa_juros).quantize(_DUAS_CASAS, rounding=ROUND_HALF_UP)
        valor_parcela = amortizacao + juros
        cronograma.append((valor_parcela, amortizacao))
        saldo -= amortizacao
    return cronograma
