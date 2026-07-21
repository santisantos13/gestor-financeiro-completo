/**
 * Formatação de exibição — nunca recalcula nem converte permanentemente um
 * valor Decimal-como-string em number (analise-arquitetural-frontend.md,
 * seção 0). `Number()` é usado só na hora de formatar, nunca guardado em
 * estado. Ver docs/analise-arquitetural-dashboard.md, seção 7.4.
 */

const moneyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

/** Notação compacta nativa do `Intl` ("R$ 1,2 mi", "R$ 123,5 mil") — usada
 * pelos cards "hero" do Dashboard (ver `formatMoneyInteligente` abaixo) em
 * vez de encolher a fonte indefinidamente para caber um valor longo. Etapa
 * de Refinamento UX/UI, item 3 ("valores ultrapassando os cards"): pedido
 * explícito do usuário foi "compactação inteligente (R$ 1,2 mi quando fizer
 * sentido)" em vez de só diminuir o texto. */
const moneyCompactFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** `valor` é sempre a string Decimal que vem da API (ex. "1234.56"). */
export function formatMoney(valor: string | number): string {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return moneyFormatter.format(0);
  return moneyFormatter.format(numero);
}

/** Versão compacta de `formatMoney` ("R$ 1,2 mi") — nunca usada sozinha,
 * sempre como alternativa ao valor cheio quando `formatMoneyInteligente`
 * decide que vale a pena (ver docstring lá). */
export function formatMoneyCompacto(valor: string | number): string {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return moneyCompactFormatter.format(0);
  return moneyCompactFormatter.format(numero);
}

/** A partir de que magnitude a versão cheia ("R$ 123.456,78") já fica longa
 * demais para os cards "hero" do Dashboard — escolhido pelo comprimento real
 * da string formatada (13 caracteres), não por um valor redondo arbitrário. */
const LIMIAR_COMPACTACAO = 100_000;

/** Decide entre valor cheio e compacto pela MAGNITUDE do número-alvo (nunca
 * pelo comprimento variável de um valor intermediário de animação) — ver
 * `StatCard`/`AnimatedNumber`. Abaixo do limiar, sempre o valor cheio
 * (a grande maioria dos valores reais do usuário); a partir dele, a forma
 * compacta, que também resolve o estouro em telas estreitas (mobile) sem
 * precisar reduzir fonte indefinidamente. */
export function formatMoneyInteligente(valor: string | number): string {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return formatMoney(0);
  return Math.abs(numero) >= LIMIAR_COMPACTACAO ? formatMoneyCompacto(numero) : formatMoney(numero);
}

/** Mesmo critério de magnitude de `formatMoneyInteligente`, exposto à parte
 * para quem precisa decidir o formatador ANTES de formatar (`AnimatedNumber`
 * usa isso para nunca trocar de formatador no meio da animação de count-up —
 * a decisão é tomada uma vez, pelo valor-alvo final, não quadro a quadro). */
export function deveCompactarMoney(valor: string | number): boolean {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  return !Number.isNaN(numero) && Math.abs(numero) >= LIMIAR_COMPACTACAO;
}

/** `valor` já vem na escala 0-100 (ex. "42.5" significa 42,5%) — os campos
 * `percentual`/`percentual_medio_metas` do backend usam essa escala, então
 * dividimos por 100 antes do Intl.NumberFormat (que espera fração 0-1 para
 * `style: "percent"`). */
export function formatPercent(valor: string | number): string {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return percentFormatter.format(0);
  return percentFormatter.format(numero / 100);
}

/** Extrai o número puro (usado pelo `AnimatedNumber` para animar frame a
 * frame) sem formatar — mesma regra de nunca guardar em estado além do
 * instante do frame. */
export function toNumber(valor: string | number): number {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  return Number.isNaN(numero) ? 0 : numero;
}

/** Escala tipográfica adaptativa do `StatCard`. Calculada a partir do
 * comprimento do valor-alvo já FORMATADO (nunca do valor animado quadro a
 * quadro do `AnimatedNumber` — os dígitos crescem durante o count-up e
 * recalcular a cada frame faria a fonte "pular" de tamanho no meio da
 * animação). Nunca uma redução uniforme de fonte para todos os cards -
 * só entra num tier menor quem realmente precisa.
 *
 * Etapa de Refinamento UX/UI, item 3 (bug real, com print): os limiares
 * originais ("até 11 caracteres, mantém os 44px de `text-display`") foram
 * calibrados olhando só o comprimento da string, sem levar em conta que os
 * 3 cards do meio de `ResumoFinanceiroSection` são bem mais estreitos
 * (2/12 colunas, ~230-280px de conteúdo) que os 2 cards "hero" das pontas
 * (3/12). A 44px, um número tabular gasta ~25px/caractere - "R$ 1.005,84"
 * (11 caracteres, dentro do limiar antigo) já não cabia nesses cards
 * estreitos e vazava por cima do card vizinho. Limiares recalibrados pelo
 * pior caso real (o card mais estreito do Dashboard), não pelo melhor:
 * `text-display` agora reservado para valores bem curtos (o caso comum,
 * "R$ 176,83"); praticamente todo valor de 3 a 4 dígitos com centavos cai
 * em `text-h1`, ainda grande e legível, sem vazar. Combinado com
 * `formatMoneyInteligente` (compactação "R$ 1,2 mi" a partir de R$ 100 mil)
 * - juntos cobrem tanto o valor "comprido por ser grande" quanto o valor
 * "comprido por ocupar um card estreito". */
export function tamanhoValorHero(formatado: string): string {
  const tamanho = formatado.length;
  if (tamanho <= 9) return "text-display";
  if (tamanho <= 13) return "text-h1";
  if (tamanho <= 17) return "text-h2";
  return "text-h3";
}
