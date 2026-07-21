/**
 * Mapa `CategoriaEventoCalendario` → cor do dot/label da legenda do
 * Calendário Financeiro. Ver
 * docs/analise-arquitetural-transferencias-frontend.md.
 *
 * Usa exclusivamente tokens já existentes no design system — nenhuma cor
 * nova foi criada. RECEITA/DESPESA/FATURA_FECHAMENTO/FATURA_VENCIMENTO/
 * TRANSFERENCIA/META usam os tokens semânticos financeiros (`--color-
 * positive/negative/warning/info/accent`, design-system.md, seção 6).
 *
 * FINANCIAMENTO/EMPRESTIMO (adicionado a pedido do usuário, 2026-07-21:
 * "pode dar uma cor" — antes ficavam agrupados em RECEITA/DESPESA genérico,
 * simplificação documentada aqui anteriormente) reaproveitam `chart-4`/
 * `chart-5` (`--color-chart-4/5`, seção 6.6) em vez de inventar 2 tokens
 * novos — mesmo precedente já usado para promover `info` a partir de
 * `chart-2` (ver nota em index.css). Continuam sem significado financeiro
 * fixo (não são "positivo"/"negativo" - são categorias de ORIGEM, não de
 * sinal), por isso não usam positive/negative/warning.
 */
import type { CategoriaEventoCalendario } from "../types/enums";

export const COR_DOT_POR_CATEGORIA: Record<CategoriaEventoCalendario, string> = {
  RECEITA: "bg-positive",
  DESPESA: "bg-negative",
  FATURA_FECHAMENTO: "bg-accent",
  FATURA_VENCIMENTO: "bg-warning",
  TRANSFERENCIA: "bg-info",
  META: "bg-text-tertiary",
  FINANCIAMENTO: "bg-chart-5",
  EMPRESTIMO: "bg-chart-4",
};

/** Cor de TEXTO (valor monetário do evento) por categoria — companheiro de
 * `COR_DOT_POR_CATEGORIA` (mesmo tom, variante `text-*`). Único lugar que
 * decide essa cor; `EventoDiaDrawer` só lê daqui, nunca reimplementa o
 * ternário. `TRANSFERENCIA` não é nem ganho nem perda de patrimônio (o
 * dinheiro só troca de lugar — ver docstring de `Transferencia` no
 * backend), por isso usa `info` (a mesma cor do dot), nunca positive/negative. */
export const TEXT_COR_POR_CATEGORIA: Record<CategoriaEventoCalendario, string> = {
  RECEITA: "text-positive",
  DESPESA: "text-negative",
  FATURA_FECHAMENTO: "text-accent",
  FATURA_VENCIMENTO: "text-warning",
  TRANSFERENCIA: "text-info",
  META: "text-text-primary",
  FINANCIAMENTO: "text-chart-5",
  EMPRESTIMO: "text-chart-4",
};

export const LABEL_CATEGORIA_EVENTO: Record<CategoriaEventoCalendario, string> = {
  RECEITA: "Receita",
  DESPESA: "Despesa",
  FATURA_FECHAMENTO: "Fechamento de fatura",
  FATURA_VENCIMENTO: "Vencimento de fatura",
  TRANSFERENCIA: "Transferência",
  META: "Prazo de meta",
  FINANCIAMENTO: "Financiamento",
  EMPRESTIMO: "Empréstimo",
};

/** Ordem fixa de exibição na legenda — mais frequente/relevante primeiro. */
export const ORDEM_LEGENDA_CALENDARIO: CategoriaEventoCalendario[] = [
  "RECEITA",
  "DESPESA",
  "FINANCIAMENTO",
  "EMPRESTIMO",
  "TRANSFERENCIA",
  "FATURA_FECHAMENTO",
  "FATURA_VENCIMENTO",
  "META",
];
