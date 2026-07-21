import { Table } from "./Table";
import { TableHeader } from "./TableHeader";
import { TableBody } from "./TableBody";
import { TableCell } from "./TableCell";
import { TableRow } from "./TableRow";
import { TableSkeleton } from "./TableSkeleton";

export interface LoadingTableProps {
  columnLabels: string[];
  rows?: number;
  withSelection?: boolean;
}

/** `Table` + `TableSkeleton` no formato de uma tabela real — usado como
 * fallback de `DataTable` enquanto `isLoading` (design-system.md, seção
 * 20.3: skeleton é o padrão de primeira carga de uma seção inteira, nunca
 * um `Spinner` central por cima). */
export function LoadingTable({ columnLabels, rows = 8, withSelection = false }: LoadingTableProps) {
  return (
    <Table aria-busy="true">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {withSelection && <TableCell header aria-hidden="true" />}
          {columnLabels.map((label) => (
            <TableCell key={label} header>
              {label}
            </TableCell>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableSkeleton rows={rows} columns={columnLabels.length} withSelection={withSelection} />
      </TableBody>
    </Table>
  );
}
