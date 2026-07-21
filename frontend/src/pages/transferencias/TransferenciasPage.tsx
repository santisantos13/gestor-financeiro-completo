import { useMemo, useState } from "react";
import { ArrowLeftRight, Plus, Undo2 } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { DataTable } from "../../components/ui/DataTable";
import { ConfirmAction } from "../../components/ui/ConfirmAction";
import { Switch } from "../../components/ui/Switch";
import { TransferenciaFormDialog } from "../../components/domain/transferencia/TransferenciaFormDialog";
import { buildTransferenciaTableColumns } from "../../components/domain/transferencia/transferenciaTableColumns";
import { useTransferencias, useCancelarTransferencia } from "../../hooks/useTransferenciaQueries";
import { useContas } from "../../hooks/useContaQueries";
import { useToast } from "../../hooks/useToast";
import { getErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";
import type { TransferenciaRead } from "../../types/transferencia";
import type { RowAction } from "../../types/table";

/**
 * Página `/transferencias` — reaproveita 100% da infraestrutura já
 * existente (`DataTable`, `ConfirmAction`, `FormDialog` via
 * `TransferenciaFormDialog`), mesmo espírito de `/contas`/`/transacoes`. Ver
 * docs/analise-arquitetural-transferencias-frontend.md, seções 4, 6 e 8.
 *
 * "Mostrar transferências canceladas" espelha o "Mostrar inativas" de toda
 * outra entidade com soft delete — desabilitado por padrão (pedido
 * explícito do usuário).
 */
export function TransferenciasPage() {
  const toast = useToast();
  const [mostrarCanceladas, setMostrarCanceladas] = useState(false);
  const { data: transferencias, isLoading, error, refetch } = useTransferencias(!mostrarCanceladas);
  // apenasAtivas=false: uma transferência antiga pode referenciar uma conta
  // hoje inativa — precisamos do nome dela mesmo assim (mesmo raciocínio já
  // usado em TransacaoFormDialog ao editar).
  const { data: contas } = useContas(false);

  const [formularioAberto, setFormularioAberto] = useState(false);
  const [transferenciaParaCancelar, setTransferenciaParaCancelar] = useState<TransferenciaRead | null>(null);
  const cancelarTransferencia = useCancelarTransferencia(
    transferenciaParaCancelar?.conta_origem_id,
    transferenciaParaCancelar?.conta_destino_id,
  );

  const contasPorId = useMemo(() => new Map((contas ?? []).map((c) => [c.id, c])), [contas]);
  const columns = useMemo(() => buildTransferenciaTableColumns({ contasPorId }), [contasPorId]);

  async function confirmarCancelamento() {
    if (!transferenciaParaCancelar) return;
    try {
      await cancelarTransferencia.mutateAsync(transferenciaParaCancelar.id);
      toast.success(`Transferência de ${formatMoney(transferenciaParaCancelar.valor)} cancelada.`);
      setTransferenciaParaCancelar(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  const rowActions: RowAction<TransferenciaRead>[] = [
    {
      // Nunca "Excluir" — o backend não tem exclusão física de
      // Transferência (só soft cancel), e o rótulo precisa deixar isso
      // claro (seção 8, ponto 4 da análise).
      label: "Cancelar transferência",
      icon: Undo2,
      tone: "danger",
      onClick: (transferencia) => setTransferenciaParaCancelar(transferencia),
      hidden: (transferencia) => !transferencia.ativo,
    },
  ];

  const origemCancelamento = transferenciaParaCancelar
    ? contasPorId.get(transferenciaParaCancelar.conta_origem_id)?.nome
    : undefined;
  const destinoCancelamento = transferenciaParaCancelar
    ? contasPorId.get(transferenciaParaCancelar.conta_destino_id)?.nome
    : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Transferências</h1>
          <p className="mt-1 text-sm text-text-secondary">Movimentações de dinheiro entre suas contas.</p>
        </div>
        <Button onClick={() => setFormularioAberto(true)}>
          <Plus size={16} aria-hidden="true" />
          Nova transferência
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="mostrar-canceladas"
          checked={mostrarCanceladas}
          onCheckedChange={setMostrarCanceladas}
          aria-label="Mostrar transferências canceladas"
        />
        <label htmlFor="mostrar-canceladas" className="cursor-pointer text-sm text-text-secondary">
          Mostrar transferências canceladas
        </label>
      </div>

      <DataTable
        data={transferencias ?? []}
        columns={columns}
        getRowId={(transferencia) => transferencia.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        searchable
        searchPlaceholder="Buscar por descrição..."
        rowActions={rowActions}
        emptyIcon={ArrowLeftRight}
        emptyTitle="Nenhuma transferência ainda"
        emptyAction={
          !transferencias || transferencias.length === 0 ? (
            <Button size="sm" onClick={() => setFormularioAberto(true)}>
              <Plus size={14} aria-hidden="true" />
              Nova transferência
            </Button>
          ) : undefined
        }
        emptyDescription="Mova dinheiro entre suas contas com o botão acima."
        aria-label="Transferências"
      />

      <TransferenciaFormDialog open={formularioAberto} onClose={() => setFormularioAberto(false)} />

      <ConfirmAction
        open={transferenciaParaCancelar != null}
        title={transferenciaParaCancelar ? `Cancelar transferência de ${formatMoney(transferenciaParaCancelar.valor)}?` : ""}
        description={
          origemCancelamento && destinoCancelamento
            ? `A movimentação de "${origemCancelamento}" para "${destinoCancelamento}" será revertida: o valor volta a contar no saldo de "${origemCancelamento}" e deixa de contar no de "${destinoCancelamento}". O histórico desta transferência é preservado, só marcada como cancelada.`
            : "A movimentação será revertida nos saldos das duas contas. O histórico é preservado, só marcado como cancelado."
        }
        confirmLabel="Cancelar transferência"
        tone="danger"
        loading={cancelarTransferencia.isPending}
        onConfirm={confirmarCancelamento}
        onCancel={() => setTransferenciaParaCancelar(null)}
      />
    </div>
  );
}
