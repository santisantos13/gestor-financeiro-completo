/**
 * Cores para os gráficos da Etapa de Gráficos (docs/analise-arquitetural-graficos.md,
 * seção 5) — nunca hex hardcoded direto num componente de gráfico, sempre a
 * partir daqui, espelhando design-system.md, seções 6.4 e 6.6.
 *
 * Passadas como string `var(--...)` (não classes Tailwind) porque os
 * componentes do Recharts recebem cor via prop SVG (`fill`/`stroke`), não
 * via `className` — navegadores modernos resolvem `var()` normalmente em
 * atributos de apresentação SVG.
 */

/** Seção 6.4 — polaridade financeira (Evolução do saldo, Entradas x Saídas). */
export const CORES_POLARIDADE = {
  positivo: "var(--color-positive)",
  negativo: "var(--color-negative)",
  accent: "var(--color-accent)",
} as const;

/** Seção 6.6 — paleta categórica de 6 cores (Gastos por categoria/cartão,
 * Saldo por conta), sem nenhuma polaridade. `chart-6` (slate) reservado
 * para "outros/sem categoria", mesmo papel documentado na seção 6.6. */
export const PALETA_CATEGORICA = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "var(--color-chart-6)",
] as const;

/** Ciclo pela paleta categórica por índice — usado quando o backend não
 * fornece uma cor própria (`categoria_cor` nulo, ou `GastoPorCartao`, que
 * não tem cor nenhuma). Índice `-1`/fora do array cai no slate de
 * "outros" (última posição), nunca em `undefined`. */
export function corCategoricaPorIndice(indice: number): string {
  if (indice < 0 || indice >= PALETA_CATEGORICA.length) return PALETA_CATEGORICA[PALETA_CATEGORICA.length - 1];
  return PALETA_CATEGORICA[indice];
}
