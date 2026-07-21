/**
 * Tipos genéricos do transporte HTTP - nada aqui é específico de uma
 * entidade do backend. Ver docs/analise-arquitetural-frontend.md, seção 4.
 */

/** Formato de um item de erro de validação do handler PADRÃO do FastAPI
 * (RequestValidationError) - schema Pydantic malformado. Ver seção 0/8
 * do doc de arquitetura: é uma forma DIFERENTE de `detail` da que os
 * handlers de domínio do projeto (BusinessRuleError etc.) devolvem. */
export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/**
 * Erro normalizado por `api/httpClient.ts` para toda resposta não-2xx (ou
 * falha de rede, com status 0). `detail` é `string` quando o erro vem de um
 * handler de domínio do projeto (`app/main.py`: NotFoundError,
 * BusinessRuleError, ConflictError, NaoAutenticadoError, AcessoNegadoError)
 * e `ValidationErrorItem[]` quando vem do validador padrão do FastAPI -
 * mesmo status 422 pode ser qualquer um dos dois. Use
 * `utils/errors.ts#getErrorMessage` para não tratar essa dualidade em cada
 * componente.
 */
export interface ApiError {
  status: number;
  detail: string | ValidationErrorItem[];
}

export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    "detail" in error &&
    typeof (error as ApiError).status === "number"
  );
}
