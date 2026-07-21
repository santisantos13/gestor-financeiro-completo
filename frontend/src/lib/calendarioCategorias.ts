/**
 * Mapa `CategoriaEventoCalendario` → cor do dot/label da legenda do
 * Calendário Financeiro. Ver
 * docs/analise-arquitetural-transferencias-frontend.md.
 *
 * Usa exclusivamente tokens semânticos já existentes (`--color-positive/
 * negative/warning/info/accent`, design-system.md, seção 6) — nenhuma cor
 * nova foi criada para esta etapa. Simplificação deliberada: o pedido
 * original imaginava 8 cores (incluindo Financiamento/Empréstimo
 * separados), mas no modelo real esses dois já são `Transacao` (RECEITA ou
 * DESPESA) — dar a eles uma cor própria exigiria inventar 2 tokens novos só
 * para esta tela, o que design-system.md desaconselha (cor
 * sempre com significado fixo, reaproveitado em todo o sistema, nunca uma
 * exceção local). Ficam agrupados em RECEITA/DESPESA (mesma cor de
 * qualquer outra transação), e o clique no dia continua distinguindo a
 * origem exata pelo ícone (`origemNavegacao.ts`) dentro do Drawer.
 */
import type { CategoriaEventoCalendario } from "../types/enums";

export const COR_DOT_POR_CATEGORIA: Record<CategoriaEventoCalendario, string> = {
  RECEITA: "bg-positive",
  DESPESA: "bg-negative",
  FATURA_FECHAMENTO: "bg-accent",
  FATURA_VENCIMENTO: "bg-warning",
  TRANSFERENCIA: "bg-info",
  META: "bg-text-tertiary",
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
};

export const LABEL_CATEGORIA_EVENTO: Record<CategoriaEventoCalendario, string> = {
  RECEITA: "Receita",
  DESPESA: "Despesa",
  FATURA_FECHAMENTO: "Fechamento de fatura",
  FATURA_VENCIMENTO: "Vencimento de fatura",
  TRANSFERENCIA: "Transferência",
  META: "Prazo de meta",
};

/** Ordem fixa de exibição na legenda — mais frequente/relevante primeiro. */
export const ORDEM_LEGENDA_CALENDARIO: CategoriaEventoCalendario[] = [
  "RECEITA",
  "DESPESA",
  "TRANSFERENCIA",
  "FATURA_FECHAMENTO",
  "FATURA_VENCIMENTO",
  "META",
];
