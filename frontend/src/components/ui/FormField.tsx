import type { ReactNode } from "react";
import { FormLabel } from "./FormLabel";
import { FormDescription } from "./FormDescription";
import { FormError } from "./FormError";

export interface FormFieldProps {
  id: string;
  label: string;
  optional?: boolean;
  description?: string;
  error?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Chrome de campo (label + slot de input + descrição/erro) — todo `*Field`
 * genérico da Etapa F5 compõe isto por dentro, em vez de reimplementar
 * label/mensagem de erro do zero (docs/analise-arquitetural-frontend.md,
 * seção 12). Decisão desta etapa: em vez de `FormField` injetar `id`/`aria-*`
 * via `cloneElement` num `children` arbitrário (frágil quando o input é um
 * composto como `Select`/`DateInput`, que nem sempre repassa props extras
 * para o nó DOM certo), cada `*Field` já monta seu próprio input com
 * `id`/`name`/`aria-invalid` corretos e só usa `FormField` para o chrome
 * ao redor — mais verboso por campo, muito mais robusto no conjunto.
 */
export function FormField({ id, label, optional, description, error, children, className = "" }: FormFieldProps) {
  const errorId = `${id}-error`;
  const descriptionId = `${id}-description`;

  return (
    <div className={`space-y-1.5 ${className}`}>
      <FormLabel htmlFor={id} optional={optional}>
        {label}
      </FormLabel>
      {children}
      {description && !error && <FormDescription id={descriptionId}>{description}</FormDescription>}
      <FormError id={errorId} message={error} />
    </div>
  );
}
