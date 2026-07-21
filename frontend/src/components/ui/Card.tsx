import { type HTMLAttributes, type ReactNode } from "react";
import { motion } from "motion/react";
import { DURATION, EASE } from "../../lib/motion";

// Mesmo motivo do Button.tsx: `motion.div` já usa `transform`/`animate`
// internamente, então os handlers de gesto nativo que colidem com a
// assinatura do Framer Motion são omitidos aqui.
type NativeDivProps = Omit<
  HTMLAttributes<HTMLDivElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration"
>;

export interface CardProps extends NativeDivProps {
  children: ReactNode;
  /** Fade + 8px slide-up na MONTAGEM (motion-principles.md, seção 5.1) —
   * opt-in (default `false`) porque a maioria dos usos de `Card` não deve
   * reanimar toda vez que remonta (ex. item de lista filtrada, que
   * remonta com frequência) — motion-principles.md, seção 7, "habituação".
   * Usado por `StatCard`, cujo mount real acontece só quando o dado do
   * Dashboard chega pela primeira vez. */
  animateEntrance?: boolean;
}

/** Superfície base de todo card do dashboard — `--color-surface-2` +
 * `--radius-lg` + `--color-border-default` (design-system.md, seções 6.1,
 * 9, 11). Hover: elevação sutil (`whileHover`, 2px — mesma técnica do
 * `Button.tsx`, nunca CSS `translate` misturado com `motion`), borda
 * reagindo para `--color-border-strong` e sombra `--shadow-sm` — "leve
 * elevação + borda reagindo + profundidade" pedido na Etapa de
 * Refinamento Visual, tudo via tokens já existentes do Design System,
 * nenhum valor novo inventado. Peça genérica; quem decide o conteúdo é
 * quem usa — docs/analise-arquitetural-dashboard.md, seção 9.1. */
export function Card({ children, className = "", animateEntrance = false, ...props }: CardProps) {
  return (
    <motion.div
      {...(animateEntrance
        ? {
            initial: { opacity: 0, y: 8 },
            animate: { opacity: 1, y: 0, transition: { duration: DURATION.moderate, ease: EASE.out } },
          }
        : {})}
      whileHover={{ y: -2, transition: { duration: DURATION.fast, ease: EASE.out } }}
      className={`rounded-lg border border-border bg-surface-2 p-4 transition-[box-shadow,border-color] duration-fast ease-out hover:border-border-strong hover:shadow-sm ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  );
}
