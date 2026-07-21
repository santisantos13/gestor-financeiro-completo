import { AlertCircle } from "lucide-react";
import { getErrorMessage } from "../../utils/errors";

export interface ErrorMessageProps {
  error: unknown;
  className?: string;
}

/** Exibe qualquer erro (ApiError ou Error nativo) de forma consistente -
 * ver docs/analise-arquitetural-frontend.md, seção 8/9. Visual formalizado
 * na Etapa F2 (design-system.md, seção 6.4 — cor negativa é significado
 * fixo, nunca decorativa). */
export function ErrorMessage({ error, className = "" }: ErrorMessageProps) {
  return (
    <p role="alert" className={`flex items-start gap-1.5 text-sm text-negative ${className}`}>
      <AlertCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
      <span>{getErrorMessage(error)}</span>
    </p>
  );
}
