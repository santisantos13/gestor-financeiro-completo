/**
 * Utilitário de teste — envolve só os providers que os alvos desta etapa
 * (LoginPage, TagFormDialog, DataTable) realmente precisam, confirmado por
 * leitura direta do código antes de escrever qualquer teste (ver
 * docs/analise-arquitetural-testes-frontend.md). Mesma ordem relativa de
 * `App.tsx`: QueryClientProvider > AuthProvider > ToastProvider - AuthProvider
 * usa `useQueryClient()` internamente, por isso precisa estar DENTRO do
 * QueryClientProvider. ThemeProvider/NavOrderProvider ficam de fora: nenhum
 * dos 3 alvos depende de tema ou de ordem de navegação.
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
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ToastProvider>
            <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
          </ToastProvider>
        </AuthProvider>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper }) };
}
