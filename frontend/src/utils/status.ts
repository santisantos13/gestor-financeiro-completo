/**
 * Sistema semântico de status — funções puras reutilizáveis por QUALQUER
 * entidade do projeto (revisão de UX de Cartões formalizou isso como
 * padrão do sistema inteiro, não só de Cartão): decide o `tone` correto
 * (`positive`/`info`/`warning`/`negative`/`neutral`, design-system.md,
 * seção 6.4) a partir de um dado bruto (percentual utilizado, dias até um
 * prazo), em vez de cada tela reimplementar seu próprio limiar com uma
 * cor "que combina com o layout". Cor aqui é sempre significado, nunca
 * decoração — a mesma regra dura já registrada para Badge/ProgressBar.
 *
 * Hoje consumido por Cartão (limite/vencimento de fatura); nasce pronto
 * para Transação, Parcelamento, Conta Recorrente, Financiamento,
 * Empréstimo e Meta usarem exatamente a mesma régua quando cada um
 * precisar de um indicador de "quão perto do limite/prazo" — sem
 * duplicar o limiar em cada entidade nova.
 */
export type ToneSemantico = "positive" | "info" | "warning" | "negative";

/** Percentual de um limite/orçamento utilizado (0-100+, pode passar de
 * 100 — nunca clampado aqui, quem exibe decide se clampa visualmente).
 * `positive` (saudável) até 80%, `warning` (atenção) de 80% a 100%,
 * `negative` (estourado) a partir de 100%. Usado hoje por
 * `CartaoVisual`/`CartaoResumoCard`/`CartoesCard` (limite de cartão);
 * mesmo cálculo serve para "% de uma Meta atingido" ou "% de um
 * orçamento de Categoria gasto" quando essas telas existirem. */
export function tonePorUtilizacao(percentual: number): ToneSemantico {
  if (percentual >= 100) return "negative";
  if (percentual >= 80) return "warning";
  return "positive";
}

/** Urgência de um prazo a partir da diferença em dias (positivo = no
 * futuro, negativo = no passado — mesmo sinal de `utils/date.ts`,
 * `diferencaEmDias`). `negative` quando já atrasado ou vence hoje/amanhã
 * (≤1 dia — não faz sentido tratar "vence amanhã" como uma mera
 * "atenção"), `warning` até 7 dias (janela de uma semana, prazo real mas
 * ainda dá tempo de agir), `info` daí em diante (prazo distante — ainda
 * vale mostrar a informação, mas sem competir visualmente com o que
 * precisa de ação agora). Usado hoje por `CartaoVisual` (fecha/vence) e
 * `ProximaFaturaCard`; mesma régua serve para vencimento de parcela,
 * ocorrência de Conta Recorrente, ou prazo de Meta no futuro. */
export function tonePorPrazo(diferencaDias: number): ToneSemantico {
  if (diferencaDias <= 1) return "negative";
  if (diferencaDias <= 7) return "warning";
  return "info";
}

/** Classe Tailwind de cor de TEXTO por tone — mapa estático (nunca
 * interpolação de string tipo `text-${tone}`, que o JIT do Tailwind não
 * consegue detectar em tempo de build). Centraliza o que antes cada
 * componente reinventava com seu próprio ternário
 * (`CartaoVisual`/`CartaoResumoCard`/`CartoesCard` tinham cada um o seu). */
export const TEXT_TONE_CLASS: Record<ToneSemantico, string> = {
  positive: "text-positive",
  negative: "text-negative",
  warning: "text-warning",
  info: "text-info",
};
