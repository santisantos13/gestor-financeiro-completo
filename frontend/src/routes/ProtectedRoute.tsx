import { Navigate, Outlet } from "react-router-dom";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";

/** Guarda de rota - ver docs/analise-arquitetural-frontend.md, seção 7.
 * `loading`: ainda não sabemos se a sessão salva é válida (boot em
 * andamento) - nunca deixa a tela de login piscar antes disso.
 * `unauthenticated`: redireciona para /login.
 * `authenticated`: renderiza a rota protegida normalmente. */
export function ProtectedRoute() {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
