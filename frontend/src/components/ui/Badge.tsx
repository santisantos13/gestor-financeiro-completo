import { type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { DURATION, EASE } from "../../lib/motion";

export type BadgeTone = "positive" | "negative" | "warning" | "info" | "neutral" | "accent";

export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
  /** Quando true, a troca de conteúdo faz crossfade (mudança de status
   * vista em tempo real pelo usuário) em vez de trocar abruptamente —
   * motion-principles.md, seção 6.3. Desligado por padrão porque a maioria
   * dos usos é uma renderização única (lista carregada do servidor). */
  animateChange?: boolean;
}

const TONE_CLASSES: Record<BadgeTone, string> = {
  positive: "bg-positive-subtle text-positive",
  negative: "bg-negative-subtle text-negative",
  warning: "bg-warning-subtle text-warning",
  // `info` — sistema semântico de status (revisão de UX de Cartões):
  // estado informativo/em-andamento, nem sucesso nem alerta (design-system.md, seção 6.4).
  info: "bg-info-subtle text-info",
  neutral: "bg-surface-3 text-text-secondary",
  accent: "bg-accent-subtle text-accent",
};

/** Componente visual por trás de StatusFatura/StatusTransacao/
 * StatusContratoCredito — design-system.md, seção 14. Cor é sempre
 * significado fixo (seção 6.4), nunca decorativa. */
export function Badge({ tone = "neutral", children, className = "", animateChange = false }: BadgeProps) {
  const classes = `inline-flex items-center rounded-full px-2 py-0.5 text-micro font-medium leading-none ${TONE_CLASSES[tone]} ${className}`;

  if (!animateChange) {
    return <span className={classes}>{children}</span>;
  }

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={`${tone}-${children}`}
        className={classes}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: DURATION.moderate, ease: EASE.inOut }}
      >
        {children}
      </motion.span>
    </AnimatePresence>
  );
}
