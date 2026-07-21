import type { KeyboardEvent } from "react";
import { Home } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { ProgressBar } from "../../ui/ProgressBar";
import { Gauge } from "../../ui/Gauge";
import { formatMoney, formatPercent } from "../../../utils/format";
import { formatDate } from "../../../utils/date";
import { useFinanciamentosQuery } from "../../../hooks/useCentralFinanceiraQueries";
import type { FinanciamentoResumo } from "../../../types/centralFinanceira";

/** `/central-financeira/financiamentos` — some se `financiamentos.length === 0`
 * (seção 10). `parcelas_pagas`/`parcelas_restantes`/`proxima_parcela_*` já
 * vêm calculados pelo backend (`FinanciamentoResumo`) — nenhum cálculo
 * aqui. Card inteiro clicável (navega para `/financiamentos`, Sprint de
 * Refinamento Premium item 12 — antes era o único card sem destino).
 *
 * "Financiamento Principal" (Refinamento Visual, pedido explícito do
 * usuário, referência de outro app): o financiamento com a parcela mais
 * próxima do vencimento ganha destaque no topo, com um `Gauge` de
 * progresso — em vez de um card novo dedicado (que duplicaria este),
 * mantém tudo num só lugar. Os demais (se houver mais de um) continuam
 * listados abaixo, como já era. Ver
 * docs/analise-arquitetural-dashboard-hero-redesign.md, decisão 6. */
export function FinanciamentosCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useFinanciamentosQuery();

  if (isLoading) return <LoadingCard lines={3} />;

  if (error) {
    return (
      <Card>
        <SectionTitle>Financiamentos</SectionTitle>
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  if (!data || data.financiamentos.length === 0) return null;

  function abrirFinanciamentos() {
    navigate("/financiamentos");
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      abrirFinanciamentos();
    }
  }

  const principal = [...data.financiamentos].sort((a, b) => {
    if (!a.proxima_parcela_data) return 1;
    if (!b.proxima_parcela_data) return -1;
    return a.proxima_parcela_data.localeCompare(b.proxima_parcela_data);
  })[0] as FinanciamentoResumo;
  const demais = data.financiamentos.filter((f) => f.id !== principal.id);
  const progressoPrincipal = (principal.parcelas_pagas / principal.num_parcelas) * 100;

  return (
    <Card
      role="link"
      tabIndex={0}
      onClick={abrirFinanciamentos}
      onKeyDown={onKeyDown}
      aria-label="Ver financiamentos"
      className="cursor-pointer"
    >
      <SectionTitle>Financiamentos</SectionTitle>

      <div className="flex items-center gap-3">
        <Gauge
          value={progressoPrincipal}
          tone="accent"
          aria-label={`${principal.parcelas_pagas} de ${principal.num_parcelas} parcelas pagas`}
        >
          <span className="text-caption font-semibold text-text-primary">{formatPercent(progressoPrincipal)}</span>
        </Gauge>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">
            {principal.bem_financiado ?? principal.descricao}
          </p>
          <p className="text-caption text-text-tertiary">
            {principal.parcelas_pagas}/{principal.num_parcelas} parcelas
            {principal.proxima_parcela_data && principal.proxima_parcela_valor
              ? ` · próxima ${formatMoney(principal.proxima_parcela_valor)} em ${formatDate(principal.proxima_parcela_data)}`
              : ""}
          </p>
        </div>
        <FinancialBadge status={principal.status} className="shrink-0" />
      </div>

      {demais.length > 0 && (
        <ul className="mt-4 space-y-4 border-t border-border-subtle pt-4">
          {demais.map((financiamento) => {
            const progresso = (financiamento.parcelas_pagas / financiamento.num_parcelas) * 100;
            return (
              <li key={financiamento.id}>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm text-text-primary">
                    <Home size={14} className="text-text-tertiary" aria-hidden="true" />
                    {financiamento.descricao}
                  </span>
                  <FinancialBadge status={financiamento.status} />
                </div>
                <p className="mt-1 text-caption text-text-tertiary">
                  Saldo devedor:{" "}
                  <span className="tabular text-text-secondary">{formatMoney(financiamento.saldo_devedor)}</span>
                </p>
                <ProgressBar
                  value={progresso}
                  className="mt-2"
                  aria-label={`${financiamento.parcelas_pagas} de ${financiamento.num_parcelas} parcelas pagas`}
                />
                <p className="mt-1 text-caption text-text-tertiary">
                  {financiamento.parcelas_pagas}/{financiamento.num_parcelas} parcelas
                  {financiamento.proxima_parcela_data && financiamento.proxima_parcela_valor
                    ? ` · próxima: ${formatMoney(financiamento.proxima_parcela_valor)}`
                    : ""}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
