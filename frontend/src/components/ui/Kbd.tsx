import type { ReactNode } from "react";

export interface KbdProps {
  children: ReactNode;
  className?: string;
}

/** Chip de atalho de teclado — reforça "teclado em primeiro lugar"
 * (design-system.md, seção 3). Borda inferior mais forte simula o efeito
 * de uma tecla física. */
export function Kbd({ children, className = "" }: KbdProps) {
  return (
    <kbd
      className={`inline-flex items-center justify-center rounded-xs border border-border-strong border-b-2 bg-surface-3 px-1.5 py-0.5 font-mono text-micro text-text-secondary ${className}`}
    >
      {children}
    </kbd>
  );
}
