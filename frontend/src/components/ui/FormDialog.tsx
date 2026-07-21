import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { modalBackdrop, modalPanel } from "../../lib/motion";
import { Button } from "./Button";

export interface FormDialogProps {
  open: boolean;
  title: string;
  description?: string;
  /** Formulário tem alteração não salva — tipicamente `form.formState.isDirty`
   * do RHF. `FormDialog` não sabe nada de RHF por si (decoupled de
   * propósito), só recebe esse booleano de quem monta o formulário. */
  isDirty?: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Função em vez de nó pronto: o rodapé (tipicamente `FormActions` com
   * `CancelButton`/`SubmitButton`) recebe `requestClose` para que o botão
   * "Cancelar" passe pelo MESMO fluxo de confirmação de `Esc`/backdrop —
   * nunca um caminho de fechar que pula a checagem de alteração não
   * salva. */
  footer?: (requestClose: () => void) => ReactNode;
  className?: string;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal padrão de criar/editar — `docs/design-system.md`, seção 15/22.
 * `--color-surface-4`, `--radius-xl`, `--shadow-xl`, backdrop `--blur-lg`.
 * Abertura/fechamento usam exatamente `modalBackdrop`/`modalPanel` de
 * `lib/motion.ts` (scale 0.96→1 + fade, spring `smooth` na entrada; fade +
 * scale sutil, `--ease-in`, na saída — já o mesmo par usado por
 * `ConfirmAction` na Etapa F4, nenhum timing novo inventado aqui).
 *
 * Fecha com `Esc`, clique no backdrop ou botão "×" — mas nunca perde dado
 * digitado por engano: se `isDirty`, o pedido de fechar troca o CONTEÚDO
 * do modal por uma confirmação ("Descartar alterações?"), em vez de abrir
 * um segundo modal por cima (design-system.md, seção 22: "nunca modal
 * sobre modal — um FormDialog que precisar de confirmação extra usa
 * DeleteDialog substituindo o conteúdo, não empilhando"). Foco preso
 * dentro do modal enquanto aberto, retorna ao elemento que abriu ao
 * fechar, scroll do body bloqueado.
 */
export function FormDialog({
  open,
  title,
  description,
  isDirty = false,
  onClose,
  children,
  footer,
  className = "",
}: FormDialogProps) {
  const [confirmandoFechar, setConfirmandoFechar] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  function requestClose() {
    if (isDirty) {
      setConfirmandoFechar(true);
      return;
    }
    onClose();
  }

  function discardAndClose() {
    setConfirmandoFechar(false);
    onClose();
  }

  useEffect(() => {
    if (!open) {
      setConfirmandoFechar(false);
      return;
    }

    const previamenteFocado = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const focaveis = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    focaveis?.[0]?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        requestClose();
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
          {...modalBackdrop}
          className="fixed inset-0 z-[var(--z-tier2)] flex items-center justify-center bg-bg/60 p-4 backdrop-blur-lg"
          onClick={requestClose}
        >
          <motion.div
            {...modalPanel}
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={description ? descriptionId : undefined}
            onClick={(event) => event.stopPropagation()}
            className={`flex max-h-[85vh] w-full max-w-lg flex-col rounded-xl border border-border bg-surface-4 shadow-xl ${className}`}
          >
            {confirmandoFechar ? (
              <div className="p-5">
                <h2 className="text-h3 font-semibold text-text-primary">Descartar alterações?</h2>
                <p className="mt-1 text-sm text-text-secondary">
                  Você tem alterações não salvas neste formulário. Se sair agora, elas serão perdidas.
                </p>
                <div className="mt-5 flex justify-end gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setConfirmandoFechar(false)}>
                    Continuar editando
                  </Button>
                  <Button variant="danger" size="sm" onClick={discardAndClose}>
                    Descartar alterações
                  </Button>
                </div>
              </div>
            ) : (
              <>
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
                    onClick={requestClose}
                    aria-label="Fechar"
                    className="shrink-0 rounded-sm p-1 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-3 hover:text-text-primary"
                  >
                    <X size={18} aria-hidden="true" />
                  </button>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-5">{children}</div>

                {footer && <div className="border-t border-border-subtle p-5 pt-4">{footer(requestClose)}</div>}
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
