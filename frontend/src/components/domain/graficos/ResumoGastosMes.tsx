import { ArrowDown, ArrowUp } from "lucide-react";
import { formatMoney } from "../../../utils/format";

export interface ResumoGastosMesProps {
  totalAtual: number;
  /** `null` enquanto o mês anterior ainda carrega/falha - nesse caso o
   * componente mostra só o total, sem variação (nunca um "0%"/"∞%"
   * enganoso). */
  totalAnterior: number | null;
}

/** Seta + variação percentual do gasto do mês vs mês anterior. NÃO
 * reaproveita `ui/TrendIndicator` (usado em `StatCard` para saldo/receita,
 * onde "mais" é sempre bom, verde) porque a semântica aqui é invertida:
 * gasto SUBINDO é a notícia ruim (vermelho), gasto CAINDO é a boa (verde) -
 * mesmo princípio do "Sistema semântico de status" do projeto (tone
 * correto por significado, não por sinal aritmético cru). */
function IndicadorVariacaoGasto({ percentual }: { percentual: number }) {
  const aumentou = percentual >= 0;
  const Icon = aumentou ? ArrowUp : ArrowDown;
  return (
    <span
      className={`tabular inline-flex items-center gap-0.5 text-sm font-medium ${aumentou ? "text-negative" : "text-positive"}`}
    >
      <Icon size={14} aria-hidden="true" />
      {Math.abs(percentual).toFixed(1)}%
    </span>
  );
}

/**
 * Total de gastos do mês selecionado (soma de `gastos_por_categoria`, que
 * cobre 100% das despesas do período - cartão e conta somados, ver
 * docs/analise-arquitetural-graficos.md) + variação vs o mês anterior.
 * Nenhum cálculo de agregação novo aqui: os dois totais já vêm prontos de
 * duas chamadas de `graficos_periodo` (mês atual/anterior) que
 * `GraficosPage` já faz; esta é só a formatação da comparação, mesma
 * aritmética simples (`(atual-anterior)/anterior`) que qualquer dashboard
 * faz sobre dois números já oficiais - não uma regra de negócio nova.
 */
export function ResumoGastosMes({ totalAtual, totalAnterior }: ResumoGastosMesProps) {
  const percentual =
    totalAnterior !== null && totalAnterior > 0 ? ((totalAtual - totalAnterior) / totalAnterior) * 100 : null;

  return (
    <div className="mt-1 flex flex-wrap items-baseline gap-2">
      <span className="font-mono tabular text-h3 font-semibold text-text-primary">{formatMoney(totalAtual)}</span>
      {percentual !== null && <IndicadorVariacaoGasto percentual={percentual} />}
      {totalAnterior !== null && (
        <span className="text-caption text-text-tertiary">vs {formatMoney(totalAnterior)} no mês anterior</span>
      )}
    </div>
  );
}
