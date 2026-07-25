import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { Landmark } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney, formatMoneyCompacto } from "../../../utils/format";
import type { GastoPorConta } from "../../../types/centralFinanceira";

export interface GastosPorContaChartProps {
  gastos: GastoPorConta[];
}

/**
 * "Gastos por conta" — donut, mesmo par (gráfico + legenda) de
 * `GastosPorCategoriaChart`/`SaldoPorContaChart`, paleta categórica por
 * índice (`GastoPorConta` não carrega cor própria, mesma situação de
 * `GastoPorCartao`). Único ponto de diferença deliberado, pedido pelo
 * usuário como inspiração no app do Mercado Pago: o total do período fica
 * escrito no miolo vazio do donut (via `<text>` absoluto sobre o
 * `ResponsiveContainer`), não só na lista ao lado — ver
 * docs/analise-arquitetural-graficos.md, seção 8.
 */
export function GastosPorContaChart({ gastos }: GastosPorContaChartProps) {
  if (gastos.length === 0) {
    return (
      <EmptyState
        icon={Landmark}
        title="Nenhum gasto no período"
        description="Os gastos por conta deste mês aparecem aqui assim que houver despesas lançadas direto de uma conta."
      />
    );
  }

  const total = gastos.reduce((soma, g) => soma + Number(g.total), 0);

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
      <div className="relative w-full sm:max-w-[220px]">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={gastos}
              dataKey={(g: GastoPorConta) => Number(g.total)}
              nameKey="conta_nome"
              innerRadius={55}
              outerRadius={90}
              paddingAngle={2}
              animationDuration={600}
            >
              {gastos.map((g, indice) => (
                <Cell key={g.conta_id} fill={corCategoricaPorIndice(indice)} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.[0]) return null;
                const gasto = payload[0].payload as GastoPorConta;
                const indice = gastos.findIndex((g) => g.conta_id === gasto.conta_id);
                return (
                  <ChartTooltip
                    title={gasto.conta_nome}
                    items={[{ label: "Total", value: formatMoney(gasto.total), color: corCategoricaPorIndice(indice) }]}
                  />
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-caption text-text-tertiary">Total</span>
          <span className="font-mono tabular text-sm font-semibold text-text-primary">
            {formatMoneyCompacto(total)}
          </span>
        </div>
      </div>

      <div className="min-w-0 flex-1 space-y-1.5">
        {gastos.map((g, indice) => {
          const percentual = total > 0 ? (Number(g.total) / total) * 100 : 0;
          return (
            <div key={g.conta_id} className="flex items-center gap-2 text-sm">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: corCategoricaPorIndice(indice) }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-text-secondary">{g.conta_nome}</span>
              <span className="shrink-0 font-mono tabular text-text-primary">{formatMoney(g.total)}</span>
              <span className="w-10 shrink-0 text-right text-caption text-text-tertiary">{percentual.toFixed(0)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
