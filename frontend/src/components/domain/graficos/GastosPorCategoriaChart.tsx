import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { PieChart as PieChartIcon } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { agruparCaudaLonga } from "../../../lib/agruparCaudaLonga";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney } from "../../../utils/format";
import type { GastoPorCategoria } from "../../../types/centralFinanceira";

export interface GastosPorCategoriaChartProps {
  gastos: GastoPorCategoria[];
  /** Melhorias de Gráficos (2026-07-26) — drill-down: quando fornecido, cada
   * fatia/linha com `categoria_id` real (nunca "Sem categoria" nem o item
   * sintético "Outros", ambos `categoria_id: null`) vira clicável, levando
   * para `/transacoes` já filtrado por aquela categoria e período. */
  onSelecionarCategoria?: (categoriaId: number) => void;
}

const LIMITE_ITENS = 6;

/**
 * "Gastos por categoria" — donut, paleta categórica (seção 6.6): usa
 * `categoria_cor` quando o backend fornece (a mesma cor do cadastro da
 * Categoria, `ColorPicker`), caindo na paleta categórica por índice quando
 * `categoria_cor` é nulo (categoria sem cor definida, ou "Sem categoria").
 *
 * Cauda longa agrupada em "Outros" (`agruparCaudaLonga`) quando há mais de
 * `LIMITE_ITENS` categorias no período — evita donut/legenda ilegíveis para
 * quem tem muitas categorias cadastradas (Melhorias de Gráficos, 2026-07-26).
 */
export function GastosPorCategoriaChart({ gastos, onSelecionarCategoria }: GastosPorCategoriaChartProps) {
  const gastosExibidos = useMemo(
    () =>
      agruparCaudaLonga(
        gastos,
        (g) => Number(g.total),
        (soma, qtd) => ({
          categoria_id: null,
          categoria_nome: `Outros (${qtd})`,
          categoria_cor: "var(--color-chart-6)",
          categoria_icone: null,
          total: soma.toFixed(2),
        }),
        LIMITE_ITENS,
      ),
    [gastos],
  );

  if (gastos.length === 0) {
    return (
      <EmptyState
        icon={PieChartIcon}
        title="Nenhum gasto no período"
        description="Os gastos por categoria deste mês aparecem aqui assim que houver despesas lançadas."
      />
    );
  }

  const total = gastosExibidos.reduce((soma, g) => soma + Number(g.total), 0);

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
      <ResponsiveContainer width="100%" height={220} className="sm:max-w-[220px]">
        <PieChart>
          <Pie
            data={gastosExibidos}
            dataKey={(g: GastoPorCategoria) => Number(g.total)}
            nameKey="categoria_nome"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            animationDuration={600}
          >
            {gastosExibidos.map((g, indice) => (
              <Cell
                key={g.categoria_id ?? `sem-categoria-${indice}`}
                fill={g.categoria_cor ?? corCategoricaPorIndice(indice)}
                cursor={onSelecionarCategoria && g.categoria_id != null ? "pointer" : undefined}
                onClick={
                  onSelecionarCategoria && g.categoria_id != null
                    ? () => onSelecionarCategoria(g.categoria_id as number)
                    : undefined
                }
              />
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
        {gastosExibidos.map((g, indice) => {
          const percentual = total > 0 ? (Number(g.total) / total) * 100 : 0;
          const clicavel = onSelecionarCategoria != null && g.categoria_id != null;
          return (
            <button
              key={g.categoria_id ?? `sem-categoria-${indice}`}
              type="button"
              disabled={!clicavel}
              onClick={clicavel ? () => onSelecionarCategoria!(g.categoria_id as number) : undefined}
              className={`flex w-full items-center gap-2 rounded-sm text-sm ${clicavel ? "cursor-pointer hover:bg-surface-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" : "cursor-default"}`}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: g.categoria_cor ?? corCategoricaPorIndice(indice) }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-left text-text-secondary">{g.categoria_nome}</span>
              <span className="shrink-0 font-mono tabular text-text-primary">{formatMoney(g.total)}</span>
              <span className="w-10 shrink-0 text-right text-caption text-text-tertiary">{percentual.toFixed(0)}%</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
