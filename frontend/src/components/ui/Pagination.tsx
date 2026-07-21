import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";
import { Select } from "./Select";

export interface PaginationProps {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  className?: string;
}

const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

/** Controles de paginação no rodapé da tabela — design-system.md, seção
 * 18. "Mostrando X–Y de Z" + anterior/próximo + seletor opcional de itens
 * por página (reaproveita `Select`, Etapa F2). */
export function Pagination({
  page,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_PAGE_SIZE_OPTIONS,
  className = "",
}: PaginationProps) {
  const inicio = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const fim = Math.min(page * pageSize, totalItems);

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle pt-3 ${className}`}
    >
      <p className="text-caption text-text-tertiary">
        Mostrando <span className="tabular text-text-secondary">{inicio}–{fim}</span> de{" "}
        <span className="tabular text-text-secondary">{totalItems}</span>
      </p>
      <div className="flex items-center gap-3">
        {onPageSizeChange && (
          <div className="flex items-center gap-2">
            <span className="text-caption text-text-tertiary">Por página</span>
            <Select
              className="w-20"
              value={String(pageSize)}
              onChange={(value) => onPageSizeChange(Number(value))}
              options={pageSizeOptions.map((size) => ({ value: String(size), label: String(size) }))}
              aria-label="Itens por página"
            />
          </div>
        )}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            aria-label="Página anterior"
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </Button>
          <span className="tabular px-2 text-sm text-text-secondary">
            {page} / {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            aria-label="Próxima página"
          >
            <ChevronRight size={16} aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
}
