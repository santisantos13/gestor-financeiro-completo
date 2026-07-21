import { type ReactNode, type TdHTMLAttributes } from "react";
import type { ColumnAlign } from "../../types/table";

export interface TableCellProps extends TdHTMLAttributes<HTMLTableCellElement | HTMLTableHeaderCellElement> {
  children?: ReactNode;
  align?: ColumnAlign;
  /** Renderiza `<th>` em vez de `<td>` — usado pelo cabeçalho da tabela. */
  header?: boolean;
}

const ALIGN_CLASSES: Record<ColumnAlign, string> = {
  left: "text-left",
  right: "text-right",
  center: "text-center",
};

/** Célula de dado ou cabeçalho. Colunas alinhadas à direita ganham
 * `.tabular` (Geist Mono, tabular-nums) automaticamente — na prática toda
 * coluna `align="right"` deste projeto é numérica/monetária
 * (design-system.md, seção 18). */
export function TableCell({ children, align = "left", header = false, className = "", ...props }: TableCellProps) {
  const classes = `px-4 py-3 ${ALIGN_CLASSES[align]} ${align === "right" ? "tabular" : ""} ${
    header ? "text-caption font-medium uppercase tracking-wide text-text-tertiary" : "text-sm text-text-primary"
  } ${className}`;

  if (header) {
    return (
      <th className={classes} {...props}>
        {children}
      </th>
    );
  }

  return (
    <td className={classes} {...props}>
      {children}
    </td>
  );
}
