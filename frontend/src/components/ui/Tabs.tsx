export interface TabItem {
  id: string;
  label: string;
}

export interface TabsProps {
  tabs: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
  "aria-label"?: string;
}

/**
 * Segmented control — trilho `--color-surface-3` (mesmo trilho de
 * `ProgressBar`/`Gauge`) com uma pílula `--color-accent` marcando a aba
 * ativa. Componente novo (o projeto não tinha `Tabs` até esta etapa, ver
 * docs/analise-arquitetural-dashboard-hero-redesign.md), mas reaproveita
 * 100% dos tokens já existentes — nenhuma cor/timing novo. Controlado
 * (`value`/`onChange`, sem estado interno) — quem usa decide o que
 * renderizar por aba, este componente só é a faixa de seleção.
 */
export function Tabs({ tabs, value, onChange, className = "", ...props }: TabsProps) {
  return (
    <div
      role="tablist"
      aria-label={props["aria-label"]}
      className={`inline-flex items-center gap-1 rounded-full bg-surface-3 p-1 ${className}`}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={value === tab.id}
          onClick={() => onChange(tab.id)}
          className={`rounded-full px-3 py-1 text-caption font-medium transition-colors duration-fast ease-out ${
            value === tab.id
              ? "bg-accent text-text-onAccent"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
