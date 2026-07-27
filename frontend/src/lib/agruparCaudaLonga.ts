/**
 * Melhorias de Gráficos (2026-07-26) — agrupa a cauda longa de uma lista já
 * ordenada (maior total primeiro, mesma garantia de
 * `CentralFinanceiraService.graficos_periodo`: os 3 agrupamentos já vêm
 * ordenados por `total` desc) num único item sintético "Outros", evitando
 * donuts/legendas poluídos quando o usuário tem muitas categorias/contas/
 * cartões cadastrados. Genérico por design — usado por
 * `GastosPorCategoriaChart`, `GastosPorContaChart` e `GastosPorCartaoChart`,
 * cada um com seu próprio shape de item (nenhum agrupamento aqui conhece
 * `categoria_nome`/`conta_nome` etc., só recebe um acessor de total e uma
 * fábrica do item "Outros" no shape certo). `GastosComparativoChart` faz seu
 * próprio agrupamento (2 totais por linha - atual e anterior - não cabem no
 * acessor único deste helper).
 */
export function agruparCaudaLonga<T>(
  itensOrdenados: T[],
  obterTotal: (item: T) => number,
  montarOutros: (somaOutros: number, quantidadeAgrupada: number) => T,
  limite = 6,
): T[] {
  if (itensOrdenados.length <= limite) return itensOrdenados;

  const principais = itensOrdenados.slice(0, limite - 1);
  const resto = itensOrdenados.slice(limite - 1);
  const somaResto = resto.reduce((soma, item) => soma + obterTotal(item), 0);

  return [...principais, montarOutros(somaResto, resto.length)];
}
