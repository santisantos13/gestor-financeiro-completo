import { Skeleton } from "../ui/Skeleton";

/**
 * Fallback de `<Suspense>` para o code-splitting por rota
 * (`routes/AppRoutes.tsx`) — aparece só durante o download do chunk de uma
 * página (rápido em conexão normal, e só na primeira vez que a rota é
 * visitada; o Vite mantém o chunk em cache do navegador depois). Formato
 * genérico o bastante para qualquer página (título + blocos), nenhum
 * componente de loading novo — reaproveita `Skeleton` já existente.
 */
export function RouteLoadingFallback() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
