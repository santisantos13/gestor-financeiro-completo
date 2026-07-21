import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { MetricCard } from "../../ui/MetricCard";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { formatPercent } from "../../../utils/format";
import { useIndicadoresGeraisQuery } from "../../../hooks/useCentralFinanceiraQueries";

/** `/central-financeira/indicadores` — faixa compacta de 8 `MetricCard`,
 * sempre visível (números de apoio, não uma lista que possa ficar vazia).
 * docs/analise-arquitetural-dashboard.md, seção 8.3. Também é consultado
 * por `DashboardPage` para o gate de onboarding (seção 7.1) — mesma
 * `queryKey`, o React Query deduplica automaticamente, sem requisição
 * duplicada. */
export function IndicadoresStrip() {
  const { data, isLoading, error, refetch } = useIndicadoresGeraisQuery();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
        {Array.from({ length: 8 }).map((_, index) => (
          <LoadingCard key={index} lines={1} />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <SectionTitle>Indicadores gerais</SectionTitle>
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  return (
    <div>
      <SectionTitle>Indicadores gerais</SectionTitle>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
        <MetricCard label="Contas ativas" value={String(data.contas_ativas)} />
        <MetricCard label="Cartões ativos" value={String(data.cartoes_ativos)} />
        <MetricCard label="Faturas em aberto" value={String(data.faturas_em_aberto)} />
        <MetricCard label="Financiamentos ativos" value={String(data.financiamentos_ativos)} />
        <MetricCard label="Empréstimos ativos" value={String(data.emprestimos_ativos)} />
        <MetricCard label="Metas ativas" value={String(data.metas_ativas)} />
        <MetricCard label="Progresso médio de metas" value={formatPercent(data.percentual_medio_metas)} />
        <MetricCard label="Parcelas atrasadas" value={String(data.parcelas_atrasadas)} />
      </div>
    </div>
  );
}
