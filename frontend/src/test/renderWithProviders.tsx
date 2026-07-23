/**
 * Utilitário de teste — envolve os providers que os alvos usados até agora
 * (LoginPage, TagFormDialog, DataTable, ConfiguracoesPage) precisam,
 * confirmado por leitura direta do código antes de escrever qualquer teste
 * (ver docs/analise-arquitetural-testes-frontend.md). Mesma ordem relativa
 * de `App.tsx`: QueryClientProvider > AuthProvider > ToastProvider -
 * AuthProvider usa `useQueryClient()` internamente, por isso precisa estar
 * DENTRO do QueryClientProvider. `PreferenciasProvider`/`ThemeProvider`
 * entraram na etapa de Configurações (`ConfiguracoesPage` usa
 * `DateFormatToggle` + `ThemeToggle`, que chamam `usePreferencias()`/
 * `useTheme()`) - ficam fora do `QueryClientProvider` (só localStorage, sem
 * rede), mesma posição relativa de `App.tsx`. `NavOrderProvider` continua
 * de fora: nenhum alvo atual depende de ordem de navegação.
 *
 * `MemoryRouter` no lugar do `BrowserRouter` de produção - permite controlar
 * a rota inicial (`initialEntries`) sem depender do histórico real do
 * navegador, mesma prática padrão de teste com React Router.
 */
import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../contexts/AuthContext";
import { ToastProvider } from "../contexts/ToastContext";
import { PreferenciasProvider } from "../contexts/PreferenciasContext";
import { ThemeProvider } from "../contexts/ThemeContext";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

interface RenderWithProvidersOptions {
  initialEntries?: string[];
  queryClient?: QueryClient;
}

export function renderWithProviders(ui: ReactElement, options: RenderWithProvidersOptions = {}) {
  const queryClient = options.queryClient ?? createTestQueryClient();
  const initialEntries = options.initialEntries ?? ["/"];

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <ThemeProvider>
        <PreferenciasProvider>
          <QueryClientProvider client={queryClient}>
            <AuthProvider>
              <ToastProvider>
                <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
              </ToastProvider>
            </AuthProvider>
          </QueryClientProvider>
        </PreferenciasProvider>
      </ThemeProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper }) };
}
