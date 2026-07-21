import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { drawerBackdrop, drawerPanel } from "../../lib/motion";

export interface DrawerProps {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Overlay tier 2 ancorado à borda direita da tela —
 * `docs/analise-arquitetural-overlays.md`, seção 4.5. Mesma superfície de
 * `FormDialog` (`--color-surface-4`/`--shadow-xl`/`--blur-lg`), só a
 * geometria muda (retângulo vertical na borda em vez de caixa
 * centralizada). Primeiro consumidor real: detalhes/ações de uma fatura
 * individual (`docs/analise-arquitetural-fatura-frontend.md`).
 *
 * Fecha com `Esc`, clique no backdrop ou botão "×" — foco preso dentro
 * enquanto aberto, retorna ao elemento que abriu ao fechar, scroll do body
 * bloqueado. Mesmas regras de `FormDialog` (design-system.md, seção 22),
 * estendidas aqui — nunca dois overlays tier 2 abertos ao mesmo tempo.
 */
export function Drawer({ open, title, description, onClose, children, footer, className = "" }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) return;

    const previamenteFocado = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const focaveis = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    focaveis?.[0]?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;

      const nodes = panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeyDown);
      previamenteFocado?.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          {...drawerBackdrop}
          className="fixed inset-0 z-[var(--z-tier2)] bg-bg/60 backdrop-blur-lg"
          onClick={onClose}
        >
          <motion.div
            {...drawerPanel}
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={description ? descriptionId : undefined}
            onClick={(event) => event.stopPropagation()}
            className={`fixed inset-y-0 right-0 flex w-full max-w-[30rem] flex-col border-l border-border bg-surface-4 shadow-xl ${className}`}
          >
            <div className="flex items-start justify-between gap-4 border-b border-border-subtle p-5 pb-4">
              <div className="min-w-0">
                <h2 id={titleId} className="text-h3 font-semibold text-text-primary">
                  {title}
                </h2>
                {description && (
                  <p id={descriptionId} className="mt-1 text-sm text-text-secondary">
                    {description}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Fechar"
                className="shrink-0 rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-3 hover:text-text-primary"
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-5">{children}</div>

            {footer && <div className="border-t border-border-subtle p-5 pt-4">{footer}</div>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
