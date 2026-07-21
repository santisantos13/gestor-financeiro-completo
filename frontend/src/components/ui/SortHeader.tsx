import { type ReactNode } from "react";
import { ChevronUp } from "lucide-react";
import { TableCell } from "./TableCell";
import type { ColumnAlign, SortDirection } from "../../types/table";

export interface SortHeaderProps {
  children: ReactNode;
  active: boolean;
  direction: SortDirection;
  align?: ColumnAlign;
  onClick: () => void;
  className?: string;
}

/** Cabeçalho de coluna clicável — ordena ao clicar, seta rotaciona
 * conforme a direção (design-system.md, seção 18: "ícone de seta que anima
 * a rotação, `--duration-fast`"). Ciclo: nenhum → asc → desc → nenhum
 * (`hooks/useDataTable.ts`, `toggleSort`). */
export function SortHeader({
  children,
  active,
  direction,
  align = "left",
  onClick,
  className = "",
}: SortHeaderProps) {
  return (
    <TableCell header align={align} className={className}>
      <button
        type="button"
        onClick={onClick}
        className={`inline-flex items-center gap-1 whitespace-nowrap transition-colors duration-fast ease-out hover:text-text-secondary ${
          active ? "text-text-secondary" : ""
        } ${align === "right" ? "flex-row-reverse" : ""}`}
      >
        {children}
        <ChevronUp
          size={12}
          aria-hidden="true"
          className={`shrink-0 transition-all duration-fast ease-out ${active ? "opacity-100" : "opacity-30"} ${
            direction === "desc" ? "rotate-180" : ""
          }`}
        />
      </button>
    </TableCell>
  );
}
