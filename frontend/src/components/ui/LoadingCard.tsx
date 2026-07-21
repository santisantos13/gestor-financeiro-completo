import { Card } from "./Card";
import { Skeleton } from "./Skeleton";

export interface LoadingCardProps {
  /** Quantas linhas de skeleton desenhar dentro do card, além do título. */
  lines?: number;
  className?: string;
}

/** `Card` + `Skeleton` no formato de um card de dashboard genérico — usado
 * como fallback de qualquer seção enquanto `isLoading` (design-system.md,
 * seção 20.3: skeleton é o padrão de primeira carga de uma seção inteira,
 * nunca um Spinner central por cima). */
export function LoadingCard({ lines = 3, className = "" }: LoadingCardProps) {
  return (
    <Card className={className}>
      <Skeleton className="h-4 w-24" />
      <div className="mt-4 space-y-2.5">
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton key={index} className="h-3.5 w-full" />
        ))}
      </div>
    </Card>
  );
}
