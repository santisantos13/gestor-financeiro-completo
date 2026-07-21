import { Select } from "./Select";
import type { FilterDef } from "../../types/table";

export interface FilterBarProps<T> {
  filters: FilterDef<T>[];
  activeFilters: Record<string, string>;
  onFilterChange: (key: string, value: string) => void;
  className?: string;
}

/** Uma barra de `Select` (Etapa F2), um por `FilterDef` — cada um sempre
 * ganha uma opção "todos" implícita. design-system.md, seção 18 ("filtro
 * como barra acima do cabeçalho"). */
export function FilterBar<T>({ filters, activeFilters, onFilterChange, className = "" }: FilterBarProps<T>) {
  if (filters.length === 0) return null;

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {filters.map((filtro) => (
        <Select
          key={filtro.key}
          className="w-44"
          value={activeFilters[filtro.key] ?? ""}
          onChange={(value) => onFilterChange(filtro.key, value)}
          options={[{ value: "", label: `${filtro.label}: todos` }, ...filtro.options]}
          aria-label={filtro.label}
        />
      ))}
    </div>
  );
}
