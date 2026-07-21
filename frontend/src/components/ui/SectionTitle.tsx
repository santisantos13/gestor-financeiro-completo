import { type ReactNode } from "react";

export interface SectionTitleProps {
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}

/** `--text-h2` + espaçamento padrão acima de cada bloco do Bento Grid —
 * design-system.md, seção 7.1. `action` opcional alinhado à direita (ex.
 * `PeriodoSeletor` ao lado do título de Resumo Financeiro). */
export function SectionTitle({ children, action, className = "" }: SectionTitleProps) {
  return (
    <div className={`mb-3 flex items-center justify-between ${className}`}>
      <h2 className="text-h2 font-semibold text-text-primary">{children}</h2>
      {action}
    </div>
  );
}
