import { createContext, useCallback, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { AlertCircle, Info } from "lucide-react";
import { DURATION, EASE, SPRING } from "../lib/motion";

export type ToastType = "success" | "error" | "info";

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

export interface ToastContextValue {
  showToast: (type: ToastType, message: string) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

const AUTO_DISMISS_MS = 5000;

const ICONS: Partial<Record<ToastType, typeof AlertCircle>> = {
  error: AlertCircle,
  info: Info,
};

const ICON_CLASSES: Record<ToastType, string> = {
  success: "text-positive",
  error: "text-negative",
  info: "text-accent",
};

/** Ícone de sucesso do toast — motion-principles.md, seção 5.7: o check é
 * desenhado via `pathLength` de 0 a 1 em `--duration-base`, uma vez,
 * `--ease-out`. Cada toast é uma montagem nova, então "uma vez" já é
 * natural (nunca reanima num toast que já existia). */
function SuccessCheckIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0 text-positive" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={2} opacity={0.35} />
      <motion.path
        d="M7 12.5l3 3 7-7"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1, transition: { duration: DURATION.base, ease: EASE.out } }}
      />
    </svg>
  );
}

/** Canal único de notificação global (rede, erro inesperado, sessão
 * expirada) — ver docs/analise-arquitetural-frontend.md, seção 8. Visual
 * formalizado em design-system.md, seção 21: `--color-surface-4` +
 * `--shadow-lg`, `--radius-lg`, ícone por tipo, entra com slide-up+fade
 * (spring `smooth`), timer de auto-dismiss pausa no hover. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
    timers.current.delete(id);
  }, []);

  const scheduleDismiss = useCallback(
    (id: number, delay: number) => {
      const timer = setTimeout(() => dismissToast(id), delay);
      timers.current.set(id, timer);
    },
    [dismissToast],
  );

  const showToast = useCallback(
    (type: ToastType, message: string) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, type, message }]);
      scheduleDismiss(id, AUTO_DISMISS_MS);
    },
    [scheduleDismiss],
  );

  function pause(id: number) {
    const timer = timers.current.get(id);
    if (timer) clearTimeout(timer);
  }

  function resume(id: number) {
    scheduleDismiss(id, AUTO_DISMISS_MS);
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[var(--z-toast)] flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => {
            const Icon = ICONS[toast.type];
            return (
              <motion.div
                key={toast.id}
                role="status"
                aria-live="polite"
                onMouseEnter={() => pause(toast.id)}
                onMouseLeave={() => resume(toast.id)}
                initial={{ opacity: 0, y: 16, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1, transition: SPRING.smooth }}
                exit={{ opacity: 0, scale: 0.98, transition: { duration: 0.15 } }}
                className="flex items-start gap-2 rounded-lg bg-surface-4 px-4 py-3 text-sm text-text-primary shadow-lg"
              >
                {toast.type === "success" || !Icon ? (
                  <SuccessCheckIcon />
                ) : (
                  <Icon size={16} className={`mt-0.5 shrink-0 ${ICON_CLASSES[toast.type]}`} aria-hidden="true" />
                )}
                <span>{toast.message}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
