import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { PieChart as PieChartIcon } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney } from "../../../utils/format";
import type { GastoPorCategoria } from "../../../types/centralFinanceira";

export interface GastosPorCategoriaChartProps {
  gastos: GastoPorCategoria[];
}

/**
 * "Gastos por categoria" — donut, paleta categórica (seção 6.6): usa
 * `categoria_cor` quando o backend fornece (a mesma cor do cadastro da
 * Categoria, `ColorPicker`), caindo na paleta categórica por índice quando
 * `categoria_cor` é nulo (categoria sem cor definida, ou "Sem categoria").
 */
export function GastosPorCategoriaChart({ gastos }: GastosPorCategoriaChartProps) {
  if (gastos.length === 0) {
    return (
      <EmptyState
        icon={PieChartIcon}
        title="Nenhum gasto no período"
        description="Os gastos por categoria deste mês aparecem aqui assim que houver despesas lançadas."
      />
    );
  }

  const total = gastos.reduce((soma, g) => soma + Number(g.total), 0);

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
      <ResponsiveContainer width="100%" height={220} className="sm:max-w-[220px]">
        <PieChart>
          <Pie
            data={gastos}
            dataKey={(g: GastoPorCategoria) => Number(g.total)}
            nameKey="categoria_nome"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            animationDuration={600}
          >
            {gastos.map((g, indice) => (
              <Cell key={g.categoria_id ?? `sem-categoria-${indice}`} fill={g.categoria_cor ?? corCategoricaPorIndice(indice)} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const gasto = payload[0].payload as GastoPorCategoria;
              return (
                <ChartTooltip
                  title={gasto.categoria_nome}
                  items={[{ label: "Total", value: formatMoney(gasto.total), color: gasto.categoria_cor ?? "var(--color-chart-6)" }]}
                />
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="min-w-0 flex-1 space-y-1.5">
        {gastos.map((g, indice) => {
          const percentual = total > 0 ? (Number(g.total) / total) * 100 : 0;
          return (
            <div key={g.categoria_id ?? `sem-categoria-${indice}`} className="flex items-center gap-2 text-sm">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: g.categoria_cor ?? corCategoricaPorIndice(indice) }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-text-secondary">{g.categoria_nome}</span>
              <span className="shrink-0 font-mono tabular text-text-primary">{formatMoney(g.total)}</span>
              <span className="w-10 shrink-0 text-right text-caption text-text-tertiary">{percentual.toFixed(0)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
