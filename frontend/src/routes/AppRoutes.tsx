import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { AuthLayout } from "../layouts/AuthLayout";
import { LoginPage } from "../pages/auth/LoginPage";
import { RegistrarPage } from "../pages/auth/RegistrarPage";
import { RouteLoadingFallback } from "../components/layout/RouteLoadingFallback";
import { ProtectedRoute } from "./ProtectedRoute";

// Code-splitting por rota (Refinamento de Pickers/Performance,
// docs/analise-arquitetural-refinamento-pickers-performance.md, seção 7):
// achado real da auditoria — nenhuma página do projeto usava `React.lazy`,
// então o primeiro carregamento baixava o código de TODAS as telas (inclusive
// `/dev/*`) de uma vez, o `vite build` já acusando um chunk único de 741KB.
// `LoginPage`/`RegistrarPage` continuam eager (são a primeira coisa que um
// usuário não autenticado vê, lazy não ajudaria e só atrasaria); todo o resto
// carrega sob demanda, um chunk por página.
const DashboardPage = lazy(() => import("../pages/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const ContasPage = lazy(() => import("../pages/contas/ContasPage").then((m) => ({ default: m.ContasPage })));
const CartoesPage = lazy(() => import("../pages/cartoes/CartoesPage").then((m) => ({ default: m.CartoesPage })));
const CartaoDetalhePage = lazy(() =>
  import("../pages/cartoes/CartaoDetalhePage").then((m) => ({ default: m.CartaoDetalhePage })),
);
const CategoriasPage = lazy(() =>
  import("../pages/categorias/CategoriasPage").then((m) => ({ default: m.CategoriasPage })),
);
const TagsPage = lazy(() => import("../pages/tags/TagsPage").then((m) => ({ default: m.TagsPage })));
const TransacoesPage = lazy(() =>
  import("../pages/transacoes/TransacoesPage").then((m) => ({ default: m.TransacoesPage })),
);
const TransferenciasPage = lazy(() =>
  import("../pages/transferencias/TransferenciasPage").then((m) => ({ default: m.TransferenciasPage })),
);
const CalendarioPage = lazy(() =>
  import("../pages/calendario/CalendarioPage").then((m) => ({ default: m.CalendarioPage })),
);
const GraficosPage = lazy(() =>
  import("../pages/graficos/GraficosPage").then((m) => ({ default: m.GraficosPage })),
);
const FinanciamentosPage = lazy(() =>
  import("../pages/financiamentos/FinanciamentosPage").then((m) => ({ default: m.FinanciamentosPage })),
);
const EmprestimosPage = lazy(() =>
  import("../pages/emprestimos/EmprestimosPage").then((m) => ({ default: m.EmprestimosPage })),
);
const MetasPage = lazy(() => import("../pages/metas/MetasPage").then((m) => ({ default: m.MetasPage })));
const RecorrentesPage = lazy(() =>
  import("../pages/recorrentes/RecorrentesPage").then((m) => ({ default: m.RecorrentesPage })),
);
const NovidadesPage = lazy(() =>
  import("../pages/novidades/NovidadesPage").then((m) => ({ default: m.NovidadesPage })),
);
const ConfiguracoesPage = lazy(() =>
  import("../pages/configuracoes/ConfiguracoesPage").then((m) => ({ default: m.ConfiguracoesPage })),
);
const DevPage = lazy(() => import("../pages/dev/DevPage").then((m) => ({ default: m.DevPage })));
const DevTablesPage = lazy(() => import("../pages/dev/DevTablesPage").then((m) => ({ default: m.DevTablesPage })));
const DevFormsPage = lazy(() => import("../pages/dev/DevFormsPage").then((m) => ({ default: m.DevFormsPage })));

/**
 * Arvore de rotas. Cresce incrementalmente, uma entidade por etapa (mesmo
 * espirito de `main.py` ganhando um `include_router` por etapa no
 * backend) - ver docs/analise-arquitetural-frontend.md, secao 10.
 *
 * `/dev` (Etapa F3), `/dev/tables` (Etapa F4) e `/dev/forms` (Etapa F5):
 * laboratorios visuais permanentes, protegidos pela mesma `ProtectedRoute`
 * do resto do app mas deliberadamente fora do `Sidebar` (`NAV_ITEMS`) -
 * acessados so digitando a URL, nao sao navegacao real do produto. Ver
 * docs/analise-arquitetural-dashboard.md, secao 12.
 *
 * `/contas` (Etapa F6), `/categorias` (Etapa F7), `/tags` (Etapa F8) e
 * `/cartoes` (Etapa F9): rotas de CRUD real de entidade - estao no
 * `Sidebar` (`components/layout/Sidebar.tsx`) e em `MobileNav`, diferente
 * dos `/dev/*`.
 *
 * `/cartoes/:id` (Etapa F10): primeira pagina de DETALHES do projeto -
 * todas as entidades anteriores usam so `FormDialog` para visualizar/
 * editar. Nasce da preparacao de Fatura
 * (`docs/analise-arquitetural-fatura-frontend.md`): as faturas de um
 * cartao vivem inline nesta pagina, nao presas a um Drawer de lista.
 *
 * `/transacoes`: primeira entidade com volume real (docs/analise-arquitetural-transacao-frontend.md).
 * Tambem esta no `Sidebar`/`MobileNav`.
 *
 * `<Suspense>` envolve só o `<Route element={<AppLayout />}>` (Sidebar/
 * Header nunca somem durante a troca de página, só o conteúdo interno
 * mostra o fallback) — um único `Suspense` para todas as rotas protegidas,
 * não um por rota, evita remontar o layout a cada navegação.
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/registrar" element={<RegistrarPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <DashboardPage />
              </Suspense>
            }
          />
          <Route
            path="/contas"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <ContasPage />
              </Suspense>
            }
          />
          <Route
            path="/cartoes"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <CartoesPage />
              </Suspense>
            }
          />
          <Route
            path="/cartoes/:id"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <CartaoDetalhePage />
              </Suspense>
            }
          />
          <Route
            path="/categorias"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <CategoriasPage />
              </Suspense>
            }
          />
          <Route
            path="/tags"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <TagsPage />
              </Suspense>
            }
          />
          <Route
            path="/transacoes"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <TransacoesPage />
              </Suspense>
            }
          />
          <Route
            path="/transferencias"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <TransferenciasPage />
              </Suspense>
            }
          />
          <Route
            path="/calendario"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <CalendarioPage />
              </Suspense>
            }
          />
          <Route
            path="/graficos"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <GraficosPage />
              </Suspense>
            }
          />
          <Route
            path="/financiamentos"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <FinanciamentosPage />
              </Suspense>
            }
          />
          <Route
            path="/emprestimos"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <EmprestimosPage />
              </Suspense>
            }
          />
          <Route
            path="/metas"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <MetasPage />
              </Suspense>
            }
          />
          <Route
            path="/recorrentes"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <RecorrentesPage />
              </Suspense>
            }
          />
          <Route
            path="/novidades"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <NovidadesPage />
              </Suspense>
            }
          />
          <Route
            path="/configuracoes"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <ConfiguracoesPage />
              </Suspense>
            }
          />
          <Route
            path="/dev"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <DevPage />
              </Suspense>
            }
          />
          <Route
            path="/dev/tables"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <DevTablesPage />
              </Suspense>
            }
          />
          <Route
            path="/dev/forms"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <DevFormsPage />
              </Suspense>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
