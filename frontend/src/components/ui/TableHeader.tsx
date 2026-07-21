import { type ReactNode } from "react";

export interface TableHeaderProps {
  children: ReactNode;
  className?: string;
}

/** `<thead>` sticky — design-system.md, seção 18 ("cabeçalho sticky ao
 * rolar tabelas longas"). Funciona dentro do container com `overflow-y`
 * que `DataTable` fornece. */
export function TableHeader({ children, className = "" }: TableHeaderProps) {
  return <thead className={`sticky top-0 z-10 bg-surface-1 ${className}`}>{children}</thead>;
}
