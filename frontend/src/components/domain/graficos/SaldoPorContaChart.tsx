import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { Wallet } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney } from "../../../utils/format";
import type { ContaSaldoResumo } from "../../../types/centralFinanceira";

export interface SaldoPorContaChartProps {
  contas: ContaSaldoResumo[];
}

/**
 * "Distribuição do saldo atual por conta" — 5º gráfico da etapa (o "que
 * mais achar válido"), custo zero de backend: reaproveita
 * `SaldoConsolidadoRead.contas`, já usado pelo hero "Saldo total" do
 * Dashboard (docs/analise-arquitetural-graficos.md, seção 1). Contas com
 * saldo negativo (`saldo_atual < 0`) são excluídas do donut — um valor
 * negativo não tem representação sensata como "fatia" de um todo — mas
 * continuam contadas na lista abaixo, com o token `--color-negative`.
 */
export function SaldoPorContaChart({ contas }: SaldoPorContaChartProps) {
  if (contas.length === 0) {
    return (
      <EmptyState
        icon={Wallet}
        title="Nenhuma conta cadastrada"
        description="Cadastre uma conta para ver a distribuição do seu saldo."
      />
    );
  }

  const positivas = contas.filter((c) => Number(c.saldo_atual) > 0);
  const total = contas.reduce((soma, c) => soma + Number(c.saldo_atual), 0);

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
      <ResponsiveContainer width="100%" height={220} className="sm:max-w-[220px]">
        <PieChart>
          <Pie
            data={positivas}
            dataKey={(c: ContaSaldoResumo) => Number(c.saldo_atual)}
            nameKey="nome"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            animationDuration={600}
          >
            {positivas.map((c, indice) => (
              <Cell key={c.id} fill={corCategoricaPorIndice(indice)} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const conta = payload[0].payload as ContaSaldoResumo;
              const indice = positivas.findIndex((c) => c.id === conta.id);
              return (
                <ChartTooltip
                  title={conta.nome}
                  items={[{ label: "Saldo", value: formatMoney(conta.saldo_atual), color: corCategoricaPorIndice(indice) }]}
                />
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="min-w-0 flex-1 space-y-1.5">
        {contas.map((c) => {
          const valor = Number(c.saldo_atual);
          const indicePositiva = positivas.findIndex((p) => p.id === c.id);
          const percentual = total !== 0 ? (valor / total) * 100 : 0;
          return (
            <div key={c.id} className="flex items-center gap-2 text-sm">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: valor < 0 ? "var(--color-negative)" : corCategoricaPorIndice(indicePositiva) }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-text-secondary">{c.nome}</span>
              <span className={`shrink-0 font-mono tabular ${valor < 0 ? "text-negative" : "text-text-primary"}`}>
                {formatMoney(c.saldo_atual)}
              </span>
              {valor >= 0 && <span className="w-10 shrink-0 text-right text-caption text-text-tertiary">{percentual.toFixed(0)}%</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
