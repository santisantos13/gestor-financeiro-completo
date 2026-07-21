import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { motion } from "motion/react";
import { DURATION, EASE } from "../../lib/motion";
import { useDataTable } from "../../hooks/useDataTable";
import type { BulkAction, ColumnDef, FilterDef, RowAction, SortState } from "../../types/table";
import { Table } from "./Table";
import { TableHeader } from "./TableHeader";
import { TableRow } from "./TableRow";
import { TableCell } from "./TableCell";
import { SortHeader } from "./SortHeader";
import { SelectionCheckbox } from "./SelectionCheckbox";
import { RowActions } from "./RowActions";
import { LoadingTable } from "./LoadingTable";
import { EmptyTable } from "./EmptyTable";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";
import { Toolbar } from "./Toolbar";
import { BulkActions } from "./BulkActions";
import { Card } from "./Card";
import { ErrorMessage } from "./ErrorMessage";
import { Button } from "./Button";

export interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  getRowId: (row: T) => string | number;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  filters?: FilterDef<T>[];
  searchable?: boolean;
  searchPlaceholder?: string;
  selectable?: boolean;
  rowActions?: RowAction<T>[];
  bulkActions?: BulkAction<T>[];
  columnVisibility?: boolean;
  pageSize?: number;
  pageSizeOptions?: number[];
  /** Ordenação com que a tabela já nasce (ex.: Contas quer nascer ordenada
   * do maior para o menor saldo) — repassado direto a `useDataTable`. O
   * usuário continua livre para trocar clicando em qualquer cabeçalho
   * `sortable`. */
  defaultSort?: SortState;
  emptyIcon?: LucideIcon;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  onRowClick?: (row: T) => void;
  className?: string;
  "aria-label"?: string;
}

/**
 * Orquestrador genérico do sistema de tabelas (Etapa F4) — nenhuma
 * entidade específica, colunas/filtros/ações vêm inteiramente de quem usa
 * (ver docs/analise-arquitetural-frontend.md, seção 13). Toda a mecânica
 * de busca/filtro/ordenação/paginação/seleção mora em
 * `hooks/useDataTable.ts`; este componente só decide o que renderizar em
 * cada estado. Responsivo: `<table>` real em telas `md+`, lista de cards
 * abaixo disso (design-system.md, seção 24).
 */
