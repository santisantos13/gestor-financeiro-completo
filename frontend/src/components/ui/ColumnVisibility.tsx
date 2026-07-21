import { createPortal } from "react-dom";
import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Columns3 } from "lucide-react";
import { DURATION, EASE } from "../../lib/motion";
import { useFloatingPanel } from "../../hooks/useFloatingPanel";
import { Checkbox } from "./Checkbox";
import { Button } from "./Button";
import type { ColumnDef } from "../../types/table";

export interface ColumnVisibilityProps<T> {
  columns: ColumnDef<T>[];
  hiddenColumnKeys: Set<string>;
  onToggle: (columnKey: string) => void;
  className?: string;
}

const PANEL_WIDTH = 208;

/** Popover com um `Checkbox` por coluna. Painel portado para
 * `document.body` com `position: fixed` (`useFloatingPanel`) desde o
 * Refinamento de Pickers/Performance — antes duplicava seu próprio
 * `useEffect` de clique-fora/`Esc` (nem reaproveitava
 * `useDismissableOverlay`, que já existia); agora usa a mesma
 * infraestrutura compartilhada de `RichPicker`/`SearchSelect`/
 * `MultiSelectField`/`Select`. */
export function ColumnVisibility<T>({
  columns,
  hiddenColumnKeys,
  onToggle,
  className = "",
}: ColumnVisibilityProps<T>) {
  const [open, setOpen] = useState(false);

  function close() {
    setOpen(false);
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLDivElement>(open, close, {
    panelWidth: () => PANEL_WIDTH,
    align: "end",
  });

  return (
    <div ref={anchorRef} className={`relative ${className}`}>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Columns3 size={14} aria-hidden="true" />
        Colunas
      </Button>
      {createPortal(
        <AnimatePresence>
          {open && rect && (
            <motion.div
              ref={panelRef}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
              exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
              style={{ position: "fixed", top: rect.top, left: rect.left, width: rect.width }}
              className="z-[var(--z-tier1)] rounded-md border border-border bg-surface-3 p-2 shadow-md"
            >
              {columns.map((column) => (
                <label
                  key={column.key}
                  className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-text-primary hover:bg-surface-4"
                >
                  <Checkbox checked={!hiddenColumnKeys.has(column.key)} onChange={() => onToggle(column.key)} />
                  {column.header}
                </label>
              ))}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
