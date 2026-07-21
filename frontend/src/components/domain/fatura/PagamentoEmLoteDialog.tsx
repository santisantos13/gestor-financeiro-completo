import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { CancelButton } from "../../ui/CancelButton";
import { SubmitButton } from "../../ui/SubmitButton";
import { DateField } from "../../ui/DateField";
import { usePagarFaturasEmLote } from "../../../hooks/useFaturaQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage } from "../../../utils/errors";
import {
  pagamentoEmLoteFormSchema,
  pagamentoEmLoteFormValuesParaPayload,
  type PagamentoEmLoteFormValues,
} from "../../../schemas/fatura";

export interface PagamentoEmLoteDialogProps {
  open: boolean;
  cartaoId: number;
  /** `Cartao.conta_pagamento_id` — mesma necessidade de invalidação de
   * `FaturaDrawer` (o pagamento cria uma `Transacao` de despesa nessa
   * conta). */
  contaPagamentoId?: number | null;
  /** Ids capturados no momento em que o usuário clicou em "Pagar
   * selecionadas" (`BulkActions` já entrega `selectedRows` no clique) —
   * não reage a mudanças de seleção depois que o diálogo abre. */
  faturaIds: number[];
  onClose: () => void;
}

const VALORES_VAZIOS: PagamentoEmLoteFormValues = { data: "" };

/**
 * Pedido explícito do usuário (2026-07-20): "só tem como excluir as
 * faturas ao selecionar todas ou várias, seria interessante poder pagar
 * todas selecionadas" — mesma seleção múltipla já usada para exclusão em
 * lote (`CartaoDetalhePage`), agora com uma ação de pagamento.
 *
 * Só pede a DATA do pagamento — nunca um valor único: cada fatura
 * selecionada é paga pelo seu próprio restante (mesmo atalho "Pagar
 * restante" do `FaturaDrawer`, só que aplicado a N faturas de uma vez),
 * calculado pelo backend (`FaturaService.pagar_em_lote`). Faturas ainda
 * ABERTAS ou já quitadas dentro da seleção são puladas automaticamente
 * (nunca bloqueiam o lote inteiro) — o toast de sucesso avisa quando nem
 * toda a seleção foi processada.
 */
export function PagamentoEmLoteDialog({
  open,
  cartaoId,
  contaPagamentoId,
  faturaIds,
  onClose,
}: PagamentoEmLoteDialogProps) {
  const toast = useToast();
  const pagarEmLote = usePagarFaturasEmLote(cartaoId, contaPagamentoId);

  const form = useForm<PagamentoEmLoteFormValues>({
    resolver: zodResolver(pagamentoEmLoteFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      // Data de hoje já preenchida — no caso comum (pagou tudo agora) o
      // usuário só confirma, sem precisar digitar nada.
      form.reset({ data: new Date().toISOString().slice(0, 10) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function onSubmit(valores: PagamentoEmLoteFormValues) {
    try {
      const resultado = await pagarEmLote.mutateAsync(
        pagamentoEmLoteFormValuesParaPayload(valores, faturaIds),
      );
      if (resultado.pagas === faturaIds.length) {
        toast.success(
          resultado.pagas === 1 ? "Fatura paga." : `${resultado.pagas} faturas pagas.`,
        );
      } else {
        toast.success(
          `${resultado.pagas} de ${faturaIds.length} faturas pagas — as demais já estavam ` +
            "quitadas ou ainda estão abertas.",
        );
      }
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title="Pagar faturas selecionadas"
      description={`Registra o pagamento do valor restante de cada uma das ${faturaIds.length} fatura(s) selecionada(s), na mesma data. Faturas ainda abertas ou já quitadas são puladas automaticamente.`}
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="pagamento-em-lote-form" loading={pagarEmLote.isPending}>
            Pagar selecionadas
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="pagamento-em-lote-form" form={form} onSubmit={onSubmit} className="space-y-4">
        <DateField name="data" label="Data do pagamento" />
      </Form>
    </FormDialog>
  );
}
