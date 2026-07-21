/**
 * Ponte não-React entre `AuthContext` e `httpClient`. `httpClient` roda
 * dentro de `queryFn`/`mutationFn` do React Query - fora da árvore de
 * componentes - então não pode `useContext`. `AuthContext` é o ÚNICO
 * escritor deste módulo (ver docs/analise-arquitetural-frontend.md, seção
 * 7); tudo mais só lê.
 *
 * Só o access token vive aqui (memória, perdido ao recarregar a página de
 * propósito). O refresh token vive em `localStorage` - ver
 * `REFRESH_TOKEN_STORAGE_KEY` abaixo, único ponto que sabe essa chave.
 */

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export const REFRESH_TOKEN_STORAGE_KEY = "financas:refresh_token";

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  }
}

/** Limpa os dois tokens - usado no logout e quando uma sessão expira. */
export function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}
