import { AnimatePresence, motion } from "motion/react";
import { AlertCircle } from "lucide-react";
import { DURATION } from "../../lib/motion";

export interface FormErrorProps {
  message?: string;
  id?: string;
}

/** `ValidationMessage` de `docs/design-system.md` (seção 15): `--text-sm`,
 * `--color-negative`, ícone `AlertCircle` 14px, entra com fade+slide-down
 * de 4px em `--duration-fast` — **sem shake**, decisão explícita de
 * `docs/motion-principles.md` (seção 5.6: tremor é redundante com
 * cor+ícone+texto e desconfortável para quem é sensível a movimento). A
 * borda do campo em si já muda para negativa instantaneamente (sem
 * transição) por conta própria — só a mensagem anima. */
export function FormError({ message, id }: FormErrorProps) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      {message && (
        <motion.p
          id={id}
          role="alert"
          key={message}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: DURATION.fast }}
          className="flex items-start gap-1.5 text-sm text-negative"
        >
          <AlertCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{message}</span>
        </motion.p>
      )}
    </AnimatePresence>
  );
}
