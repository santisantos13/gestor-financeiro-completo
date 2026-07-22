import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { BarChart3 } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { CORES_POLARIDADE } from "../../../lib/chartColors";
import { formatMoneyCompacto, formatMoney } from "../../../utils/format";
import { nomeMes } from "../../../utils/date";
import type { PontoTendenciaMensal } from "../../../types/centralFinanceira";

export interface EntradasSaidasChartProps {
  meses: PontoTendenciaMensal[];
}

function rotuloMes(ponto: PontoTendenciaMensal): string {
  return `${nomeMes(ponto.mes).slice(0, 3)}/${String(ponto.ano).slice(2)}`;
}

/**
 * "Entradas x Saídas por mês" — barras agrupadas, cor de POLARIDADE fixa
 * (positive/negative, seção 6.4 — nunca a paleta categórica da seção 6.6,
 * que não tem significado semântico). Sem grid vertical, só linhas guia
 * horizontais sutis (`--color-border-subtle`, design-system.md seção 19).
 */
export function EntradasSaidasChart({ meses }: EntradasSaidasChartProps) {
  if (meses.length === 0) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Sem histórico ainda"
        description="Entradas e saídas por mês aparecem aqui assim que houver transações lançadas."
      />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={meses} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--color-border-subtle)" />
        <XAxis
          dataKey={rotuloMes}
          tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--color-border-subtle)" }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
          tickLine={false}
          axisLine={false}
          width={64}
          tickFormatter={(valor: number) => formatMoneyCompacto(valor)}
        />
        <Tooltip
          cursor={{ fill: "var(--color-surface-3)" }}
          content={({ active, payload }) => {
            if (!active || !payload?.[0]) return null;
            const ponto = payload[0].payload as PontoTendenciaMensal;
            return (
              <ChartTooltip
                title={`${nomeMes(ponto.mes)} de ${ponto.ano}`}
                items={[
                  { label: "Entradas", value: formatMoney(ponto.entradas), color: CORES_POLARIDADE.positivo },
                  { label: "Saídas", value: formatMoney(ponto.saidas), color: CORES_POLARIDADE.negativo },
                ]}
              />
            );
          }}
        />
        <Bar
          dataKey={(ponto: PontoTendenciaMensal) => Number(ponto.entradas)}
          name="Entradas"
          fill={CORES_POLARIDADE.positivo}
          radius={[3, 3, 0, 0]}
          animationDuration={600}
        />
        <Bar
          dataKey={(ponto: PontoTendenciaMensal) => Number(ponto.saidas)}
          name="Saídas"
          fill={CORES_POLARIDADE.negativo}
          radius={[3, 3, 0, 0]}
          animationDuration={600}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
