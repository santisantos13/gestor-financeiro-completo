import { MetricCard } from "../../ui/MetricCard";
import { Skeleton } from "../../ui/Skeleton";
import { formatMoney } from "../../../utils/format";
import { useVisaoMensalQuery } from "../../../hooks/useCentralFinanceiraQueries";

export interface TransacaoResumoPeriodoProps {
  ano: number;
  mes: number;
}

/**
 * Faixa de resumo do período acima da tabela de `/transacoes` — reaproveita
 * `GET /central-financeira/visao-mensal` (`useVisaoMensalQuery`, já usado
 * pelo Dashboard em `ResumoFinanceiroSection`) em vez de somar as transações
 * já carregadas no cliente: o backend já expõe exatamente
 * `entradas`/`saidas`/`fluxo_caixa` do mês, e somar de novo no cliente
 * duplicaria uma agregação que já existe (mesmo raciocínio de
 * `TransacaoRepository.somar_por_periodo` preferir `SUM` no banco a somar
 * em Python). Ver docs/analise-arquitetural-transacao-frontend.md, seção
 * 10.
 */
export function TransacaoResumoPeriodo({ ano, mes }: TransacaoResumoPeriodoProps) {
  const { data, isLoading } = useVisaoMensalQuery(ano, mes);

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-md" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <MetricCard label="Receitas do período" value={formatMoney(data.entradas)} className="border-positive/30" />
      <MetricCard label="Despesas do período" value={formatMoney(data.saidas)} className="border-negative/30" />
      <MetricCard label="Saldo do período" value={formatMoney(data.fluxo_caixa)} />
    </div>
  );
}
