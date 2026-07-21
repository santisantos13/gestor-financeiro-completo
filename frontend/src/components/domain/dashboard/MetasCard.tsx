import { useNavigate } from "react-router-dom";
import type { KeyboardEvent } from "react";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { MetricCard } from "../../ui/MetricCard";
import { Badge } from "../../ui/Badge";
import { formatMoney, formatPercent } from "../../../utils/format";
import { formatDate } from "../../../utils/date";
import { useMetasQuery } from "../../../hooks/useCentralFinanceiraQueries";
import type { MetaRead } from "../../../types/centralFinanceira";

/** `/central-financeira/metas` — resumo (Sprint de Refinamento Premium,
 * item 10): contagem, progresso médio, próxima conclusão e contagem de
 * metas em risco, com botão "Ver todas". Substitui a antiga listagem de
 * cada meta individualmente. `percentual`/`situacao_planejamento` já vêm
 * calculados pelo `MetaService` (`percentual` do backend, "em risco" =
 * `situacao_planejamento === "ATRASADO"`) — este card só soma/conta/ordena
 * sobre eles, nenhuma fórmula nova. */
export function MetasCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useMetasQuery();

  if (isLoading) return <LoadingCard lines={3} />;

  if (error) {
    return (
      <Card>
        <SectionTitle>Metas</SectionTitle>
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  if (!data || data.metas.length === 0) return null;

  function abrirMetas() {
    navigate("/metas");
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      abrirMetas();
    }
  }

  const metas = data.metas;
  const percentualMedio =
    metas.reduce((total, meta) => total + Number(meta.percentual), 0) / metas.length;
  const emRisco = metas.filter((meta) => meta.situacao_planejamento === "ATRASADO");

  const proximaConclusao = [...metas]
    .filter((meta) => Number(meta.percentual) < 100)
    .sort((a, b) => Number(b.percentual) - Number(a.percentual))[0] as MetaRead | undefined;

  return (
    <Card role="link" tabIndex={0} onClick={abrirMetas} onKeyDown={onKeyDown} aria-label="Ver metas" className="cursor-pointer">
      <SectionTitle>Metas</SectionTitle>
      <div className="grid grid-cols-2 gap-2.5">
        <MetricCard label="Metas ativas" value={String(metas.length)} />
        <MetricCard label="Progresso médio" value={formatPercent(percentualMedio)} />
      </div>
      {proximaConclusao && (
        <div className="mt-3 border-t border-border-subtle pt-3">
          <p className="text-caption text-text-tertiary">Mais perto de concluir</p>
          <div className="mt-1 flex items-center justify-between gap-2">
            <span className="truncate text-sm text-text-primary">{proximaConclusao.descricao}</span>
            <span className="tabular shrink-0 text-sm font-medium text-text-secondary">
              {formatPercent(proximaConclusao.percentual)}
            </span>
          </div>
          <p className="text-caption text-text-tertiary">
            {formatMoney(proximaConclusao.valor_acumulado)} de {formatMoney(proximaConclusao.valor_alvo)}
            {proximaConclusao.data_alvo ? ` · prazo ${formatDate(proximaConclusao.data_alvo)}` : ""}
          </p>
        </div>
      )}
      {emRisco.length > 0 && (
        <p className="mt-3 border-t border-border-subtle pt-3 text-caption text-text-tertiary">
          <Badge tone="negative" className="mr-1.5">
            {emRisco.length}
          </Badge>
          {emRisco.length === 1 ? "meta atrasada" : "metas atrasadas"}
        </p>
      )}
    </Card>
  );
}
