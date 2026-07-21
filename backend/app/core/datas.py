"""Utilitário compartilhado de aritmética de datas por mês.

Extraído de `FaturaService` (onde nasceu como `_proximo_mes`/`_dia_valido`,
privados) porque `ParcelamentoService` precisa exatamente do mesmo cálculo
para datar as parcelas de uma compra parcelada - duplicar essas duas
funções pequenas em dois Services violaria o mesmo princípio de "evitar
duplicação de regras" já aplicado em toda parte deste projeto. Nenhuma
abstração nova além de duas funções puras: não é uma classe, não guarda
estado, não depende de nada além da stdlib.
"""
import calendar
from datetime import date, timedelta

from app.models.enums import FrequenciaRecorrencia


def proximo_mes(ano: int, mes: int) -> tuple[int, int]:
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def somar_meses(ano: int, mes: int, n: int) -> tuple[int, int]:
    """Generalização de `proximo_mes` (que vira o caso particular n=1) -
    criada na expansão de Conta Recorrente para BIMESTRAL/TRIMESTRAL/
    SEMESTRAL/ANUAL (ver docs/analise-arquitetural-conta-recorrente-expansao.md,
    seção 3.1). `proximo_mes` permanece intocada: Parcelamento/Fatura
    continuam usando a função que sempre usaram."""
    total = (ano * 12) + (mes - 1) + n
    return total // 12, (total % 12) + 1


def dia_valido(ano: int, mes: int, dia: int) -> date:
    """Mesmo dia do mês pedido, ou o último dia válido daquele mês se ele
    não existir (ex: dia 31 pedido em fevereiro vira 28 ou 29)."""
    ultimo_dia_do_mes = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia_do_mes))


# Intervalo em DIAS das frequências baseadas em dias. QUINZENAL = 14 dias
# fixos - decisão explícita do usuário (2026-07-20), não "duas vezes por
# mês em dias fixos".
_DIAS_POR_FREQUENCIA: dict[FrequenciaRecorrencia, int] = {
    FrequenciaRecorrencia.DIARIA: 1,
    FrequenciaRecorrencia.SEMANAL: 7,
    FrequenciaRecorrencia.QUINZENAL: 14,
}

# Intervalo em MESES das frequências baseadas em meses.
_MESES_POR_FREQUENCIA: dict[FrequenciaRecorrencia, int] = {
    FrequenciaRecorrencia.MENSAL: 1,
    FrequenciaRecorrencia.BIMESTRAL: 2,
    FrequenciaRecorrencia.TRIMESTRAL: 3,
    FrequenciaRecorrencia.SEMESTRAL: 6,
    FrequenciaRecorrencia.ANUAL: 12,
}

FREQUENCIAS_BASEADAS_EM_DIAS = frozenset(_DIAS_POR_FREQUENCIA)
FREQUENCIAS_BASEADAS_EM_MESES = frozenset(_MESES_POR_FREQUENCIA)


def avancar_data(data: date, frequencia: FrequenciaRecorrencia, dia_vencimento: int | None) -> date:
    """A ÚNICA função de avanço de datas de recorrência - toda frequência
    passa por aqui (ver docs/analise-arquitetural-conta-recorrente-expansao.md,
    seção 3.1; unicidade é decisão explícita do usuário, 2026-07-20).

    Frequências baseadas em dias somam um intervalo fixo (`dia_vencimento`
    não se aplica - a âncora do dia da semana/quinzena é a própria data
    anterior, que remonta à `data_inicio` do template). Frequências
    baseadas em meses somam N meses e clampam em `dia_vencimento` via
    `dia_valido` - o clamp NUNCA "gruda": dia 31 vira 28 em fevereiro,
    mas volta a ser 31 em março, porque cada avanço parte de
    `dia_vencimento` (o desejado), não do dia da data anterior."""
    dias = _DIAS_POR_FREQUENCIA.get(frequencia)
    if dias is not None:
        return data + timedelta(days=dias)

    meses = _MESES_POR_FREQUENCIA[frequencia]
    if dia_vencimento is None:  # pragma: no cover - Service valida antes
        raise ValueError(f"dia_vencimento é obrigatório para frequência {frequencia.value}.")
    ano, mes = somar_meses(data.year, data.month, meses)
    return dia_valido(ano, mes, dia_vencimento)
