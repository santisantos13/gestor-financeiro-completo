import type { ReactNode } from "react";
import { SearchBar } from "./SearchBar";
import { FilterBar } from "./FilterBar";
import { ColumnVisibility } from "./ColumnVisibility";
import type { ColumnDef, FilterDef } from "../../types/table";

export interface ToolbarProps<T> {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  filters?: FilterDef<T>[];
  activeFilters?: Record<string, string>;
  onFilterChange?: (key: string, value: string) => void;
  columns?: ColumnDef<T>[];
  hiddenColumnKeys?: Set<string>;
  onToggleColumn?: (columnKey: string) => void;
  /** Slot à direita — normalmente `BulkActions` quando há seleção ativa. */
  trailing?: ReactNode;
  className?: string;
}

/** Barra acima da tabela — busca + filtros + visibilidade de coluna
 * (design-system.md, seção 18). Cada peça é opcional: `DataTable` só
 * passa o que fizer sentido para a tabela em questão. */
export function Toolbar<T>({
  searchValue,
  onSearchChange,
  searchPlaceholder,
  filters = [],
  activeFilters = {},
  onFilterChange,
  columns,
  hiddenColumnKeys,
  onToggleColumn,
  trailing,
  className = "",
}: ToolbarProps<T>) {
  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 ${className}`}>
      <div className="flex flex-wrap items-center gap-2">
        {onSearchChange && (
          <SearchBar
            value={searchValue ?? ""}
            onChange={onSearchChange}
            placeholder={searchPlaceholder}
            className="w-56"
          />
        )}
        {onFilterChange && (
          <FilterBar filters={filters} activeFilters={activeFilters} onFilterChange={onFilterChange} />
        )}
      </div>
      <div className="flex items-center gap-2">
        {trailing}
        {columns && hiddenColumnKeys && onToggleColumn && (
          <ColumnVisibility columns={columns} hiddenColumnKeys={hiddenColumnKeys} onToggle={onToggleColumn} />
        )}
      </div>
    </div>
  );
}
