import { useState } from "react";
import { Home, Plus } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { FinancialBadge } from "../../components/ui/FinancialBadge";
import { Skeleton } from "../../components/ui/Skeleton";
import { Switch } from "../../components/ui/Switch";
import { FinanciamentoFormDialog } from "../../components/domain/financiamento/FinanciamentoFormDialog";
import { FinanciamentoDrawer } from "../../components/domain/financiamento/FinanciamentoDrawer";
import { useFinanciamentos } from "../../hooks/useFinanciamentoQueries";
import { formatMoney } from "../../utils/format";
import type { FinanciamentoRead } from "../../types/financiamento";

/**
 * Página `/financiamentos` — Etapa de Onboarding. Grid de cards clicáveis
 * (mesmo espírito de `CartoesPage`), cada um abrindo `FinanciamentoDrawer`
 * (cronograma completo + ação de pagar parcela). Sem edição/exclusão: o
 * backend não tem `Update`/`DELETE` para Financiamento (campos estruturais
 * imutáveis — ver docstring de `types/financiamento.ts`).
 *
 * "Mostrar quitados" desabilitado por padrão, mesmo espírito de "Mostrar
 * inativos"/"Mostrar canceladas" de toda entidade com estado terminal —
 * um contrato QUITADO não precisa de atenção contínua.
 */
export function FinanciamentosPage() {
  const [mostrarQuitados, setMostrarQuitados] = useState(false);
  const { data: financiamentos, isLoading, error, refetch } = useFinanciamentos(!mostrarQuitados);

  const [formularioAberto, setFormularioAberto] = useState(false);
  const [financiamentoSelecionadoId, setFinanciamentoSelecionadoId] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Financiamentos</h1>
          <p className="mt-1 text-sm text-text-secondary">Imóveis, veículos e outros contratos de crédito.</p>
        </div>
        <Button onClick={() => setFormularioAberto(true)}>
          <Plus size={16} aria-hidden="true" />
          Novo financiamento
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="mostrar-quitados"
          checked={mostrarQuitados}
          onCheckedChange={setMostrarQuitados}
          aria-label="Mostrar financiamentos quitados"
        />
        <label htmlFor="mostrar-quitados" className="cursor-pointer text-sm text-text-secondary">
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
      ) : !financiamentos || financiamentos.length === 0 ? (
        <Card>
          <EmptyState
            icon={Home}
            title="Nenhum financiamento ainda"
            description="Cadastre um financiamento em andamento (ou já em dia) para acompanhar o saldo devedor aqui."
            action={
              <Button size="sm" onClick={() => setFormularioAberto(true)}>
                <Plus size={14} aria-hidden="true" />
                Novo financiamento
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {financiamentos.map((financiamento: FinanciamentoRead) => (
            <Card
              key={financiamento.id}
              role="link"
              tabIndex={0}
              onClick={() => setFinanciamentoSelecionadoId(financiamento.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setFinanciamentoSelecionadoId(financiamento.id);
                }
              }}
              aria-label={`Ver detalhes de ${financiamento.descricao}`}
              className="cursor-pointer space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-text-primary">{financiamento.descricao}</p>
                  <p className="truncate text-caption text-text-tertiary">{financiamento.instituicao_financeira}</p>
                </div>
                <FinancialBadge status={financiamento.status} />
              </div>
              <div>
                <p className="text-caption text-text-tertiary">Saldo devedor</p>
                <p className="font-mono tabular text-h3 font-semibold text-text-primary">
                  {formatMoney(financiamento.saldo_devedor)}
                </p>
              </div>
              <p className="text-caption text-text-tertiary">{financiamento.num_parcelas} parcelas no total</p>
            </Card>
          ))}
        </div>
      )}

      <FinanciamentoFormDialog open={formularioAberto} onClose={() => setFormularioAberto(false)} />

      <FinanciamentoDrawer
        financiamentoId={financiamentoSelecionadoId}
        onClose={() => setFinanciamentoSelecionadoId(null)}
      />
    </div>
  );
}
