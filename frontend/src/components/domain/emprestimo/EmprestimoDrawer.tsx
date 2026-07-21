import { useState } from "react";
import { AlertTriangle, Pencil, Trash2 } from "lucide-react";
import { Drawer } from "../../ui/Drawer";
import { Button } from "../../ui/Button";
import { FinancialBadge } from "../../ui/FinancialBadge";
import { ProgressBar } from "../../ui/ProgressBar";
import { Skeleton } from "../../ui/Skeleton";
import { ParcelaContratoEditForm } from "../transacao/ParcelaContratoEditForm";
import {
  useEmprestimo,
  useParcelasEmprestimo,
  usePagarParcelaEmprestimo,
  useExcluirEmprestimo,
} from "../../../hooks/useEmprestimoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage } from "../../../utils/errors";
import { formatMoney, formatPercent } from "../../../utils/format";
import { formatDate } from "../../../utils/date";
import type { TransacaoRead } from "../../../types/transacao";

export interface EmprestimoDrawerProps {
  emprestimoId: number | null;
  onClose: () => void;
}

/** Drawer de cronograma de UM Empréstimo — mesma estrutura de
 * `FinanciamentoDrawer.tsx` (ver docstring lá para o raciocínio completo,
 * incluindo a confirmação de exclusão inline e o formulário de correção de
 * parcela, ambos substituindo o conteúdo do Drawer em vez de `ConfirmAction`/
 * `FormDialog` por cima). */
export function EmprestimoDrawer({ emprestimoId, onClose }: EmprestimoDrawerProps) {
  const toast = useToast();
  const { data: emprestimo, isLoading } = useEmprestimo(emprestimoId);
  const { data: parcelas, isLoading: carregandoParcelas } = useParcelasEmprestimo(emprestimoId);
  const pagarParcela = usePagarParcelaEmprestimo();
  const excluirEmprestimo = useExcluirEmprestimo();

  const [confirmandoExcluir, setConfirmandoExcluir] = useState(false);
  const [parcelaEmEdicao, setParcelaEmEdicao] = useState<TransacaoRead | null>(null);

  async function pagar(numeroParcela: number) {
    if (!emprestimoId) return;
    try {
      await pagarParcela.mutateAsync({ id: emprestimoId, numeroParcela });
      toast.success(`Parcela ${numeroParcela} paga.`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExcluir() {
    if (!emprestimoId || !emprestimo) return;
    try {
      await excluirEmprestimo.mutateAsync({ id: emprestimoId, contaId: emprestimo.conta_id });
      toast.success(`Empréstimo "${emprestimo.descricao}" excluído.`);
      setConfirmandoExcluir(false);
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  const parcelasComNumero = parcelas?.filter((p) => p.numero_parcela != null) ?? [];
  const parcelasPagas = parcelasComNumero.filter((p) => p.status === "PAGO").length;
  const totalPago = parcelasComNumero
    .filter((p) => p.status === "PAGO")
    .reduce((soma, p) => soma + Number(p.valor), 0);
  const progresso = emprestimo ? (parcelasPagas / emprestimo.num_parcelas) * 100 : 0;

  return (
    <Drawer open={emprestimoId != null} title={emprestimo?.descricao ?? "Empréstimo"} onClose={onClose}>
      {isLoading || !emprestimo ? (
        <div className="space-y-3">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : parcelaEmEdicao ? (
        <ParcelaContratoEditForm
          parcela={parcelaEmEdicao}
          onSalvo={() => setParcelaEmEdicao(null)}
          onCancelar={() => setParcelaEmEdicao(null)}
        />
      ) : confirmandoExcluir ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-negative-subtle">
              <AlertTriangle size={16} className="text-negative" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="text-h3 font-semibold text-text-primary">Excluir este empréstimo?</h3>
              <p className="mt-1 text-sm text-text-secondary">
                Esta ação é permanente. As parcelas já lançadas (pagas ou não) não são apagadas — só
                perdem o vínculo com este empréstimo e viram transações avulsas comuns na conta.
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setConfirmandoExcluir(false)}>
              Cancelar
            </Button>
            <Button variant="danger" size="sm" loading={excluirEmprestimo.isPending} onClick={confirmarExcluir}>
              Excluir
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <FinancialBadge status={emprestimo.status} />
            <span className="text-sm text-text-tertiary">{emprestimo.instituicao_financeira}</span>
          </div>

          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-caption text-text-tertiary">Saldo devedor</dt>
              <dd className="font-mono tabular text-text-primary">{formatMoney(emprestimo.saldo_devedor)}</dd>
            </div>
            <div>
              <dt className="text-caption text-text-tertiary">Taxa de juros</dt>
              <dd className="font-mono tabular text-text-primary">
                {formatPercent(Number(emprestimo.taxa_juros) * 100)} a.m.
              </dd>
            </div>
            <div>
              <dt className="text-caption text-text-tertiary">Sistema</dt>
              <dd className="text-text-primary">{emprestimo.sistema_amortizacao}</dd>
            </div>
            <div>
              <dt className="text-caption text-text-tertiary">Início</dt>
              <dd className="text-text-primary">{formatDate(emprestimo.data_inicio)}</dd>
            </div>
          </dl>

          <div>
            <ProgressBar
              value={progresso}
              aria-label={`${parcelasPagas} de ${emprestimo.num_parcelas} parcelas pagas`}
            />
            <p className="mt-1 text-caption text-text-tertiary">
              {parcelasPagas}/{emprestimo.num_parcelas} parcelas pagas · {formatMoney(totalPago)} já pago
            </p>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Cronograma</p>
            {carregandoParcelas ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <ul className="max-h-80 space-y-1.5 overflow-y-auto pr-1">
                {parcelasComNumero
                  .slice()
                  .sort((a, b) => (a.numero_parcela ?? 0) - (b.numero_parcela ?? 0))
                  .map((parcela) => (
                    <li
                      key={parcela.id}
                      className="flex items-center justify-between rounded-md border border-border bg-surface-2 px-3 py-2 text-sm"
                    >
                      <span className="text-text-secondary">
                        {parcela.numero_parcela}/{emprestimo.num_parcelas} · {formatDate(parcela.data)}
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="font-mono tabular text-text-primary">{formatMoney(parcela.valor)}</span>
                        {parcela.status === "PAGO" ? (
                          <FinancialBadge status="PAGO" />
                        ) : (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={pagarParcela.isPending}
                            onClick={() => pagar(parcela.numero_parcela as number)}
                          >
                            Pagar
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label={`Corrigir parcela ${parcela.numero_parcela}`}
                          onClick={() => setParcelaEmEdicao(parcela)}
                        >
                          <Pencil size={14} aria-hidden="true" />
                        </Button>
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="w-full hover:text-negative"
            onClick={() => setConfirmandoExcluir(true)}
          >
            <Trash2 size={14} aria-hidden="true" />
            Excluir empréstimo
          </Button>
        </div>
      )}
    </Drawer>
  );
}
