/**
 * Mapa único `origem_tipo` → ícone/rota de navegação, compartilhado por
 * `AgendaFinanceiraCard` (Dashboard) e `CalendarioFinanceiro`/`EventoDiaDrawer`
 * (Etapa de Calendário Financeiro) — extraído para cá para os dois nunca
 * divergirem (antes só existia dentro de `AgendaFinanceiraCard.tsx`). Ver
 * docs/analise-arquitetural-transferencias-frontend.md.
 *
 * `ROTA_POR_ORIGEM` só tem entrada para os tipos onde `origem_id` já é
 * suficiente para montar a URL sem uma chamada extra ao backend. `FATURA`
 * fica de fora de propósito (o evento traz o id da fatura, não o
 * `cartao_id` que `/cartoes/:id` precisa). `PARCELAMENTO`/`FINANCIAMENTO`/
 * `EMPRESTIMO`/`CONTA_RECORRENTE`/`META` não têm rota própria ainda no
 * frontend — permanecem sem destino, documentado como deferido (mesmo
 * levantamento já feito para a Agenda).
 */
import type { LucideIcon } from "lucide-react";
import {
  ArrowLeftRight,
  Banknote,
  CreditCard,
  Home,
  Layers,
  Receipt,
  Repeat,
  Target,
  Wallet,
} from "lucide-react";
import type { TipoEntidadeReferenciavel } from "../types/enums";

export const ICONE_POR_ORIGEM: Record<TipoEntidadeReferenciavel, LucideIcon> = {
  CONTA: Wallet,
  CARTAO: CreditCard,
  FATURA: Receipt,
  TRANSACAO: ArrowLeftRight,
  PARCELAMENTO: Layers,
  FINANCIAMENTO: Home,
  EMPRESTIMO: Banknote,
  CONTA_RECORRENTE: Repeat,
  META: Target,
  TRANSFERENCIA: ArrowLeftRight,
};

export const ROTA_POR_ORIGEM: Partial<Record<TipoEntidadeReferenciavel, (id: number) => string>> = {
  CONTA: () => "/contas",
  CARTAO: (id) => `/cartoes/${id}`,
  TRANSACAO: () => "/transacoes",
  TRANSFERENCIA: () => "/transferencias",
  // Expansão de Contas Recorrentes (2026-07-20): a página /recorrentes
  // passou a existir - fecha o "deferido" documentado no cabeçalho.
  CONTA_RECORRENTE: () => "/recorrentes",
};
