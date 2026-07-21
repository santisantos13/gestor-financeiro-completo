/**
 * Tipos genéricos do sistema de tabelas (Etapa F4) — nenhum aqui conhece
 * uma entidade específica do backend (Conta, Transação etc.); quem
 * preenche `ColumnDef<T>`/`FilterDef<T>`/`RowAction<T>`/`BulkAction<T>` é
 * sempre quem usa `DataTable`, numa etapa futura de CRUD. Ver
 * docs/analise-arquitetural-frontend.md, seção 13 (paginação/ordenação/
 * filtro client-side, decisão já aprovada).
 */
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type SortDirection = "asc" | "desc" | null;

export interface SortState {
  columnKey: string | null;
  direction: SortDirection;
}

export type ColumnAlign = "left" | "right" | "center";

export interface ColumnDef<T> {
  /** Identificador único da coluna — usado por ordenação, visibilidade e `key` do React. */
  key: string;
  header: string;
  /** Extrai o valor bruto da linha — usado por busca e ordenação (nunca só pela exibição). */
  accessor: (row: T) => string | number | boolean | null | undefined;
  /** Como renderizar a célula. Se omitido, usa `String(accessor(row))`. */
  render?: (row: T) => ReactNode;
  sortable?: boolean;
  align?: ColumnAlign;
  /** Classe Tailwind de largura opcional (ex. `"w-32"`). */
  width?: string;
  /** Esconde a coluna abaixo de `md` — design-system.md, seção 24 (linha vira card). */
  hideOnMobile?: boolean;
}

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterDef<T> {
  key: string;
  label: string;
  options: FilterOption[];
  /** Testa se a linha passa no filtro para o valor selecionado. */
  predicate: (row: T, value: string) => boolean;
}

export interface RowAction<T> {
  label: string;
  icon: LucideIcon;
  onClick: (row: T) => void;
  tone?: "default" | "danger";
  /** Esconde a ação para linhas específicas (ex. já paga, não cancelável). */
  hidden?: (row: T) => boolean;
}

export interface BulkAction<T> {
  label: string;
  icon?: LucideIcon;
  onClick: (selectedRows: T[]) => void;
  tone?: "default" | "danger";
  /** Exige confirmação (`ConfirmAction`) antes de executar — default `true` quando `tone: "danger"`. */
  requireConfirmation?: boolean;
  confirmTitle?: string;
  confirmDescription?: string;
}
