export interface MetricCardProps {
  label: string;
  value: string;
  className?: string;
}

/** Versão compacta do `StatCard`, sem `AnimatedNumber` grande — usada na
 * faixa de Indicadores Gerais (contagens de apoio, não os números "hero" do
 * Resumo). design-system.md, seção 16, adaptado para densidade maior —
 * docs/analise-arquitetural-dashboard.md, seção 8.3. */
export function MetricCard({ label, value, className = "" }: MetricCardProps) {
  return (
    <div className={`rounded-md border border-border-subtle bg-surface-1 px-3 py-2.5 ${className}`}>
      <p className="text-caption text-text-tertiary">{label}</p>
      <p className="tabular mt-0.5 text-h3 font-semibold text-text-primary">{value}</p>
    </div>
  );
}
