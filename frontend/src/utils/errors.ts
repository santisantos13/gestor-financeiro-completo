import { isApiError, type ApiError } from "../types/api";

/**
 * Normaliza a dualidade de `ApiError.detail` (string vinda de um handler de
 * domínio do projeto, ou lista de `ValidationErrorItem` vinda do validador
 * padrão do FastAPI - ver docs/analise-arquitetural-frontend.md, seção 0)
 * numa única string exibível. Nenhum componente precisa saber sobre essa
 * dualidade além deste utilitário.
 */
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (typeof error.detail === "string") {
      return error.detail;
    }
    if (Array.isArray(error.detail)) {
      return error.detail.map((item) => item.msg).join(" ");
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Algo deu errado. Tente novamente.";
}

/** Usado por formulários para tentar mapear um erro 422 de validação
 * padrão do FastAPI para o campo correspondente (`loc` costuma ser
 * `["body", "nome_do_campo"]`). Devolve `null` quando o erro não é desse
 * formato (ex.: BusinessRuleError, que é uma string sem campo associado). */
export function getFieldErrors(error: unknown): Record<string, string> | null {
  if (!isApiError(error) || !Array.isArray(error.detail)) {
    return null;
  }
  const fieldErrors: Record<string, string> = {};
  for (const item of error.detail) {
    const field = item.loc[item.loc.length - 1];
    if (typeof field === "string") {
      fieldErrors[field] = item.msg;
    }
  }
  return fieldErrors;
}

export type { ApiError };
