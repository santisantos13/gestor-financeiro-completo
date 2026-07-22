import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { CreditCard } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney, formatMoneyCompacto } from "../../../utils/format";
import type { GastoPorCartao } from "../../../types/centralFinanceira";

export interface GastosPorCartaoChartProps {
  gastos: GastoPorCartao[];
}

/**
 * "Gastos por cartão" — barras horizontais, paleta categórica por índice
 * (`GastoPorCartao` não carrega cor própria do Cartão, diferente de
 * Categoria — ver docs/analise-arquitetural-graficos.md, seção 2.2).
 */
export function GastosPorCartaoChart({ gastos }: GastosPorCartaoChartProps) {
  if (gastos.length === 0) {
    return (
      <EmptyState
        icon={CreditCard}
        title="Nenhuma compra no período"
        description="Os gastos por cartão deste mês aparecem aqui assim que houver compras lançadas."
      />
    );
  }

  const altura = Math.max(120, gastos.length * 40);

  return (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart data={gastos} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 0 }}>
        <XAxis
          type="number"
          tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--color-border-subtle)" }}
          tickFormatter={(valor: number) => formatMoneyCompacto(valor)}
        />
        <YAxis
          type="category"
          dataKey="cartao_nome"
          tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
          tickLine={false}
          axisLine={false}
          width={100}
        />
        <Tooltip
          cursor={{ fill: "var(--color-surface-3)" }}
          content={({ active, payload }) => {
            if (!active || !payload?.[0]) return null;
            const gasto = payload[0].payload as GastoPorCartao;
            const indice = gastos.findIndex((g) => g.cartao_id === gasto.cartao_id);
            return (
              <ChartTooltip
                title={gasto.cartao_nome}
                items={[{ label: "Total", value: formatMoney(gasto.total), color: corCategoricaPorIndice(indice) }]}
              />
            );
          }}
        />
        <Bar dataKey={(g: GastoPorCartao) => Number(g.total)} radius={[0, 3, 3, 0]} animationDuration={600}>
          {gastos.map((g, indice) => (
            <Cell key={g.cartao_id} fill={corCategoricaPorIndice(indice)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
