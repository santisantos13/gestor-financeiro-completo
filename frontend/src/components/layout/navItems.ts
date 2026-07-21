import {
  ArrowLeftRight,
  Repeat,
  Banknote,
  CalendarDays,
  CreditCard,
  Home,
  LayoutDashboard,
  Receipt,
  Tag,
  Tags,
  Target,
  Wallet,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

/**
 * Lista unica de navegacao, compartilhada por Sidebar (md+) e
 * MobileNav (abaixo de md) - extraida daqui na etapa de Refinamento
 * de UI para os dois nunca divergirem (antes so existia dentro de
 * Sidebar.tsx, e a navegacao mobile nem existia: ver
 * docs/revisao-tecnica-refinamento-ui.md, secao sobre responsividade).
 *
 * /tags (Etapa F8) usa o icone Tags (plural), nao Tag (singular) - Tag
 * ja esta em uso pelo item /categorias (e como fallback neutro em
 * lib/icons.ts); usar o mesmo icone nos dois itens vizinhos do menu
 * criaria confusao visual sem necessidade.
 */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transacoes", label: "Transações", icon: Receipt },
  { to: "/transferencias", label: "Transferências", icon: ArrowLeftRight },
  { to: "/recorrentes", label: "Recorrentes", icon: Repeat },
  { to: "/calendario", label: "Calendário", icon: CalendarDays },
  { to: "/contas", label: "Contas", icon: Wallet },
  { to: "/cartoes", label: "Cartões", icon: CreditCard },
  { to: "/financiamentos", label: "Financiamentos", icon: Home },
  { to: "/emprestimos", label: "Empréstimos", icon: Banknote },
  { to: "/metas", label: "Metas", icon: Target },
  { to: "/categorias", label: "Categorias", icon: Tag },
  { to: "/tags", label: "Tags", icon: Tags },
];
