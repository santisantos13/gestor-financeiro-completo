import type { ReactNode } from "react";

export interface ChartTooltipItem {
  label: string;
  value: string;
  color: string;
}

export interface ChartTooltipProps {
  title: ReactNode;
  items: ChartTooltipItem[];
}

/**
 * Tooltip de hover comum aos gráficos da Etapa de Gráficos —
 * `--color-surface-4` + `--shadow-md` + `--radius-md`, valor em Geist Mono
 * (design-system.md, seção 19). Usado via `content` customizado do
 * `<Tooltip>` do Recharts em cada gráfico (nunca o tooltip default da
 * biblioteca, que não segue nenhum token do Design System).
 */
export function ChartTooltip({ title, items }: ChartTooltipProps) {
  return (
    <div className="rounded-md border border-border-subtle bg-surface-4 px-3 py-2 text-sm shadow-md">
      <p className="mb-1 font-medium text-text-primary">{title}</p>
      <div className="space-y-0.5">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            <span className="text-text-secondary">{item.label}</span>
            <span className="ml-auto font-mono tabular text-text-primary">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
