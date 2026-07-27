import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { Landmark } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { agruparCaudaLonga } from "../../../lib/agruparCaudaLonga";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney, formatMoneyCompacto } from "../../../utils/format";
import type { GastoPorConta } from "../../../types/centralFinanceira";

export interface GastosPorContaChartProps {
  gastos: GastoPorConta[];
  /** Melhorias de Gráficos (2026-07-26) — drill-down: leva para `/transacoes`
   * já filtrado por `conta_id` + período (filtro exato — diferente de
   * "Gastos por cartão", que nunca aparece em `/transacoes`, ver
   * `GastosPorCartaoChart`). Nunca chamado para o item sintético "Outros"
   * (`conta_id: null` só nesse caso, `GastoPorConta.conta_id` real nunca é
   * nulo). */
  onSelecionarConta?: (contaId: number) => void;
}

/** Local apenas — `GastoPorConta.conta_id` nunca é nulo de verdade (o
 * backend sempre resolve uma Conta real); `null` aqui é só o sentinela do
 * item sintético "Outros" montado por `agruparCaudaLonga`. */
type LinhaConta = Omit<GastoPorConta, "conta_id"> & { conta_id: number | null };

const LIMITE_ITENS = 6;

/**
 * "Gastos por conta" — donut, mesmo par (gráfico + legenda) de
 * `GastosPorCategoriaChart`/`SaldoPorContaChart`, paleta categórica por
 * índice (`GastoPorConta` não carrega cor própria, mesma situação de
 * `GastoPorCartao`). Único ponto de diferença deliberado, pedido pelo
 * usuário como inspiração no app do Mercado Pago: o total do período fica
 * escrito no miolo vazio do donut (via `<text>` absoluto sobre o
 * `ResponsiveContainer`), não só na lista ao lado — ver
 * docs/analise-arquitetural-graficos.md, seção 8.
 *
 * Cauda longa agrupada em "Outros" acima de `LIMITE_ITENS` contas (mesma
 * lógica de `GastosPorCategoriaChart`).
 */
export function GastosPorContaChart({ gastos, onSelecionarConta }: GastosPorContaChartProps) {
  const gastosExibidos: LinhaConta[] = useMemo(
    () =>
      agruparCaudaLonga<LinhaConta>(
        gastos,
        (g) => Number(g.total),
        (soma, qtd) => ({ conta_id: null, conta_nome: `Outros (${qtd})`, total: soma.toFixed(2) }),
        LIMITE_ITENS,
      ),
    [gastos],
  );

  if (gastos.length === 0) {
    return (
      <EmptyState
        icon={Landmark}
        title="Nenhum gasto no período"
        description="Os gastos por conta deste mês aparecem aqui assim que houver despesas lançadas direto de uma conta."
      />
    );
  }

  const total = gastosExibidos.reduce((soma, g) => soma + Number(g.total), 0);

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
      <div className="relative w-full sm:max-w-[220px]">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={gastosExibidos}
              dataKey={(g: LinhaConta) => Number(g.total)}
              nameKey="conta_nome"
              innerRadius={55}
              outerRadius={90}
              paddingAngle={2}
              animationDuration={600}
            >
              {gastosExibidos.map((g, indice) => (
                <Cell
                  key={g.conta_id ?? "outros"}
                  fill={corCategoricaPorIndice(indice)}
                  cursor={onSelecionarConta && g.conta_id != null ? "pointer" : undefined}
                  onClick={
                    onSelecionarConta && g.conta_id != null ? () => onSelecionarConta(g.conta_id as number) : undefined
                  }
                />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.[0]) return null;
                const gasto = payload[0].payload as LinhaConta;
                const indice = gastosExibidos.findIndex((g) => g.conta_id === gasto.conta_id);
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
        {gastosExibidos.map((g, indice) => {
          const percentual = total > 0 ? (Number(g.total) / total) * 100 : 0;
          const clicavel = onSelecionarConta != null && g.conta_id != null;
          return (
            <button
              key={g.conta_id ?? "outros"}
              type="button"
              disabled={!clicavel}
              onClick={clicavel ? () => onSelecionarConta!(g.conta_id as number) : undefined}
              className={`flex w-full items-center gap-2 rounded-sm text-sm ${clicavel ? "cursor-pointer hover:bg-surface-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" : "cursor-default"}`}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: corCategoricaPorIndice(indice) }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-left text-text-secondary">{g.conta_nome}</span>
              <span className="shrink-0 font-mono tabular text-text-primary">{formatMoney(g.total)}</span>
              <span className="w-10 shrink-0 text-right text-caption text-text-tertiary">{percentual.toFixed(0)}%</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
