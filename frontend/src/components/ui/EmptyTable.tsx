import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { EmptyState } from "./EmptyState";

export interface EmptyTableProps {
  colSpan: number;
  icon?: LucideIcon;
  title?: string;
  description?: string;
  action?: ReactNode;
}

/** Linha única ocupando `colSpan` colunas, com `EmptyState` centralizado
 * dentro — usada por `DataTable` tanto para "nenhum dado ainda" quanto
 * para "busca/filtro sem resultado" (título/descrição diferentes em cada
 * caso, decidido por quem chama `DataTable`). design-system.md, seção
 * 20.1. */
export function EmptyTable({
  colSpan,
  icon = Inbox,
  title = "Nada por aqui",
  description,
  action,
}: EmptyTableProps) {
  return (
    <tr>
      <td colSpan={colSpan}>
        <EmptyState icon={icon} title={title} description={description} action={action} />
      </td>
    </tr>
  );
}
