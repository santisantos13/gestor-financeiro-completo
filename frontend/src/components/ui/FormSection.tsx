import type { ReactNode } from "react";

export interface FormSectionProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

/** Agrupa campos relacionados dentro de um formulário longo — subtítulo
 * `--text-h3` (design-system.md, seção 7.1: "subtítulo, cabeçalho de grupo
 * em formulário"), coluna única sempre (seção 17). Puramente estrutural,
 * não sabe nada de RHF. */
export function FormSection({ title, description, children, className = "" }: FormSectionProps) {
  return (
    <fieldset className={`space-y-4 ${className}`}>
      {(title || description) && (
        <div className="space-y-1">
          {title && <legend className="text-h3 font-semibold text-text-primary">{title}</legend>}
          {description && <p className="text-sm text-text-secondary">{description}</p>}
        </div>
      )}
      <div className="space-y-4">{children}</div>
    </fieldset>
  );
}
