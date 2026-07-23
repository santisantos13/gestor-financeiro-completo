import {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { setOnSessionExpired } from "../api/httpClient";
import {
  clearTokens,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../api/tokenStore";
import { authService } from "../services/authService";
import type { LoginRequest, PerfilUpdate, TrocarSenhaRequest, UsuarioCreate, UsuarioRead } from "../types/auth";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthStatus;
  usuario: UsuarioRead | null;
  login: (dados: LoginRequest) => Promise<void>;
  /** Registra e, em seguida, encadeia um login com as mesmas credenciais -
   * `POST /auth/registrar` não devolve token (ver types/auth.ts), então
   * sem isso o usuário precisaria digitar a senha duas vezes. Decisão de
   * UX registrada em docs/analise-arquitetural-frontend.md, seção 14. */
  registrar: (dados: UsuarioCreate) => Promise<void>;
  logout: () => Promise<void>;
  logoutTodas: () => Promise<void>;
  /** Configurações → Perfil. Atualiza o cache de `auth.me` diretamente com
   * a resposta do PATCH (em vez de só invalidar) - o Header/UserMenu
   * refletem nome/email novos no mesmo instante, sem esperar um refetch. */
  atualizarPerfil: (dados: PerfilUpdate) => Promise<UsuarioRead>;
  trocarSenha: (dados: TrocarSenhaRequest) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  // true assim que o passo de boot (seção abaixo) terminar, com ou sem
  // sucesso - antes disso `status` é sempre "loading", pra nunca piscar a
  // tela de login antes de saber se a sessão salva ainda é válida.
  const [hasBootstrapped, setHasBootstrapped] = useState(false);
  // espelho em estado React de "existe um access token válido agora" -
  // `tokenStore` não é observável pelo React sozinho (ver
  // api/tokenStore.ts), então este componente (único escritor do token)
  // também mantém essa cópia pra poder reagir/re-renderizar.
  const [hasToken, setHasToken] = useState(false);

  const clearSession = useCallback(() => {
    clearTokens();
    setHasToken(false);
    // limpa TODO o cache do React Query, não só o do usuário - evita dado
    // de uma sessão vazar pra próxima (ex.: logout seguido de login com
    // outro usuário na mesma aba).
    queryClient.clear();
  }, [queryClient]);

  // boot: uma única tentativa de renovar a sessão a partir do refresh
  // token salvo em localStorage. Rotation: o token usado aqui já nasce
  // invalidado no backend, por isso sempre grava o par novo devolvido.
  useEffect(() => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      setHasBootstrapped(true);
      return;
    }
    authService
      .refresh({ refresh_token: refreshToken })
      .then((tokens) => {
        setAccessToken(tokens.access_token);
        setRefreshToken(tokens.refresh_token);
        setHasToken(true);
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setHasBootstrapped(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // chamado pelo httpClient quando um 401 sobrevive a uma tentativa de
  // refresh automática (ver api/httpClient.ts) - mesma limpeza do logout,
  // sem chamar /auth/logout (a sessão já morreu no servidor).
  useEffect(() => {
    setOnSessionExpired(clearSession);
  }, [clearSession]);

  const meQuery = useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: authService.me,
    enabled: hasBootstrapped && hasToken,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.isError) {
      clearSession();
    }
  }, [meQuery.isError, clearSession]);

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: (tokens) => {
      setAccessToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      setHasToken(true);
    },
  });

  const registrarMutation = useMutation({ mutationFn: authService.registrar });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) return;
      // best-effort: se a chamada falhar (ex. rede), desloga localmente
      // mesmo assim - não trava o usuário numa sessão que ele já pediu
      // pra encerrar.
      await authService.logout({ refresh_token: refreshToken }).catch(() => undefined);
    },
    onSettled: clearSession,
  });

  const logoutTodasMutation = useMutation({
    mutationFn: authService.logoutTodas,
    onSettled: clearSession,
  });

  const atualizarPerfilMutation = useMutation({
    mutationFn: authService.atualizarPerfil,
    onSuccess: (usuarioAtualizado) => {
      queryClient.setQueryData(queryKeys.auth.me, usuarioAtualizado);
    },
  });

  const trocarSenhaMutation = useMutation({ mutationFn: authService.trocarSenha });

  const login = useCallback(
    async (dados: LoginRequest) => {
      await loginMutation.mutateAsync(dados);
    },
    [loginMutation],
  );

  const registrar = useCallback(
    async (dados: UsuarioCreate) => {
      await registrarMutation.mutateAsync(dados);
      await login({ email: dados.email, senha: dados.senha });
    },
    [registrarMutation, login],
  );

  const logout = useCallback(async () => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  const logoutTodas = useCallback(async () => {
    await logoutTodasMutation.mutateAsync();
  }, [logoutTodasMutation]);

  const atualizarPerfil = useCallback(
    async (dados: PerfilUpdate) => atualizarPerfilMutation.mutateAsync(dados),
    [atualizarPerfilMutation],
  );

  const trocarSenha = useCallback(
    async (dados: TrocarSenhaRequest) => {
      await trocarSenhaMutation.mutateAsync(dados);
    },
    [trocarSenhaMutation],
  );

  let status: AuthStatus;
  if (!hasBootstrapped || (hasToken && meQuery.isLoading)) {
    status = "loading";
  } else if (hasToken && meQuery.data) {
    status = "authenticated";
  } else {
    status = "unauthenticated";
  }

  const value: AuthContextValue = {
    status,
    usuario: meQuery.data ?? null,
    login,
    registrar,
    logout,
    logoutTodas,
    atualizarPerfil,
    trocarSenha,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
