import type { KeyboardEvent } from "react";
import { Banknote } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "../../ui/Card";
import { SectionTitle } from "../../ui/SectionTitle";
import { LoadingCard } from "../../ui/LoadingCard";
import { ErrorMessage } from "../../ui/ErrorMessage";
import { Button } from "../../ui/Button";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { ProgressBar } from "../../ui/ProgressBar";
import { formatMoney } from "../../../utils/format";
import { useEmprestimosQuery } from "../../../hooks/useCentralFinanceiraQueries";

/** `/central-financeira/emprestimos` — mesma estrutura de
 * `FinanciamentosCard` (seção 3.1 do doc: `EmprestimoResumo` tem a mesma
 * forma de `FinanciamentoResumo`). Some se `emprestimos.length === 0`
 * (seção 10). Card inteiro clicável (navega para `/emprestimos`, Sprint
 * de Refinamento Premium item 12). */
export function EmprestimosCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useEmprestimosQuery();

  if (isLoading) return <LoadingCard lines={3} />;

  if (error) {
    return (
      <Card>
        <SectionTitle>Empréstimos</SectionTitle>
        <ErrorMessage error={error} />
        <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  if (!data || data.emprestimos.length === 0) return null;

  function abrirEmprestimos() {
    navigate("/emprestimos");
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      abrirEmprestimos();
    }
  }

  return (
    <Card
      role="link"
      tabIndex={0}
      onClick={abrirEmprestimos}
      onKeyDown={onKeyDown}
      aria-label="Ver empréstimos"
      className="cursor-pointer"
    >
      <SectionTitle>Empréstimos</SectionTitle>
      <ul className="space-y-4">
        {data.emprestimos.map((emprestimo) => {
          const progresso = (emprestimo.parcelas_pagas / emprestimo.num_parcelas) * 100;
          return (
            <li key={emprestimo.id}>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-text-primary">
                  <Banknote size={14} className="text-text-tertiary" aria-hidden="true" />
                  {emprestimo.descricao}
                </span>
                <FinancialBadge status={emprestimo.status} />
              </div>
              <p className="mt-1 text-caption text-text-tertiary">
                Saldo devedor:{" "}
                <span className="tabular text-text-secondary">{formatMoney(emprestimo.saldo_devedor)}</span>
              </p>
              <ProgressBar
                value={progresso}
                className="mt-2"
                aria-label={`${emprestimo.parcelas_pagas} de ${emprestimo.num_parcelas} parcelas pagas`}
              />
              <p className="mt-1 text-caption text-text-tertiary">
                {emprestimo.parcelas_pagas}/{emprestimo.num_parcelas} parcelas
                {emprestimo.proxima_parcela_data && emprestimo.proxima_parcela_valor
                  ? ` · próxima: ${formatMoney(emprestimo.proxima_parcela_valor)}`
                  : ""}
              </p>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
