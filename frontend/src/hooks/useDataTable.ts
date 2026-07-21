import { useDeferredValue, useMemo, useState } from "react";
import type { ColumnDef, FilterDef, SortDirection, SortState } from "../types/table";

export interface UseDataTableOptions<T> {
  data: T[];
  columns: ColumnDef<T>[];
  getRowId: (row: T) => string | number;
  filters?: FilterDef<T>[];
  pageSize?: number;
  /** Ordenação inicial (ex.: Contas quer nascer já ordenada do maior para o
   * menor saldo) — o usuário continua livre para trocar clicando em
   * qualquer cabeçalho `sortable`, exatamente como se tivesse clicado ele
   * mesmo nesta coluna primeiro. `undefined` (padrão) mantém o
   * comportamento de sempre: nasce sem ordenação, na ordem que veio de
   * `data`. */
  defaultSort?: SortState;
}

const DEFAULT_PAGE_SIZE = 20;

/**
 * Motor genérico de busca+filtro+ordenação+paginação+seleção sobre
 * `data: T[]`, 100% client-side — decisão já aprovada em
 * docs/analise-arquitetural-frontend.md, seção 13 (backend não expõe
 * parâmetro de ordenação em nenhum endpoint de listagem; `limit` padrão de
 * 100 já cobre o volume realista de um usuário único). `DataTable`
 * (components/ui/DataTable.tsx) é o único consumidor direto deste hook —
 * mantém a lógica fora do componente, mesmo espírito de
 * `hooks/useCentralFinanceiraQueries.ts` (Etapa F3).
 *
 * `useDeferredValue` na busca evita travar a digitação recalculando o
 * filtro sobre milhares de linhas a cada tecla — motion-principles.md,
 * seção 9 (alvo de 60fps mesmo durante digitação).
 */
export function useDataTable<T>({
  data,
  columns,
  getRowId,
  filters = [],
  pageSize = DEFAULT_PAGE_SIZE,
  defaultSort,
}: UseDataTableOptions<T>) {
  const [query, setQueryState] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<SortState>(defaultSort ?? { columnKey: null, direction: null });
  const [page, setPage] = useState(1);
  const [currentPageSize, setCurrentPageSizeState] = useState(pageSize);
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set());
  const [hiddenColumnKeys, setHiddenColumnKeys] = useState<Set<string>>(new Set());

  const visibleColumns = useMemo(
    () => columns.filter((column) => !hiddenColumnKeys.has(column.key)),
    [columns, hiddenColumnKeys],
  );

  const searched = useMemo(() => {
    const trimmed = deferredQuery.trim().toLowerCase();
    if (!trimmed) return data;
    return data.filter((row) =>
      columns.some((column) => {
        const valor = column.accessor(row);
        return valor !== null && valor !== undefined && String(valor).toLowerCase().includes(trimmed);
      }),
    );
  }, [data, columns, deferredQuery]);

  const filtered = useMemo(() => {
    const entradas = Object.entries(activeFilters).filter(([, value]) => value !== "");
    if (entradas.length === 0) return searched;
    return searched.filter((row) =>
      entradas.every(([filterKey, value]) => {
        const filtro = filters.find((f) => f.key === filterKey);
        return filtro ? filtro.predicate(row, value) : true;
      }),
    );
  }, [searched, activeFilters, filters]);

  const sorted = useMemo(() => {
    if (!sort.columnKey || !sort.direction) return filtered;
    const coluna = columns.find((c) => c.key === sort.columnKey);
    if (!coluna) return filtered;
    const copia = [...filtered];
    copia.sort((a, b) => {
      const va = coluna.accessor(a);
      const vb = coluna.accessor(b);
      if (va === vb) return 0;
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      const comparacao = va < vb ? -1 : 1;
      return sort.direction === "asc" ? comparacao : -comparacao;
    });
    return copia;
  }, [filtered, sort, columns]);

  const totalItems = sorted.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / currentPageSize));
  const clampedPage = Math.min(page, totalPages);

  const paginatedRows = useMemo(() => {
    const start = (clampedPage - 1) * currentPageSize;
    return sorted.slice(start, start + currentPageSize);
  }, [sorted, clampedPage, currentPageSize]);

  const selectedRows = useMemo(
    () => data.filter((row) => selectedIds.has(getRowId(row))),
    [data, selectedIds, getRowId],
  );

  function setQuery(value: string) {
    setQueryState(value);
    setPage(1);
  }

  function setFilter(filterKey: string, value: string) {
    setActiveFilters((atual) => ({ ...atual, [filterKey]: value }));
    setPage(1);
  }

  function clearFilters() {
    setActiveFilters({});
    setPage(1);
  }

  function setPageSize(size: number) {
    setCurrentPageSizeState(size);
    setPage(1);
  }

  function toggleSort(columnKey: string) {
    setSort((atual) => {
      if (atual.columnKey !== columnKey) return { columnKey, direction: "asc" };
      const proxima: SortDirection = atual.direction === "asc" ? "desc" : atual.direction === "desc" ? null : "asc";
      return { columnKey: proxima ? columnKey : null, direction: proxima };
    });
  }

  function toggleSelect(id: string | number) {
    setSelectedIds((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(id)) proximo.delete(id);
      else proximo.add(id);
      return proximo;
    });
  }

  function toggleSelectAllOnPage() {
    const idsDaPagina = paginatedRows.map(getRowId);
    const todosSelecionados = idsDaPagina.length > 0 && idsDaPagina.every((id) => selectedIds.has(id));
    setSelectedIds((atual) => {
      const proximo = new Set(atual);
      if (todosSelecionados) {
        idsDaPagina.forEach((id) => proximo.delete(id));
      } else {
        idsDaPagina.forEach((id) => proximo.add(id));
      }
      return proximo;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  function toggleColumnVisibility(columnKey: string) {
    setHiddenColumnKeys((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(columnKey)) proximo.delete(columnKey);
      else proximo.add(columnKey);
      return proximo;
    });
  }

  return {
    query,
    setQuery,
    activeFilters,
    setFilter,
    clearFilters,
    sort,
    toggleSort,
    page: clampedPage,
    setPage,
    pageSize: currentPageSize,
    setPageSize,
    totalPages,
    totalItems,
    paginatedRows,
    visibleColumns,
    hiddenColumnKeys,
    toggleColumnVisibility,
    selectedIds,
    selectedRows,
    selectedCount: selectedIds.size,
    toggleSelect,
    toggleSelectAllOnPage,
    isAllOnPageSelected:
      paginatedRows.length > 0 && paginatedRows.every((row) => selectedIds.has(getRowId(row))),
    clearSelection,
  };
}

export type UseDataTableReturn<T> = ReturnType<typeof useDataTable<T>>;
