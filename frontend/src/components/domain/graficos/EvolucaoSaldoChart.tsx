import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { TrendingUp } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { CORES_POLARIDADE } from "../../../lib/chartColors";
import { formatMoneyCompacto, formatMoney } from "../../../utils/format";
import { nomeMes } from "../../../utils/date";
import type { PontoTendenciaMensal } from "../../../types/centralFinanceira";

export interface EvolucaoSaldoChartProps {
  meses: PontoTendenciaMensal[];
  /** Mini-card do Dashboard usa uma altura menor e esconde os eixos —
   * página `/graficos` usa a versão cheia. */
  compact?: boolean;
}

function rotuloMes(ponto: PontoTendenciaMensal): string {
  return `${nomeMes(ponto.mes).slice(0, 3)}/${String(ponto.ano).slice(2)}`;
}

/**
 * "Evolução do saldo" — área/linha do saldo total ao longo dos últimos N
 * meses (docs/analise-arquitetural-graficos.md, seção 2.1). Cor única
 * (`--color-accent`, nunca positive/negative: o SALDO em si não tem
 * polaridade fixa — só entradas/saídas têm, ver `EntradasSaidasChart`).
 * Draw-in animado só na montagem (`isAnimationActive` default do Recharts
 * já respeita isso — nunca reanima ao trocar de aba com dado em cache,
 * mesma regra do `StatCard`, design-system.md seção 19).
 */
export function EvolucaoSaldoChart({ meses, compact = false }: EvolucaoSaldoChartProps) {
  if (meses.length === 0) {
    return (
      <EmptyState
        icon={TrendingUp}
        title="Sem histórico ainda"
        description="A evolução do saldo aparece aqui assim que houver transações lançadas."
      />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={compact ? 96 : 260}>
      <AreaChart data={meses} margin={compact ? { top: 4, right: 4, left: 4, bottom: 0 } : { top: 8, right: 12, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="evolucaoSaldoGradiente" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CORES_POLARIDADE.accent} stopOpacity={0.35} />
            <stop offset="100%" stopColor={CORES_POLARIDADE.accent} stopOpacity={0} />
          </linearGradient>
        </defs>
        {!compact && (
          <XAxis
            dataKey={rotuloMes}
            tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-border-subtle)" }}
          />
        )}
        {!compact && (
          <YAxis
            tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
            tickLine={false}
            axisLine={false}
            width={64}
            tickFormatter={(valor: number) => formatMoneyCompacto(valor)}
          />
        )}
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.[0]) return null;
            const ponto = payload[0].payload as PontoTendenciaMensal;
            return (
              <ChartTooltip
                title={`${nomeMes(ponto.mes)} de ${ponto.ano}`}
                items={[{ label: "Saldo total", value: formatMoney(ponto.saldo_total), color: CORES_POLARIDADE.accent }]}
              />
            );
          }}
        />
        <Area
          type="monotone"
          dataKey={(ponto: PontoTendenciaMensal) => Number(ponto.saldo_total)}
          stroke={CORES_POLARIDADE.accent}
          strokeWidth={2}
          fill="url(#evolucaoSaldoGradiente)"
          animationDuration={600}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
