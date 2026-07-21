import { Skeleton } from "./Skeleton";
import { TableRow } from "./TableRow";
import { TableCell } from "./TableCell";

export interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  /** Desenha uma célula extra à esquerda para a checkbox de seleção. */
  withSelection?: boolean;
}

/** Linhas de skeleton no formato exato de uma linha real de tabela —
 * nunca um placeholder genérico (design-system.md, seção 20.2). Usado por
 * `LoadingTable`. */
export function TableSkeleton({ rows = 8, columns = 4, withSelection = false }: TableSkeletonProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <TableRow key={rowIndex} className="hover:bg-transparent">
          {withSelection && (
            <TableCell>
              <Skeleton className="h-4 w-4 rounded-xs" />
            </TableCell>
          )}
          {Array.from({ length: columns }).map((_, colIndex) => (
            <TableCell key={colIndex}>
              <Skeleton className="h-3.5 w-full max-w-[10rem]" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}
