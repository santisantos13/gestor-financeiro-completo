import { useState } from "react";
import { Banknote, Plus } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { FinancialBadge } from "../../components/ui/FinancialBadge";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { EmprestimoFormDialog } from "../../components/domain/emprestimo/EmprestimoFormDialog";
import { EmprestimoDrawer } from "../../components/domain/emprestimo/EmprestimoDrawer";
import { useEmprestimos } from "../../hooks/useEmprestimoQueries";
import { formatMoney } from "../../utils/format";
import type { EmprestimoRead } from "../../types/emprestimo";

/** Página `/emprestimos` — mesma estrutura de `FinanciamentosPage.tsx`
 * (ver docstring lá para o raciocínio completo). */
export function EmprestimosPage() {
  const [mostrarQuitados, setMostrarQuitados] = useState(false);
  const { data: emprestimos, isLoading, error, refetch } = useEmprestimos(!mostrarQuitados);

  const [formularioAberto, setFormularioAberto] = useState(false);
  const [emprestimoSelecionadoId, setEmprestimoSelecionadoId] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Empréstimos</h1>
          <p className="mt-1 text-sm text-text-secondary">Empréstimos pessoais e outros valores tomados.</p>
        </div>
        <Button onClick={() => setFormularioAberto(true)}>
          <Plus size={16} aria-hidden="true" />
          Novo empréstimo
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="mostrar-quitados-emprestimos"
          checked={mostrarQuitados}
          onCheckedChange={setMostrarQuitados}
          aria-label="Mostrar empréstimos quitados"
        />
        <label htmlFor="mostrar-quitados-emprestimos" className="cursor-pointer text-sm text-text-secondary">
          Mostrar quitados
        </label>
      </div>

      {error ? (
        <Card>
          <ErrorMessage error={error} />
          <Button size="sm" variant="secondary" onClick={() => refetch()} className="mt-3">
            Tentar novamente
          </Button>
        </Card>
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i} className="space-y-3">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-2 w-full" />
            </Card>
          ))}
        </div>
      ) : !emprestimos || emprestimos.length === 0 ? (
        <Card>
          <EmptyState
            icon={Banknote}
            title="Nenhum empréstimo ainda"
            description="Cadastre um empréstimo em andamento (ou já em dia) para acompanhar o saldo devedor aqui."
            action={
              <Button size="sm" onClick={() => setFormularioAberto(true)}>
                <Plus size={14} aria-hidden="true" />
                Novo empréstimo
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {emprestimos.map((emprestimo: EmprestimoRead) => (
            <Card
              key={emprestimo.id}
              role="link"
              tabIndex={0}
              onClick={() => setEmprestimoSelecionadoId(emprestimo.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setEmprestimoSelecionadoId(emprestimo.id);
                }
              }}
              aria-label={`Ver detalhes de ${emprestimo.descricao}`}
              className="cursor-pointer space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-text-primary">{emprestimo.descricao}</p>
                  <p className="truncate text-caption text-text-tertiary">{emprestimo.instituicao_financeira}</p>
                </div>
                <FinancialBadge status={emprestimo.status} />
              </div>
              <div>
                <p className="text-caption text-text-tertiary">Saldo devedor</p>
                <p className="font-mono tabular text-h3 font-semibold text-text-primary">
                  {formatMoney(emprestimo.saldo_devedor)}
                </p>
              </div>
              <p className="text-caption text-text-tertiary">{emprestimo.num_parcelas} parcelas no total</p>
            </Card>
          ))}
        </div>
      )}

      <EmprestimoFormDialog open={formularioAberto} onClose={() => setFormularioAberto(false)} />

      <EmprestimoDrawer emprestimoId={emprestimoSelecionadoId} onClose={() => setEmprestimoSelecionadoId(null)} />
    </div>
  );
}
