import { cloneElement, isValidElement, useRef, useState, type ReactElement, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { DURATION, EASE } from "../../lib/motion";

export interface TooltipProps {
  content: ReactNode;
  children: ReactElement;
  side?: "top" | "bottom";
  /** Delay antes de aparecer — evita "piscar" ao passar o mouse rápido.
   * design-system.md, seção 14. */
  delayMs?: number;
}

const SIDE_CLASSES: Record<NonNullable<TooltipProps["side"]>, string> = {
  top: "bottom-full left-1/2 mb-2 -translate-x-1/2",
  bottom: "top-full left-1/2 mt-2 -translate-x-1/2",
};

/** `--color-surface-4`, `--text-caption` — design-system.md, seção 14. */
export function Tooltip({ content, children, side = "top", delayMs = 400 }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  function show() {
    timerRef.current = setTimeout(() => setOpen(true), delayMs);
  }

  function hide() {
    clearTimeout(timerRef.current);
    setOpen(false);
  }

  if (!isValidElement(children)) return children;

  const trigger = cloneElement(children as ReactElement<Record<string, unknown>>, {
    onMouseEnter: show,
    onMouseLeave: hide,
    onFocus: show,
    onBlur: hide,
  });

  return (
    <span className="relative inline-flex">
      {trigger}
      <AnimatePresence>
        {open && (
          <motion.span
            role="tooltip"
            initial={{ opacity: 0, y: side === "top" ? 4 : -4 }}
            animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
            exit={{ opacity: 0, transition: { duration: DURATION.fast, ease: EASE.in } }}
            className={`pointer-events-none absolute z-[var(--z-tier1)] whitespace-nowrap rounded-sm bg-surface-4 px-2 py-1 text-caption text-text-primary shadow-sm ${SIDE_CLASSES[side]}`}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
