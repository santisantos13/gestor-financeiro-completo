import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileDown } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Button } from "../../components/ui/Button";
import { Switch } from "../../components/ui/Switch";
import { Tabs } from "../../components/ui/Tabs";
import { MesAnoSeletor } from "../../components/domain/calendario/MesAnoSeletor";
import { EvolucaoSaldoChart } from "../../components/domain/graficos/EvolucaoSaldoChart";
import { EntradasSaidasChart } from "../../components/domain/graficos/EntradasSaidasChart";
import { GastosPorCategoriaChart } from "../../components/domain/graficos/GastosPorCategoriaChart";
import { GastosPorCartaoChart } from "../../components/domain/graficos/GastosPorCartaoChart";
import { GastosPorContaChart } from "../../components/domain/graficos/GastosPorContaChart";
import { GastosComparativoChart } from "../../components/domain/graficos/GastosComparativoChart";
import { SaldoPorContaChart } from "../../components/domain/graficos/SaldoPorContaChart";
import { ResumoGastosMes } from "../../components/domain/graficos/ResumoGastosMes";
import {
  useGraficosPeriodoQuery,
  useGraficosTendenciasQuery,
  useSaldoConsolidadoQuery,
} from "../../hooks/useCentralFinanceiraQueries";
import { mesAnterior, nomeMes } from "../../utils/date";

const OPCOES_JANELA = [
  { id: "6", label: "6 meses" },
  { id: "12", label: "12 meses" },
  { id: "24", label: "24 meses" },
];

/**
 * Página `/graficos` — segunda das "duas coisas" pedidas (a primeira é o
 * mini-card `EvolucaoSaldoCard` do Dashboard). 6 gráficos, cada um em seu
 * próprio `Card`, sem cross-filtering entre eles (fora de escopo, ver
 * docs/analise-arquitetural-graficos.md, seção 7): "Evolução do saldo" e
 * "Entradas x Saídas" compartilham a janela de meses (`useGraficosTendenciasQuery`,
 * um único fetch); "Gastos por categoria"/"por cartão"/"por conta"
 * compartilham o seletor de mês (`useGraficosPeriodoQuery`) — `gastos_por_conta`
 * já vem na mesma resposta dos outros dois, nenhum fetch novo (seção 8);
 * "Saldo por conta" (distribuição do saldo ATUAL, não o gasto DO MÊS do
 * gráfico novo) reaproveita `useSaldoConsolidadoQuery`, já usado pelo hero
 * do Dashboard.
 *
 * Melhorias de Gráficos (2026-07-26, docs/analise-arquitetural-graficos.md
 * seção 9): (1) o card "Gastos do mês" ganhou um total + variação vs mês
 * anterior (`ResumoGastosMes`), buscando um segundo `graficos_periodo` do
 * mês anterior — nenhum endpoint novo; (2) os 3 seletores de mês duplicados
 * (um por card de gasto) viraram um único seletor compartilhado neste
 * cabeçalho; (3) um atalho "Baixar relatório" leva para `/relatorios` já
 * com o mês selecionado aqui; (4) categoria/conta ganharam drill-down para
 * `/transacoes` filtrado (cartão vai para `/cartoes/:id` - compras de
 * cartão nunca aparecem em `/transacoes`, ver `GastosPorCartaoChart`); (5)
 * os 3 gráficos de gasto agrupam a cauda longa em "Outros" acima de 6
 * itens; (6) um toggle "Comparar com mês anterior" troca o donut/barra
 * específico por `GastosComparativoChart` (barras agrupadas atual x
 * anterior) nas 3 seções.
 */
