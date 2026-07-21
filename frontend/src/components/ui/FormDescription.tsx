import type { ReactNode } from "react";

export interface FormDescriptionProps {
  children: ReactNode;
  id?: string;
  className?: string;
}

/** Texto de apoio abaixo do label, acima do input — `--text-sm`,
 * secundário. Só aparece quando o campo não está com erro (o erro
 * substitui a descrição no mesmo espaço, `FormField` decide isso). */
export function FormDescription({ children, id, className = "" }: FormDescriptionProps) {
  return (
    <p id={id} className={`text-sm text-text-tertiary ${className}`}>
      {children}
    </p>
  );
}
