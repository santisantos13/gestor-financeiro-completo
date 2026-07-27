/**
 * Único módulo que sabe `fetch`, URL base e headers - equivalente
 * conceitual ao `db/session.py` do backend (a "unidade de trabalho" de
 * rede). Ver docs/analise-arquitetural-frontend.md, seção 4.
 *
 * Regras:
 * - injeta `Authorization: Bearer <access_token>` lendo de `tokenStore`
 *   (nunca de Context - este módulo roda fora da árvore React, dentro de
 *   `queryFn`/`mutationFn` do React Query);
 * - normaliza toda resposta não-2xx (e falha de rede) num `ApiError` único;
 * - renova o access token automaticamente em 401 (com mutex, para não
 *   disparar múltiplas renovações concorrentes) e repete a requisição
 *   original uma vez; se o refresh também falhar, avisa `onSessionExpired`
 *   (registrado pelo `AuthContext`) e propaga o 401.
 */
import type { ApiError } from "../types/api";
import type { TokenResponse } from "../types/auth";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./tokenStore";

const BASE_URL = import.meta.env.VITE_API_URL;

type QueryParams = Record<string, string | number | boolean | undefined | null>;

interface RequestOptions {
  params?: QueryParams;
  body?: unknown;
}

let onSessionExpired: (() => void) | null = null;

/** Registrado uma vez pelo `AuthProvider` no mount. */
export function setOnSessionExpired(callback: () => void): void {
  onSessionExpired = callback;
}

function buildUrl(path: string, params?: QueryParams): string {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function parseErrorDetail(response: Response): Promise<ApiError["detail"]> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      return (body as { detail: ApiError["detail"] }).detail;
    }
    return response.statusText || "Erro desconhecido.";
  } catch {
    return response.statusText || "Erro desconhecido.";
  }
}

/** Chamada de baixo nível ao /auth/refresh, fora do fluxo genérico de
 * `request()` de propósito - evita qualquer risco de recursão com a
 * lógica de retry em 401 implementada logo abaixo. */
async function rawRefresh(refreshToken: string): Promise<TokenResponse | null> {
  let response: Response;
  try {
    response = await fetch(buildUrl("/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return null;
  }
  if (!response.ok) return null;
  return (await response.json()) as TokenResponse;
}

let refreshPromise: Promise<boolean> | null = null;

/** No máximo uma renovação em andamento por vez - chamadas concorrentes
 * que levam 401 ao mesmo tempo aguardam a mesma Promise em vez de
 * disparar várias renovações (mutex simples baseado em Promise
 * compartilhada). */
async function ensureFreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  refreshPromise = (async () => {
    const tokens = await rawRefresh(refreshToken);
    if (!tokens) {
      clearTokens();
      return false;
    }
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token); // rotation: token antigo já foi invalidado pelo backend
    return true;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

/** Núcleo comum de `request`/`baixarArquivo` - faz o fetch de verdade,
 * injeta o header de autenticação, tenta renovar a sessão uma vez em 401 e
 * normaliza qualquer resposta não-2xx num `ApiError`. Devolve a `Response`
 * crua (não decide se o corpo é JSON ou binário) - só `request` (JSON) e
 * `requestArquivo` (blob, ver `baixarArquivo`) sabem disso, evitando
 * duplicar a lógica de renovação/erro entre os dois. */
async function fetchComRenovacao(
  method: string,
  path: string,
  options: RequestOptions,
  isRetry = false,
): Promise<Response> {
  const accessToken = getAccessToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.params), {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    const networkError: ApiError = { status: 0, detail: "Falha de conexão com o servidor." };
    throw networkError;
  }

  // só tenta renovar sessão para requisições que de fato mandaram um
  // access token - login/registrar/refresh nunca mandam, então um 401
  // deles nunca aciona esse fluxo (evita renovar a sessão de outro
  // usuário por engano ao tentar logar com credencial errada).
  if (response.status === 401 && accessToken && !isRetry) {
    const renewed = await ensureFreshToken();
    if (renewed) {
      return fetchComRenovacao(method, path, options, true);
    }
    onSessionExpired?.();
    const detail = await parseErrorDetail(response);
    const sessionError: ApiError = { status: 401, detail };
    throw sessionError;
  }

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    const apiError: ApiError = { status: response.status, detail };
    throw apiError;
  }

  return response;
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetchComRenovacao(method, path, options);
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** `Content-Disposition: attachment; filename="x.csv"` (com ou sem aspas)
 * - `nomePadrao` cobre o caso (nunca esperado de verdade, mas defensivo)
 * de o backend omitir o header. */
function extrairNomeArquivo(response: Response, nomePadrao: string): string {
  const cabecalho = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/.exec(cabecalho);
  return match?.[1]?.trim() ?? nomePadrao;
}

async function requestArquivo(
  method: string,
  path: string,
  options: RequestOptions,
  nomePadrao: string,
): Promise<{ blob: Blob; nomeArquivo: string }> {
  const response = await fetchComRenovacao(method, path, options);
  const blob = await response.blob();
  return { blob, nomeArquivo: extrairNomeArquivo(response, nomePadrao) };
}

export const httpClient = {
  get: <T>(path: string, params?: QueryParams) => request<T>("GET", path, { params }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string, params?: QueryParams) => request<T>("DELETE", path, { params }),
  /** Download de arquivo (Relatórios: CSV/PDF) - único ponto do frontend
   * que lida com corpo BINÁRIO em vez de JSON. Reaproveita a mesma
   * renovação de sessão/normalização de erro de `request`, só troca o
   * parse final (`blob()` em vez de `json()`). Ver
   * `utils/download.ts:baixarBlob` para o que acontece depois (disparar o
   * download no navegador). */
  baixarArquivo: (path: string, params: QueryParams | undefined, nomePadrao: string) =>
    requestArquivo("GET", path, { params }, nomePadrao),
};