export function GraficosPage() {
  const navigate = useNavigate();
  const hoje = new Date();
  const [janela, setJanela] = useState("12");
  const [periodo, setPeriodo] = useState({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });
  const [comparar, setComparar] = useState(false);

  const tendencias = useGraficosTendenciasQuery(Number(janela));
  const periodoQuery = useGraficosPeriodoQuery(periodo.ano, periodo.mes);
  const saldoConsolidado = useSaldoConsolidadoQuery();

  const anterior = useMemo(() => mesAnterior(periodo.ano, periodo.mes), [periodo]);
  const periodoAnteriorQuery = useGraficosPeriodoQuery(anterior.ano, anterior.mes);

  const totalAtual = useMemo(
    () => (periodoQuery.data?.gastos_por_categoria ?? []).reduce((soma, g) => soma + Number(g.total), 0),
    [periodoQuery.data],
  );
  const totalAnterior = useMemo(
    () =>
      periodoAnteriorQuery.data
        ? periodoAnteriorQuery.data.gastos_por_categoria.reduce((soma, g) => soma + Number(g.total), 0)
        : null,
    [periodoAnteriorQuery.data],
  );

  const carregandoGastos = periodoQuery.isLoading || (comparar && periodoAnteriorQuery.isLoading);
  const erroGastos = periodoQuery.error ?? (comparar ? periodoAnteriorQuery.error : null);

  function tentarNovamenteGastos() {
    periodoQuery.refetch();
    if (comparar) periodoAnteriorQuery.refetch();
  }

  function irParaTransacoesPorCategoria(categoriaId: number) {
    navigate(`/transacoes?categoria_id=${categoriaId}&ano=${periodo.ano}&mes=${periodo.mes}`);
  }

  function irParaTransacoesPorConta(contaId: number) {
    navigate(`/transacoes?conta_id=${contaId}&ano=${periodo.ano}&mes=${periodo.mes}`);
  }

  function irParaCartao(cartaoId: number) {
    navigate(`/cartoes/${cartaoId}`);
  }

  const labelAtual = `${nomeMes(periodo.mes)}/${periodo.ano}`;
  const labelAnterior = `${nomeMes(anterior.mes)}/${anterior.ano}`;

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

        <Card className="lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <SectionTitle>Gastos do mês</SectionTitle>
              {!periodoQuery.isLoading && !periodoQuery.error && (
                <ResumoGastosMes totalAtual={totalAtual} totalAnterior={totalAnterior} />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-text-secondary">
                <Switch checked={comparar} onCheckedChange={setComparar} aria-label="Comparar com mês anterior" />
                Comparar com mês anterior
              </label>
              <MesAnoSeletor ano={periodo.ano} mes={periodo.mes} onSelecionar={(ano, mes) => setPeriodo({ ano, mes })} />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => navigate(`/relatorios?ano=${periodo.ano}&mes=${periodo.mes}`)}
              >
                <FileDown size={16} aria-hidden="true" />
                Baixar relatório
              </Button>
            </div>
          </div>
        </Card>

        <Card>
          <SectionTitle>Gastos por categoria</SectionTitle>
          {carregandoGastos ? (
            <LoadingCard lines={4} />
          ) : erroGastos ? (
            <>
              <ErrorMessage error={erroGastos} />
              <Button size="sm" variant="secondary" onClick={tentarNovamenteGastos} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : comparar ? (
            <GastosComparativoChart
              atual={(periodoQuery.data?.gastos_por_categoria ?? []).map((g) => ({ nome: g.categoria_nome, total: g.total }))}
              anterior={(periodoAnteriorQuery.data?.gastos_por_categoria ?? []).map((g) => ({
                nome: g.categoria_nome,
                total: g.total,
              }))}
              labelAtual={labelAtual}
              labelAnterior={labelAnterior}
            />
          ) : (
            <GastosPorCategoriaChart
              gastos={periodoQuery.data?.gastos_por_categoria ?? []}
              onSelecionarCategoria={irParaTransacoesPorCategoria}
            />
          )}
        </Card>

        <Card>
          <SectionTitle>Gastos por cartão</SectionTitle>
          {carregandoGastos ? (
            <LoadingCard lines={4} />
          ) : erroGastos ? (
            <>
              <ErrorMessage error={erroGastos} />
              <Button size="sm" variant="secondary" onClick={tentarNovamenteGastos} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : comparar ? (
            <GastosComparativoChart
              atual={(periodoQuery.data?.gastos_por_cartao ?? []).map((g) => ({ nome: g.cartao_nome, total: g.total }))}
              anterior={(periodoAnteriorQuery.data?.gastos_por_cartao ?? []).map((g) => ({
                nome: g.cartao_nome,
                total: g.total,
              }))}
              labelAtual={labelAtual}
              labelAnterior={labelAnterior}
            />
          ) : (
            <GastosPorCartaoChart gastos={periodoQuery.data?.gastos_por_cartao ?? []} onSelecionarCartao={irParaCartao} />
          )}
        </Card>

        <Card>
          <SectionTitle>Gastos por conta</SectionTitle>
          {carregandoGastos ? (
            <LoadingCard lines={4} />
          ) : erroGastos ? (
            <>
              <ErrorMessage error={erroGastos} />
              <Button size="sm" variant="secondary" onClick={tentarNovamenteGastos} className="mt-3">
                Tentar novamente
              </Button>
            </>
          ) : comparar ? (
            <GastosComparativoChart
              atual={(periodoQuery.data?.gastos_por_conta ?? []).map((g) => ({ nome: g.conta_nome, total: g.total }))}
              anterior={(periodoAnteriorQuery.data?.gastos_por_conta ?? []).map((g) => ({
                nome: g.conta_nome,
                total: g.total,
              }))}
              labelAtual={labelAtual}
              labelAnterior={labelAnterior}
            />
          ) : (
            <GastosPorContaChart gastos={periodoQuery.data?.gastos_por_conta ?? []} onSelecionarConta={irParaTransacoesPorConta} />
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
