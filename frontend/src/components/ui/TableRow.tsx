import { type HTMLAttributes, type ReactNode } from "react";

export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  children: ReactNode;
  selected?: boolean;
}

/** `group` habilita `RowActions` a aparecer só no hover da linha
 * (design-system.md, seção 18: "ações de linha aparecem só no hover").
 * Altura ~44px vem do padding de `TableCell`, não fixada aqui.
 *
 * Destaque de hover/seleção (Etapa de Refinamento Visual): além do fundo
 * `--color-surface-2` já existente, uma barra de acento de 3px aparece na
 * borda esquerda via `box-shadow: inset` (não `border-left`, que seria
 * afetado por `border-collapse: collapse` da `Table`; `box-shadow` não é
 * — renderiza de forma confiável em `<tr>` nos navegadores atuais). Linha
 * selecionada mantém a mesma barra permanentemente, reforçando visualmente
 * que hover e seleção usam a mesma linguagem de "isto está em destaque" —
 * evita o visual "linha cinza de admin", pedido explícito desta etapa. */
export function TableRow({ children, selected = false, className = "", ...props }: TableRowProps) {
  return (
    <tr
      className={`group relative border-b border-border-subtle transition-[background-color,box-shadow] duration-fast ease-out last:border-0 hover:bg-surface-2 hover:shadow-[inset_3px_0_0_0_var(--color-accent)] ${
        selected ? "bg-accent-subtle shadow-[inset_3px_0_0_0_var(--color-accent)]" : ""
      } ${className}`}
      {...props}
    >
      {children}
    </tr>
  );
}
