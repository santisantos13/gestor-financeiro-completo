import { httpClient } from "../api/httpClient";
import type {
  LoginRequest,
  LogoutRequest,
  RefreshRequest,
  TokenResponse,
  UsuarioCreate,
  UsuarioRead,
} from "../types/auth";

/**
 * `auth` não é uma entidade CRUD, então o formato deste service é um pouco
 * diferente dos demais (`services/<entidade>Service.ts`) - mesmo espírito
 * (funções finas, tipadas, sem decisão nenhuma), só sem o molde
 * listar/obter/criar/atualizar/excluir.
 */
export const authService = {
  registrar: (dados: UsuarioCreate) => httpClient.post<UsuarioRead>("/auth/registrar", dados),

  login: (dados: LoginRequest) => httpClient.post<TokenResponse>("/auth/login", dados),

  refresh: (dados: RefreshRequest) => httpClient.post<TokenResponse>("/auth/refresh", dados),

  logout: (dados: LogoutRequest) => httpClient.post<void>("/auth/logout", dados),

  logoutTodas: () => httpClient.post<void>("/auth/logout-todas"),

  me: () => httpClient.get<UsuarioRead>("/auth/me"),
};
