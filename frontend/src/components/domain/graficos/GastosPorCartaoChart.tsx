import { useMemo } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../../ui/EmptyState";
import { CreditCard } from "lucide-react";
import { ChartTooltip } from "./ChartTooltip";
import { agruparCaudaLonga } from "../../../lib/agruparCaudaLonga";
import { corCategoricaPorIndice } from "../../../lib/chartColors";
import { formatMoney, formatMoneyCompacto } from "../../../utils/format";
import type { GastoPorCartao } from "../../../types/centralFinanceira";

export interface GastosPorCartaoChartProps {
  gastos: GastoPorCartao[];
  /** Melhorias de Gráficos (2026-07-26) — drill-down: leva para
   * `/cartoes/:id` (página de detalhe do cartão), NUNCA para `/transacoes` -
   * compras de cartão nunca aparecem naquela tabela por desenho
   * (`apenas_conta: true`, pedido explícito do usuário em 2026-07-20), então
   * um filtro por `cartao_id` ali sempre voltaria vazio. O clique funciona
   * tanto na barra quanto na linha da lista abaixo dela (a lista existe
   * principalmente por acessibilidade/teste - um `<Cell>` do Recharts não é
   * navegável por teclado nem por leitor de tela). Nunca chamado para o
   * item sintético "Outros" (`cartao_id: null` só nesse caso). */
  onSelecionarCartao?: (cartaoId: number) => void;
}

/** Local apenas — mesmo raciocínio de `LinhaConta` em `GastosPorContaChart`. */
type LinhaCartao = Omit<GastoPorCartao, "cartao_id"> & { cartao_id: number | null };

const LIMITE_ITENS = 6;

/**
 * "Gastos por cartão" — barras horizontais, paleta categórica por índice
 * (`GastoPorCartao` não carrega cor própria do Cartão, diferente de
 * Categoria — ver docs/analise-arquitetural-graficos.md, seção 2.2).
 *
 * Cauda longa agrupada em "Outros" acima de `LIMITE_ITENS` cartões (mesma
 * lógica de `GastosPorCategoriaChart`/`GastosPorContaChart` - menos comum de
 * disparar aqui na prática, mas mantém o comportamento consistente entre os
 * 3 gráficos de período).
 *
 * Lista clicável abaixo do gráfico (Melhorias de Gráficos, 2026-07-26):
 * diferente dos dois donuts (que já tinham uma lista ao lado, reaproveitada
 * para o drill-down), este gráfico de barras não tinha nenhum elemento HTML
 * de verdade além do SVG do Recharts - um `<Cell onClick>` sozinho não é
 * clicável por teclado nem exposto a leitor de tela. A lista abaixo é a
 * superfície acessível real do drill-down (mesmo padrão de linha dos
 * outros dois gráficos); o clique direto na barra continua funcionando como
 * atalho extra, mas nunca é o único caminho.
 */
export function GastosPorCartaoChart({ gastos, onSelecionarCartao }: GastosPorCartaoChartProps) {
  const gastosExibidos: LinhaCartao[] = useMemo(
    () =>
      agruparCaudaLonga<LinhaCartao>(
        gastos,
        (g) => Number(g.total),
        (soma, qtd) => ({ cartao_id: null, cartao_nome: `Outros (${qtd})`, total: soma.toFixed(2) }),
        LIMITE_ITENS,
      ),
    [gastos],
  );

  if (gastos.length === 0) {
    return (
      <EmptyState
        icon={CreditCard}
        title="Nenhuma compra no período"
        description="Os gastos por cartão deste mês aparecem aqui assim que houver compras lançadas."
      />
    );
  }

  const altura = Math.max(120, gastosExibidos.length * 40);
  const total = gastosExibidos.reduce((soma, g) => soma + Number(g.total), 0);

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={gastosExibidos} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 0 }}>
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
              const gasto = payload[0].payload as LinhaCartao;
              const indice = gastosExibidos.findIndex((g) => g.cartao_id === gasto.cartao_id);
              return (
                <ChartTooltip
                  title={gasto.cartao_nome}
                  items={[{ label: "Total", value: formatMoney(gasto.total), color: corCategoricaPorIndice(indice) }]}
                />
              );
            }}
          />
          <Bar dataKey={(g: LinhaCartao) => Number(g.total)} radius={[0, 3, 3, 0]} animationDuration={600}>
            {gastosExibidos.map((g, indice) => (
              <Cell
                key={g.cartao_id ?? "outros"}
                fill={corCategoricaPorIndice(indice)}
                cursor={onSelecionarCartao && g.cartao_id != null ? "pointer" : undefined}
                onClick={
                  onSelecionarCartao && g.cartao_id != null ? () => onSelecionarCartao(g.cartao_id as number) : undefined
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="space-y-1.5">
        {gastosExibidos.map((g, indice) => {
          const percentual = total > 0 ? (Number(g.total) / total) * 100 : 0;
          const clicavel = onSelecionarCartao != null && g.cartao_id != null;
          return (
            <button
              key={g.cartao_id ?? "outros"}
              type="button"
              disabled={!clicavel}
              onClick={clicavel ? () => onSelecionarCartao!(g.cartao_id as number) : undefined}
              className={`flex w-full items-center gap-2 rounded-sm text-sm ${clicavel ? "cursor-pointer hover:bg-surface-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" : "cursor-default"}`}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: corCategoricaPorIndice(indice) }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-left text-text-secondary">{g.cartao_nome}</span>
              <span className="shrink-0 font-mono tabular text-text-primary">{formatMoney(g.total)}</span>
              <span className="w-10 shrink-0 text-right text-caption text-text-tertiary">{percentual.toFixed(0)}%</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