export function DataTable<T>({
  data,
  columns,
  getRowId,
  isLoading = false,
  error,
  onRetry,
  filters = [],
  searchable = false,
  searchPlaceholder,
  selectable = false,
  rowActions,
  bulkActions,
  columnVisibility = false,
  pageSize = 20,
  pageSizeOptions,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  emptyAction,
  onRowClick,
  className = "",
  defaultSort,
  ...ariaProps
}: DataTableProps<T>) {
  const table = useDataTable({ data, columns, getRowId, filters, pageSize, defaultSort });

  if (isLoading) {
    return <LoadingTable columnLabels={columns.map((c) => c.header)} withSelection={selectable} />;
  }

  if (error) {
    return (
      <Card>
        <ErrorMessage error={error} />
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={onRetry} className="mt-3">
            Tentar novamente
          </Button>
        )}
      </Card>
    );
  }

  const temBusca = table.query.trim() !== "";
  const temFiltroAtivo = Object.values(table.activeFilters).some((v) => v !== "");
  const semDadoNenhum = data.length === 0;
  const extraColunas = (selectable ? 1 : 0) + (rowActions && rowActions.length > 0 ? 1 : 0);
  const colSpanTotal = table.visibleColumns.length + extraColunas;
  // `hideOnMobile` só faz sentido na lista de cards abaixo de `md` — a
  // tabela real usa todas as `visibleColumns` normalmente. Sem este
  // filtro, o card mobile mostrava colunas pensadas só para desktop (ex.
  // "Categoria pai", "Instituição"), lotando o card com informação
  // secundária — bug real, não só um ajuste estético (design-system.md,
  // seção 24).
  const mobileColumns = table.visibleColumns.filter((column) => !column.hideOnMobile);

  return (
    <div className={`space-y-3 ${className}`}>
      {(searchable || filters.length > 0 || columnVisibility || (bulkActions && bulkActions.length > 0)) && (
        <Toolbar
          searchValue={searchable ? table.query : undefined}
          onSearchChange={searchable ? table.setQuery : undefined}
          searchPlaceholder={searchPlaceholder}
          filters={filters}
          activeFilters={table.activeFilters}
          onFilterChange={filters.length > 0 ? table.setFilter : undefined}
          columns={columnVisibility ? columns : undefined}
          hiddenColumnKeys={columnVisibility ? table.hiddenColumnKeys : undefined}
          onToggleColumn={columnVisibility ? table.toggleColumnVisibility : undefined}
          trailing={
            bulkActions && (
              <BulkActions
                selectedCount={table.selectedCount}
                selectedRows={table.selectedRows}
                actions={bulkActions}
                onClearSelection={table.clearSelection}
              />
            )
          }
        />
      )}

      {/* Desktop/tablet: tabela real, cabeçalho sticky, ordenação por coluna. */}
      <div className="hidden md:block">
        <Table aria-label={ariaProps["aria-label"]}>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              {selectable && (
                <TableCell header className="w-10">
                  <SelectionCheckbox
                    label="Selecionar todos nesta página"
                    checked={table.isAllOnPageSelected}
                    onChange={table.toggleSelectAllOnPage}
                  />
                </TableCell>
              )}
              {table.visibleColumns.map((column) =>
                column.sortable ? (
                  <SortHeader
                    key={column.key}
                    active={table.sort.columnKey === column.key}
                    direction={table.sort.columnKey === column.key ? table.sort.direction : null}
                    align={column.align}
                    onClick={() => table.toggleSort(column.key)}
                    className={column.width}
                  >
                    {column.header}
                  </SortHeader>
                ) : (
                  <TableCell key={column.key} header align={column.align} className={column.width}>
                    {column.header}
                  </TableCell>
                ),
              )}
              {rowActions && rowActions.length > 0 && <TableCell header aria-hidden="true" />}
            </TableRow>
          </TableHeader>
          {/* A key NUNCA inclui `table.query`: incluir a busca crua fazia o
              corpo inteiro da tabela remontar (fade de --duration-base) a
              CADA tecla digitada, mesmo com `useDeferredValue` no hook —
              o remonte ignorava o adiamento e recriava todas as linhas a
              cada caractere, a causa mais provável de "o site parece
              lento" durante busca. Trocar de página/filtro/ordenação
              continua remontando com fade (mudança de contexto real,
              vale a transição); digitar não. */}
          <motion.tbody
            key={`${table.page}-${JSON.stringify(table.activeFilters)}-${table.sort.columnKey}-${table.sort.direction}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: DURATION.base, ease: EASE.out } }}
          >
            {table.paginatedRows.length === 0 ? (
              <EmptyTable
                colSpan={colSpanTotal || 1}
                icon={emptyIcon}
                title={emptyTitle ?? (semDadoNenhum ? "Nenhum registro ainda" : "Nada encontrado")}
                description={
                  emptyDescription ??
                  (semDadoNenhum
                    ? undefined
                    : temBusca || temFiltroAtivo
                      ? "Tente ajustar a busca ou os filtros."
                      : undefined)
                }
                action={emptyAction}
              />
            ) : (
              table.paginatedRows.map((row) => {
                const id = getRowId(row);
                return (
                  <TableRow
                    key={id}
                    selected={table.selectedIds.has(id)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={onRowClick ? "cursor-pointer" : ""}
                  >
                    {selectable && (
                      <TableCell>
                        <SelectionCheckbox
                          label="Selecionar linha"
                          checked={table.selectedIds.has(id)}
                          onChange={() => table.toggleSelect(id)}
                        />
                      </TableCell>
                    )}
                    {table.visibleColumns.map((column) => (
                      <TableCell key={column.key} align={column.align}>
                        {column.render ? column.render(row) : String(column.accessor(row) ?? "—")}
                      </TableCell>
                    ))}
                    {rowActions && rowActions.length > 0 && (
                      <TableCell>
                        <RowActions row={row} actions={rowActions} />
                      </TableCell>
                    )}
                  </TableRow>
                );
              })
            )}
          </motion.tbody>
        </Table>
      </div>

      {/* Mobile: lista de cards — design-system.md, seção 24 (tabela densa
          vira card compacto abaixo de `md`, nunca scroll horizontal). */}
      <div className="space-y-3 md:hidden">
        {table.paginatedRows.length === 0 ? (
          <Card>
            <EmptyState
              icon={emptyIcon ?? Inbox}
              title={emptyTitle ?? (semDadoNenhum ? "Nenhum registro ainda" : "Nada encontrado")}
              description={
                emptyDescription ?? (semDadoNenhum ? undefined : "Tente ajustar a busca ou os filtros.")
              }
              action={emptyAction}
            />
          </Card>
        ) : (
          table.paginatedRows.map((row) => {
            const id = getRowId(row);
            return (
              <Card key={id} className={table.selectedIds.has(id) ? "border-accent" : ""}>
                <div className="flex items-start gap-3">
                  {selectable && (
                    <SelectionCheckbox
                      label="Selecionar linha"
                      checked={table.selectedIds.has(id)}
                      onChange={() => table.toggleSelect(id)}
                      className="mt-1"
                    />
                  )}
                  <div className="min-w-0 flex-1 space-y-1.5">
                    {mobileColumns.map((column) => (
                      <div key={column.key} className="flex items-center justify-between gap-3 text-sm">
                        <span className="shrink-0 text-text-tertiary">{column.header}</span>
                        <span
                          className={`min-w-0 truncate ${
                            column.align === "right" ? "tabular text-text-primary" : "text-text-primary"
                          }`}
                        >
                          {column.render ? column.render(row) : String(column.accessor(row) ?? "—")}
                        </span>
                      </div>
                    ))}
                  </div>
                  {rowActions && rowActions.length > 0 && (
                    <RowActions row={row} actions={rowActions} size="md" className="opacity-100" />
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>

      <Pagination
        page={table.page}
        totalPages={table.totalPages}
        totalItems={table.totalItems}
        pageSize={table.pageSize}
        onPageChange={table.setPage}
        onPageSizeChange={table.setPageSize}
        pageSizeOptions={pageSizeOptions}
      />
    </div>
  );
}
