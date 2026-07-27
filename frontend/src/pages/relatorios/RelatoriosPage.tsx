import { useState } from "react";
import { FileDown, Table } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Button } from "../../components/ui/Button";
import { MesAnoSeletor } from "../../components/domain/calendario/MesAnoSeletor";
import { useVisaoMensalQuery, useGraficosPeriodoQuery } from "../../hooks/useCentralFinanceiraQueries";
import { useBaixarRelatorioCsv, useBaixarRelatorioPdf } from "../../hooks/useRelatorioQueries";
import { useToast } from "../../hooks/useToast";
import { baixarBlob } from "../../utils/download";
import { getErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";

/**
 * Página `/relatorios` — módulo "Relatórios" do roadmap. Escopo decidido
 * (não um pedido literal do usuário - "export + tela" era vago): exporta
 * o MESMO resumo de um mês que a página `/graficos` já exibe em tela
 * (`useVisaoMensalQuery`/`useGraficosPeriodoQuery`, mesmos hooks, mesmo
 * cache - nenhum fetch novo aqui além do que já existe), em dois formatos
 * de arquivo (CSV para planilha, PDF para leitura/impressão). Nenhum
 * cálculo novo em lugar nenhum (frontend ou backend) - só reaproveita
 * `CentralFinanceiraService.visao_mensal`/`graficos_periodo`, ver
 * docs/analise-arquitetural-relatorios.md.
 *
 * O preview em tela (mesmos números que o arquivo baixado vai conter)
 * existe para o usuário confirmar ANTES de baixar - nenhum download é
 * "às cegas".
 */
export function RelatoriosPage() {
  const hoje = new Date();
  const [periodo, setPeriodo] = useState({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });
  const toast = useToast();

  const visao = useVisaoMensalQuery(periodo.ano, periodo.mes);
  const periodoQuery = useGraficosPeriodoQuery(periodo.ano, periodo.mes);
  const baixarCsv = useBaixarRelatorioCsv();
  const baixarPdf = useBaixarRelatorioPdf();

  async function handleBaixarCsv() {
    try {
      const { blob, nomeArquivo } = await baixarCsv.mutateAsync(periodo);
      baixarBlob(blob, nomeArquivo);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function handleBaixarPdf() {
    try {
      const { blob, nomeArquivo } = await baixarPdf.mutateAsync(periodo);
      baixarBlob(blob, nomeArquivo);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-h1 font-semibold text-text-primary">Relatórios</h1>
        <p className="mt-1 text-sm text-text-secondary">Exporte o resumo financeiro de um mês em CSV ou PDF.</p>
      </header>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SectionTitle>Resumo do período</SectionTitle>
          <MesAnoSeletor ano={periodo.ano} mes={periodo.mes} onSelecionar={(ano, mes) => setPeriodo({ ano, mes })} />
        </div>

        {visao.isLoading ? (
          <LoadingCard lines={3} />
        ) : visao.error ? (
          <>
            <ErrorMessage error={visao.error} />
            <Button size="sm" variant="secondary" onClick={() => visao.refetch()} className="mt-3">
              Tentar novamente
            </Button>
          </>
        ) : (
          <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <dt className="text-sm text-text-tertiary">Entradas</dt>
              <dd className="tabular text-h3 font-semibold text-positive">{formatMoney(visao.data?.entradas ?? 0)}</dd>
            </div>
            <div>
              <dt className="text-sm text-text-tertiary">Saídas</dt>
              <dd className="tabular text-h3 font-semibold text-negative">{formatMoney(visao.data?.saidas ?? 0)}</dd>
            </div>
            <div>
              <dt className="text-sm text-text-tertiary">Saldo do mês</dt>
              <dd className="tabular text-h3 font-semibold text-text-primary">
                {formatMoney(visao.data?.fluxo_caixa ?? 0)}
              </dd>
            </div>
          </dl>
        )}

        {!periodoQuery.isLoading && !periodoQuery.error && (
          <p className="mt-4 text-caption text-text-tertiary">
            {(periodoQuery.data?.gastos_por_categoria.length ?? 0) +
              (periodoQuery.data?.gastos_por_cartao.length ?? 0) +
              (periodoQuery.data?.gastos_por_conta.length ?? 0) >
            0
              ? "O arquivo exportado inclui também os gastos por categoria, cartão e conta deste mês."
              : "Nenhum gasto por categoria, cartão ou conta neste mês."}
          </p>
        )}
      </Card>

      <Card>
        <SectionTitle>Baixar relatório</SectionTitle>
        <p className="mt-1 text-sm text-text-secondary">
          Mesmos dados exibidos acima - entradas, saídas, saldo e os agrupamentos de gastos do mês selecionado.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button variant="secondary" onClick={handleBaixarCsv} loading={baixarCsv.isPending}>
            <Table size={16} aria-hidden="true" />
            Baixar CSV
          </Button>
          <Button onClick={handleBaixarPdf} loading={baixarPdf.isPending}>
            <FileDown size={16} aria-hidden="true" />
            Baixar PDF
          </Button>
        </div>
      </Card>
    </div>
  );
}
