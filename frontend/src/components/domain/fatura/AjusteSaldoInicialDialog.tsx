import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { CancelButton } from "../../ui/CancelButton";
import { SubmitButton } from "../../ui/SubmitButton";
import { CurrencyField } from "../../ui/CurrencyField";
import { useAjustarSaldoInicialFatura } from "../../../hooks/useFaturaQueries";
import { useAtualizarCartao } from "../../../hooks/useCartaoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import {
  ajusteSaldoInicialFormSchema,
  ajusteSaldoInicialFormValuesParaPayload,
  type AjusteSaldoInicialFormValues,
} from "../../../schemas/fatura";
import type { CartaoRead } from "../../../types/cartao";
import type { FaturaRead } from "../../../types/fatura";

const VALORES_VAZIOS: AjusteSaldoInicialFormValues = { ajuste_manual: "" };

export interface AjusteSaldoInicialDialogProps {
  open: boolean;
  cartao: CartaoRead;
  /** Fatura ABERTA atual do cartão, se já existir (`CartaoDetalhePage`
   * resolve isso a partir de `useFaturas`). */
  faturaAberta: FaturaRead | null | undefined;
  onClose: () => void;
}

/**
 * Pedido explícito do usuário: "faltou a opção do usuário poder informar
 * o saldo já utilizado do cartão independentemente de transações".
 *
 * Redesenhado na Sprint de Refinamento Premium (2026-07,
 * docs/analise-arquitetural-sprint-refinamento-premium.md, seção 1): a
 * versão anterior, quando não havia nenhuma fatura ABERTA (o caso comum de
 * um cartão recém-criado), criava uma silenciosamente só para poder
 * gravar `Fatura.ajuste_manual` — confuso para o usuário ("o sistema criou
 * uma fatura sozinho"). Agora esse caso edita `Cartao.saldo_inicial_utilizado`
 * diretamente (`PATCH /cartoes/{id}`), sem NENHUMA Fatura envolvida —
 * "Estado Inicial do Cartão", puramente um número no próprio Cartão.
 *
 * Quando já existe um ciclo ABERTO, o comportamento é o de sempre: ajusta
 * `Fatura.ajuste_manual` daquele ciclo (`PATCH /faturas/{id}/ajuste-manual`,
 * `FaturaService.ajustar_saldo_inicial`) — um uso diferente e ainda válido
 * (bater o saldo do ciclo corrente), não mais usado como mecanismo de
 * onboarding.
 */
export function AjusteSaldoInicialDialog({ open, cartao, faturaAberta, onClose }: AjusteSaldoInicialDialogProps) {
  const toast = useToast();
  const ajustarSaldoFatura = useAjustarSaldoInicialFatura(cartao.id);
  const atualizarCartao = useAtualizarCartao();
  const editandoFatura = faturaAberta != null;
  const salvando = ajustarSaldoFatura.isPending || atualizarCartao.isPending;

  const form = useForm<AjusteSaldoInicialFormValues>({
    resolver: zodResolver(ajusteSaldoInicialFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      const valorAtual = editandoFatura ? faturaAberta?.ajuste_manual : cartao.saldo_inicial_utilizado;
      form.reset({ ajuste_manual: valorAtual ?? "" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, editandoFatura, faturaAberta, cartao.saldo_inicial_utilizado]);

  async function onSubmit(valores: AjusteSaldoInicialFormValues) {
    try {
      if (editandoFatura && faturaAberta) {
        await ajustarSaldoFatura.mutateAsync({
          id: faturaAberta.id,
          dados: ajusteSaldoInicialFormValuesParaPayload(valores),
        });
      } else {
        await atualizarCartao.mutateAsync({
          id: cartao.id,
          dados: { saldo_inicial_utilizado: valores.ajuste_manual || "0" },
        });
      }
      toast.success("Saldo já utilizado atualizado.");
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof AjusteSaldoInicialFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title="Informar saldo já utilizado"
      description={
        editandoFatura
          ? "Diga quanto já está gasto no ciclo atual deste cartão — sem precisar lançar cada compra separadamente. Esse valor entra direto no limite disponível, sem criar nenhuma transação."
          : "Diga quanto do limite deste cartão já estava em uso — sem precisar lançar cada compra separadamente e sem criar nenhuma fatura. Esse valor entra direto no limite disponível."
      }
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="ajuste-saldo-inicial-form" loading={salvando}>
            Salvar
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="ajuste-saldo-inicial-form" form={form} onSubmit={onSubmit} className="space-y-4">
        <CurrencyField name="ajuste_manual" label="Saldo já utilizado" />
      </Form>
    </FormDialog>
  );
}
