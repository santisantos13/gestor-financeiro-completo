/**
 * Espelha backend/app/schemas/auth.py 1:1.
 */
import type { TipoPapel } from "./enums";

export interface UsuarioCreate {
  nome: string;
  email: string;
  senha: string;
}

export interface UsuarioRead {
  id: number;
  nome: string;
  email: string;
  papel: TipoPapel;
  ativo: boolean;
  criado_em: string;
}

export interface LoginRequest {
  email: string;
  senha: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expira_em_segundos: number;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface PerfilUpdate {
  nome?: string;
  email?: string;
}

export interface TrocarSenhaRequest {
  senha_atual: string;
  senha_nova: string;
}
