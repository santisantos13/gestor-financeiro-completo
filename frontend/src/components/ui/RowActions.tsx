import { Tooltip } from "./Tooltip";
import { Button } from "./Button";
import type { RowAction } from "../../types/table";

export interface RowActionsProps<T> {
  row: T;
  actions: RowAction<T>[];
  className?: string;
  /** `sm` (28px) no desktop — linha inteira já é uma área de hover grande,
   * o botão só precisa acomodar o cursor. No card mobile (`DataTable`
   * passa `md` aqui) as ações ficam sempre visíveis e são o único alvo de
   * toque disponível, por isso ganham um alvo mínimo mais confortável
   * (36px) — mesma lógica de qualquer diretriz de toque (~40-44px ideal;
   * `md` já é uma melhoria real sobre os 28px anteriores sem inflar o
   * ícone nem quebrar a densidade do design system). */
  size?: "sm" | "md";
}

/** Ícones `ghost` que só aparecem no hover da linha (`group-hover`,
 * `TableRow`) — design-system.md, seção 18. Também visível em
 * `group-focus-within` (navegação por teclado não pode depender de
 * hover de mouse). */
export function RowActions<T>({ row, actions, className = "", size = "sm" }: RowActionsProps<T>) {
  const visiveis = actions.filter((action) => !action.hidden?.(row));
  if (visiveis.length === 0) return null;

  return (
    <div
      className={`flex items-center justify-end gap-1 opacity-0 transition-opacity duration-fast ease-out group-hover:opacity-100 group-focus-within:opacity-100 ${className}`}
    >
      {visiveis.map((action) => (
        <Tooltip key={action.label} content={action.label}>
          <Button
            variant="ghost"
            size={size}
            onClick={(event) => {
              event.stopPropagation();
              action.onClick(row);
            }}
            aria-label={action.label}
            className={action.tone === "danger" ? "hover:text-negative" : ""}
          >
            <action.icon size={14} aria-hidden="true" />
          </Button>
        </Tooltip>
      ))}
    </div>
  );
}
