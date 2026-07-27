import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { Scale } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { formatMoney, formatMoneyCompacto } from "../../../utils/format";

export interface ItemComparativo {
  nome: string;
  total: string;
}

export interface GastosComparativoChartProps {
  atual: ItemComparativo[];
  anterior: ItemComparativo[];
  labelAtual: string;
  labelAnterior: string;
}

interface LinhaComparativa {
  nome: string;
  totalAtual: number;
  totalAnterior: number;
}

const LIMITE_ITENS = 6;
const COR_ATUAL = "var(--color-accent)";
const COR_ANTERIOR = "var(--color-text-tertiary)";

/** Mescla os dois períodos por `nome` (não por id — os 3 gráficos de
 * período usam domínios de id diferentes entre si, mas `nome` já é a chave
 * de exibição estável em todos). Um item presente só num dos dois meses
 * entra com `0` no outro lado (ex.: categoria nova, ou zerada este mês). */
function mesclarPeriodos(atual: ItemComparativo[], anterior: ItemComparativo[]): LinhaComparativa[] {
  const porNome = new Map<string, LinhaComparativa>();
  for (const item of atual) {
    porNome.set(item.nome, { nome: item.nome, totalAtual: Number(item.total), totalAnterior: 0 });
  }
  for (const item of anterior) {
    const existente = porNome.get(item.nome);
    if (existente) {
      existente.totalAnterior = Number(item.total);
    } else {
      porNome.set(item.nome, { nome: item.nome, totalAtual: 0, totalAnterior: Number(item.total) });
    }
  }
  return Array.from(porNome.values()).sort(
    (a, b) => b.totalAtual - a.totalAtual || b.totalAnterior - a.totalAnterior,
  );
}

/** Agrupa a cauda longa das linhas mescladas — não reaproveita
 * `lib/agruparCaudaLonga.ts` porque aqui há DOIS totais por linha (atual e
 * anterior), que precisam ser somados separadamente para o item "Outros";
 * o helper genérico só sabe somar um valor por item. */
function agruparCaudaComparativa(linhas: LinhaComparativa[], limite: number): LinhaComparativa[] {
  if (linhas.length <= limite) return linhas;
  const principais = linhas.slice(0, limite - 1);
  const resto = linhas.slice(limite - 1);
  return [
    ...principais,
    {
      nome: `Outros (${resto.length})`,
      totalAtual: resto.reduce((soma, item) => soma + item.totalAtual, 0),
      totalAnterior: resto.reduce((soma, item) => soma + item.totalAnterior, 0),
    },
  ];
}

/**
 * Gráfico de barras horizontais agrupadas (mês atual x mês anterior) —
 * genérico por nome/total, reaproveitado pelas 3 seções de "Gastos por X"
 * quando o modo "Comparar com mês anterior" está ativo em `/graficos`
 * (Melhorias de Gráficos, 2026-07-26). Substitui o donut/barra específico
 * daquela seção nesse modo — comparação lado a lado não tem um análogo
 * natural em donut, então um único componente de barras agrupadas serve
 * igualmente para categoria/cartão/conta.
 */
export function GastosComparativoChart({ atual, anterior, labelAtual, labelAnterior }: GastosComparativoChartProps) {
  const linhas = useMemo(
    () => agruparCaudaComparativa(mesclarPeriodos(atual, anterior), LIMITE_ITENS),
    [atual, anterior],
  );

  if (linhas.length === 0) {
    return (
      <EmptyState
        icon={Scale}
        title="Nada para comparar"
        description="Sem gastos neste mês nem no anterior para este agrupamento."
      />
    );
  }

  const altura = Math.max(140, linhas.length * 44);

  return (
    <div>
      <div className="mb-2 flex items-center gap-4 text-caption text-text-tertiary">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COR_ATUAL }} aria-hidden="true" />
          {labelAtual}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COR_ANTERIOR }} aria-hidden="true" />
          {labelAnterior}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={linhas} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 0 }} barGap={2}>
          <CartesianGrid horizontal={false} stroke="var(--color-border-subtle)" />
          <XAxis
            type="number"
            tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-border-subtle)" }}
            tickFormatter={(valor: number) => formatMoneyCompacto(valor)}
          />
          <YAxis
            type="category"
            dataKey="nome"
            tick={{ fontSize: 12, fill: "var(--color-text-tertiary)" }}
            tickLine={false}
            axisLine={false}
            width={100}
          />
          <Tooltip
            cursor={{ fill: "var(--color-surface-3)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const linha = payload[0].payload as LinhaComparativa;
              return (
                <ChartTooltip
                  title={linha.nome}
                  items={[
                    { label: labelAtual, value: formatMoney(linha.totalAtual), color: COR_ATUAL },
                    { label: labelAnterior, value: formatMoney(linha.totalAnterior), color: COR_ANTERIOR },
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="totalAtual" fill={COR_ATUAL} radius={[0, 3, 3, 0]} animationDuration={600} />
          <Bar dataKey="totalAnterior" fill={COR_ANTERIOR} radius={[0, 3, 3, 0]} animationDuration={600} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
