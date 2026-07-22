import { useState } from "react";
import { Card } from "../../components/ui/Card";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Button } from "../../components/ui/Button";
import { Tabs } from "../../components/ui/Tabs";
import { MesAnoSeletor } from "../../components/domain/calendario/MesAnoSeletor";
import { EvolucaoSaldoChart } from "../../components/domain/graficos/EvolucaoSaldoChart";
import { EntradasSaidasChart } from "../../components/domain/graficos/EntradasSaidasChart";
import { GastosPorCategoriaChart } from "../../components/domain/graficos/GastosPorCategoriaChart";
import { GastosPorCartaoChart } from "../../components/domain/graficos/GastosPorCartaoChart";
import { SaldoPorContaChart } from "../../components/domain/graficos/SaldoPorContaChart";
import {
  useGraficosPeriodoQuery,
  useGraficosTendenciasQuery,
  useSaldoConsolidadoQuery,
} from "../../hooks/useCentralFinanceiraQueries";

const OPCOES_JANELA = [
  { id: "6", label: "6 meses" },
  { id: "12", label: "12 meses" },
  { id: "24", label: "24 meses" },
];

/**
 * Página `/graficos` — segunda das "duas coisas" pedidas (a primeira é o
 * mini-card `EvolucaoSaldoCard` do Dashboard). 5 gráficos, cada um em seu
 * próprio `Card`, sem cross-filtering entre eles (fora de escopo, ver
 * docs/analise-arquitetural-graficos.md, seção 7): "Evolução do saldo" e
 * "Entradas x Saídas" compartilham a janela de meses (`useGraficosTendenciasQuery`,
 * um único fetch); "Gastos por categoria"/"por cartão" compartilham o
 * seletor de mês (`useGraficosPeriodoQuery`); "Saldo por conta" reaproveita
 * `useSaldoConsolidadoQuery`, já usado pelo hero do Dashboard — nenhuma
 * chamada nova para esse 5º gráfico.
 */
export function GraficosPage() {
  const hoje = new Date();
  const [janela, setJanela] = useState("12");
  const [periodo, setPeriodo] = useState({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });

  const tendencias = useGraficosTendenciasQuery(Number(janela));
  const periodoQuery = useGraficosPeriodoQuery(periodo.ano, periodo.mes);
  const saldoConsolidado = useSaldoConsolidadoQuery();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-h1 font-semibold text-text-primary">Gráficos</h1>
        <p className="mt-1 text-sm text-text-secondary">Uma visão visual das suas finanças ao longo do tempo.</p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionTitle>Evolução do saldo</SectionTitle>
            <Tabs tabs={OPCOES_JANELA} value={janela} onChange={setJanela} aria-label="Janela de meses" />
          </div>
          {tendencias.isLoading ? (
            <LoadingCard lines={4} />
          ) : tendencias.error ? (
            <>
              <ErrorMessage error={tendencias.error} />
              <Button size="sm" variant="secondary" onClick={() => tendencias.refetch()} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : (
            <EvolucaoSaldoChart meses={tendencias.data?.meses ?? []} />
          )}
        </Card>

        <Card>
          <SectionTitle>Entradas x Saídas por mês</SectionTitle>
          {tendencias.isLoading ? (
            <LoadingCard lines={4} />
          ) : tendencias.error ? (
            <>
              <ErrorMessage error={tendencias.error} />
              <Button size="sm" variant="secondary" onClick={() => tendencias.refetch()} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : (
            <EntradasSaidasChart meses={tendencias.data?.meses ?? []} />
          )}
        </Card>

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionTitle>Gastos por categoria</SectionTitle>
            <MesAnoSeletor ano={periodo.ano} mes={periodo.mes} onSelecionar={(ano, mes) => setPeriodo({ ano, mes })} />
          </div>
          {periodoQuery.isLoading ? (
            <LoadingCard lines={4} />
          ) : periodoQuery.error ? (
            <>
              <ErrorMessage error={periodoQuery.error} />
              <Button size="sm" variant="secondary" onClick={() => periodoQuery.refetch()} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : (
            <GastosPorCategoriaChart gastos={periodoQuery.data?.gastos_por_categoria ?? []} />
          )}
        </Card>

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionTitle>Gastos por cartão</SectionTitle>
            <MesAnoSeletor ano={periodo.ano} mes={periodo.mes} onSelecionar={(ano, mes) => setPeriodo({ ano, mes })} />
          </div>
          {periodoQuery.isLoading ? (
            <LoadingCard lines={4} />
          ) : periodoQuery.error ? (
            <>
              <ErrorMessage error={periodoQuery.error} />
              <Button size="sm" variant="secondary" onClick={() => periodoQuery.refetch()} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : (
            <GastosPorCartaoChart gastos={periodoQuery.data?.gastos_por_cartao ?? []} />
          )}
        </Card>

        <Card className="lg:col-span-2">
          <SectionTitle>Distribuição do saldo atual por conta</SectionTitle>
          {saldoConsolidado.isLoading ? (
            <LoadingCard lines={4} />
          ) : saldoConsolidado.error ? (
            <>
              <ErrorMessage error={saldoConsolidado.error} />
              <Button size="sm" variant="secondary" onClick={() => saldoConsolidado.refetch()} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : (
            <SaldoPorContaChart contas={saldoConsolidado.data?.contas ?? []} />
          )}
        </Card>
      </div>
    </div>
  );
}
