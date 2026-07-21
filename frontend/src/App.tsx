import { lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { NavOrderProvider } from "./contexts/NavOrderContext";
import { AppRoutes } from "./routes/AppRoutes";
import { ErrorBoundary } from "./components/layout/ErrorBoundary";
import { isApiError } from "./types/api";

/**
 * Import DINÂMICO — antes, `ReactQueryDevtools` era importado estaticamente
 * e só a RENDERIZAÇÃO era condicionada a `import.meta.env.DEV`; isso
 * empacotava o código do DevTools no bundle de produção mesmo nunca
 * aparecendo (achado real da auditoria de performance, ver
 * docs/analise-arquitetural-refinamento-pickers-performance.md, seção 6).
 * `lazy()` só é chamado quando `import.meta.env.DEV` é verdadeiro — em
 * produção, nem a chamada de `lazy` acontece, então o bundler nunca inclui
 * o módulo no chunk final.
 */
const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() => import("@tanstack/react-query-devtools").then((m) => ({ default: m.ReactQueryDevtools })))
  : null;

/**
 * React Query é a infraestrutura de comunicação com a API (cache, loading,
 * refetch, invalidação, deduplicação) - ver
 * docs/analise-arquitetural-frontend.md, seção 2/9. Erro 4xx nunca é
 * re-tentado automaticamente (não adianta repetir uma requisição malformada
 * ou não autorizada); só falha de rede/5xx tenta de novo, no máximo uma vez.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        if (isApiError(error) && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 1;
      },
    },
    mutations: {
      retry: false,
    },
  },
});

export default function App() {
  return (
    // reducedMotion="user" respeita prefers-reduced-motion globalmente para
    // toda animação de `motion` na árvore, sem checagem manual por
    // componente — docs/motion-principles.md, seção 8.
    <ErrorBoundary>
      <MotionConfig reducedMotion="user">
        {/* ThemeProvider/NavOrderProvider fora do QueryClientProvider: são
            puramente UI local (localStorage), não dependem de nenhuma chamada
            de rede — ThemeProvider da Etapa de Refinamento Visual,
            NavOrderProvider da etapa de Organização da Sidebar, mesmo
            raciocínio dos dois. */}
        <ThemeProvider>
          <NavOrderProvider>
            <QueryClientProvider client={queryClient}>
              <AuthProvider>
                <ToastProvider>
                  <BrowserRouter>
                    <AppRoutes />
                  </BrowserRouter>
                </ToastProvider>
              </AuthProvider>
              {ReactQueryDevtools && (
                <Suspense fallback={null}>
                  <ReactQueryDevtools initialIsOpen={false} />
                </Suspense>
              )}
            </QueryClientProvider>
          </NavOrderProvider>
        </ThemeProvider>
      </MotionConfig>
    </ErrorBoundary>
  );
}
