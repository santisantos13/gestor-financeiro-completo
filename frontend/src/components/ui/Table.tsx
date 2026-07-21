import { type ReactNode, type TableHTMLAttributes } from "react";

export interface TableProps extends TableHTMLAttributes<HTMLTableElement> {
  children: ReactNode;
}

/** Elemento `<table>` semântico — sem zebra striping, divisórias
 * `--color-border-subtle` entre linhas (design-system.md, seção 18).
 * Envolvido por scroll horizontal de segurança. Composição completa
 * (busca/filtro/paginação/seleção/responsividade) mora em `DataTable`. */
export function Table({ children, className = "", ...props }: TableProps) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={`w-full border-collapse text-left text-sm ${className}`} {...props}>
        {children}
      </table>
    </div>
  );
}
