import { useNavigate } from "react-router-dom";
import type { KeyboardEvent } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { EvolucaoSaldoChart } from "../graficos/EvolucaoSaldoChart";
import { formatMoney } from "../../../utils/format";
import { useGraficosTendenciasQuery } from "../../../hooks/useCentralFinanceiraQueries";

/** Janela mais curta que a página `/graficos` (padrão 12 meses) — o
 * mini-card é só um "vislumbre" da tendência recente, não uma análise
 * completa (docs/analise-arquitetural-graficos.md, seção 6). */
const MESES_MINI_CARD = 6;

/**
 * Mini-card "Evolução do saldo" do Dashboard — Etapa de Gráficos, uma das
 * duas superfícies pedidas ("as duas coisas": este card + a página
 * `/graficos` completa). Clicável (mesmo padrão de `MetasCard`), leva à
 * página cheia. Mostra a variação do saldo entre o primeiro e o último mês
 * da janela como indicador rápido (positive/negative, seção 6.4) — nenhum
 * cálculo novo, só a diferença entre dois pontos que o gráfico já recebeu.
 */
export function EvolucaoSaldoCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useGraficosTendenciasQuery(MESES_MINI_CARD);

  if (isLoading) return <LoadingCard lines={3} />;

  if (error) {
    return (
      <Card>
        <SectionTitle>Evolução do saldo</SectionTitle>
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  if (!data || data.meses.length === 0) return null;

  function abrirGraficos() {
    navigate("/graficos");
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      abrirGraficos();
    }
  }

  const meses = data.meses;
  const primeiro = Number(meses[0].saldo_total);
  const ultimo = Number(meses[meses.length - 1].saldo_total);
  const variacao = ultimo - primeiro;

  return (
    <Card
      role="link"
      tabIndex={0}
      onClick={abrirGraficos}
      onKeyDown={onKeyDown}
      aria-label="Ver gráficos"
      className="cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <SectionTitle>Evolução do saldo</SectionTitle>
        {meses.length > 1 && (
          <span
            className={`flex items-center gap-1 text-caption font-medium ${variacao >= 0 ? "text-positive" : "text-negative"}`}
          >
            {variacao >= 0 ? <TrendingUp size={14} aria-hidden="true" /> : <TrendingDown size={14} aria-hidden="true" />}
            {formatMoney(Math.abs(variacao))}
          </span>
        )}
      </div>
      <EvolucaoSaldoChart meses={meses} compact />
    </Card>
  );
}
