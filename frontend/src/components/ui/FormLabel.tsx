import type { LabelHTMLAttributes } from "react";

export interface FormLabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  /** Marca a MINORIA opcional de campos — design-system.md, seção 17: a
   * maioria dos campos deste sistema é obrigatória, então em vez de `*` em
   * cada campo obrigatório, só o opcional ganha um sufixo discreto. */
  optional?: boolean;
}

/** `--text-sm`, `--color-text-secondary` — design-system.md, seção 15
 * (`FormField`). Usado internamente por `FormField`, exportado também para
 * composições customizadas (ex. `<legend>` de um `RadioGroupField`). */
export function FormLabel({ optional = false, className = "", children, ...props }: FormLabelProps) {
  return (
    <label className={`block text-sm font-medium text-text-secondary ${className}`} {...props}>
      {children}
      {optional && <span className="ml-1 font-normal text-text-tertiary">(opcional)</span>}
    </label>
  );
}
