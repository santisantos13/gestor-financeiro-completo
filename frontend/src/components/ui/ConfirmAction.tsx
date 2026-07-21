import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle } from "lucide-react";
import { modalBackdrop, modalPanel } from "../../lib/motion";
import { Button } from "./Button";

export interface ConfirmActionProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Modal de confirmação genérico — visual de `DeleteDialog`
 * (design-system.md, seção 15): centralizado, `--color-surface-4`,
 * `--radius-xl`, `--shadow-xl`, backdrop `--blur-lg` sobre fundo escuro
 * translúcido. Foco inicial no botão Cancelar (nunca no destrutivo —
 * previne exclusão acidental por `Enter`), `Esc`/clique fora fecha, scroll
 * do body bloqueado enquanto aberto, foco retorna ao elemento anterior ao
 * fechar. Infraestrutura genérica usada por `BulkActions`/`RowActions`
 * desta etapa; renderizado via portal (`createPortal`) para nunca ser
 * cortado pelo `overflow-x-auto` de `Table`. */
export function ConfirmAction({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  tone = "default",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmActionProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const previamenteFocado = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeyDown);
      previamenteFocado?.focus();
    };
  }, [open, onCancel]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          {...modalBackdrop}
          className="fixed inset-0 z-[var(--z-tier2)] flex items-center justify-center bg-bg/60 p-4 backdrop-blur-lg"
          onClick={onCancel}
        >
          <motion.div
            {...modalPanel}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-action-title"
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-sm rounded-xl border border-border bg-surface-4 p-5 shadow-xl"
          >
            <div className="flex items-start gap-3">
              {tone === "danger" && (
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-negative-subtle">
                  <AlertTriangle size={16} className="text-negative" aria-hidden="true" />
                </span>
              )}
              <div className="min-w-0">
                <h2 id="confirm-action-title" className="text-h3 font-semibold text-text-primary">
                  {title}
                </h2>
                {description && <p className="mt-1 text-sm text-text-secondary">{description}</p>}
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button ref={cancelRef} variant="secondary" size="sm" onClick={onCancel}>
                {cancelLabel}
              </Button>
              <Button
                variant={tone === "danger" ? "danger" : "primary"}
                size="sm"
                loading={loading}
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
