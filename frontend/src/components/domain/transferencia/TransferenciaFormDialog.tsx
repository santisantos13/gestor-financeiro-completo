import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "motion/react";
import { ArrowRight, ArrowLeftRight } from "lucide-react";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { TextField } from "../../ui/TextField";
import { CurrencyField } from "../../ui/CurrencyField";
import { DateField } from "../../ui/DateField";
import { AccountSelect } from "../conta/AccountSelect";
import {
  transferenciaFormSchema,
  transferenciaFormValuesParaCriacao,
  TRANSFERENCIA_VALORES_VAZIOS,
  type TransferenciaFormValues,
} from "../../../schemas/transferencia";
import { useCriarTransferencia } from "../../../hooks/useTransferenciaQueries";
import { useContas } from "../../../hooks/useContaQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import { formatMoney } from "../../../utils/format";
import { fadeIn, EASE, DURATION } from "../../../lib/motion";

export interface TransferenciaFormDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Modal de criação de Transferência — diferente de todo `*FormDialog`
 * anterior, o objetivo explícito (docs/analise-arquitetural-transferencias-frontend.md,
 * seção 7) é comunicar "mover dinheiro entre contas", não só validar
 * campos. Sem modo edição (o backend não tem `TransferenciaUpdate` — ver
 * `types/transferencia.ts`), então este componente só cria.
 *
 * Três elementos específicos desta entidade:
 *
 * 1. Origem/destino lado a lado com uma seta entre eles — `excluirId`
 *    (`AccountSelect`, seção nova) impede escolher a mesma conta nos dois
 *    campos pela UI; o botão de trocar (`ArrowLeftRight`) inverte os dois
 *    valores sem reabrir os dropdowns.
 * 2. A seta anima só em 4 momentos permitidos (nunca em loop infinito):
 *    entrada (fadeIn no mount), hover (CSS `group-hover`, sem JS), durante
 *    o salvamento (`animate-pulse`, que para sozinho quando a mutation
 *    resolve — bounded, não é um loop eterno) e na confirmação (o preview
 *    ganha um pulso de fundo ao virar válido, motion-principles.md, seção
 *    6.2 — "pulso de fundo" para mudança de valor, nunca um re-count-up).
 * 3. Preview da movimentação — só renderiza quando origem+destino+valor já
 *    são válidos; monta o texto "{origem} → {destino}" a partir da mesma
 *    lista já buscada por `AccountSelect` (nenhuma chamada nova ao
 *    backend).
 */
export function TransferenciaFormDialog({ open, onClose }: TransferenciaFormDialogProps) {
  const toast = useToast();
  const criarTransferencia = useCriarTransferencia();
  const { data: contas } = useContas(true);
  const [acabouDeConfirmar, setAcabouDeConfirmar] = useState(false);

  const form = useForm<TransferenciaFormValues>({
    resolver: zodResolver(transferenciaFormSchema),
    mode: "onBlur",
    defaultValues: TRANSFERENCIA_VALORES_VAZIOS,
  });

  const origemId = useWatch({ control: form.control, name: "conta_origem_id" });
  const destinoId = useWatch({ control: form.control, name: "conta_destino_id" });
  const valor = useWatch({ control: form.control, name: "valor" });

  useEffect(() => {
    if (open) {
      form.reset(TRANSFERENCIA_VALORES_VAZIOS);
      setAcabouDeConfirmar(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function inverterContas() {
    form.setValue("conta_origem_id", destinoId, { shouldDirty: true });
    form.setValue("conta_destino_id", origemId, { shouldDirty: true });
  }

  const nomeContaOrigem = contas?.find((c) => String(c.id) === origemId)?.nome;
  const nomeContaDestino = contas?.find((c) => String(c.id) === destinoId)?.nome;
  const previewValido = !!nomeContaOrigem && !!nomeContaDestino && !!valor && Number(valor) > 0;

  async function onSubmit(values: TransferenciaFormValues) {
    try {
      const payload = transferenciaFormValuesParaCriacao(values);
      await criarTransferencia.mutateAsync(payload);
      // Confirmação elegante (seção 7.3 da análise): o preview pulsa em
      // verde por um instante antes do modal fechar — janela igual a
      // `DURATION.slow` (450ms, o teto de motion-principles.md), nunca um
      // loop, só um único pulso já contado.
      setAcabouDeConfirmar(true);
      toast.success(
        `Transferência de ${formatMoney(payload.valor)} de "${nomeContaOrigem}" para "${nomeContaDestino}" registrada.`,
      );
      setTimeout(onClose, DURATION.slow * 1000);
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof TransferenciaFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  const salvando = criarTransferencia.isPending;

  return (
    <FormDialog
      open={open}
      title="Nova transferência"
      description="Mova dinheiro entre duas contas suas — não é uma receita nem despesa, o valor só troca de lugar."
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="transferencia-form-dialog" loading={salvando}>
            Transferir
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="transferencia-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <div className="flex items-end gap-2">
          <div className="min-w-0 flex-1">
            <AccountSelect name="conta_origem_id" label="De" placeholder="Conta de origem" excluirId={destinoId ? Number(destinoId) : null} />
          </div>

          <div className="flex shrink-0 flex-col items-center gap-1 pb-2.5">
            <motion.button
              type="button"
              onClick={inverterContas}
              disabled={!origemId && !destinoId}
              title="Trocar origem e destino"
              aria-label="Trocar origem e destino"
              {...fadeIn(4)}
              className="group flex h-9 w-9 items-center justify-center rounded-full bg-accent-subtle text-accent transition-colors duration-fast ease-out hover:bg-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              {origemId || destinoId ? (
                <ArrowRight
                  size={17}
                  aria-hidden="true"
                  className={`transition-transform duration-base ease-out group-hover:translate-x-0.5 ${
                    salvando ? "animate-pulse" : ""
                  }`}
                />
              ) : (
                <ArrowLeftRight size={15} aria-hidden="true" />
              )}
            </motion.button>
          </div>

          <div className="min-w-0 flex-1">
            <AccountSelect name="conta_destino_id" label="Para" placeholder="Conta de destino" excluirId={origemId ? Number(origemId) : null} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <CurrencyField name="valor" label="Valor" />
          <DateField name="data" label="Data" />
        </div>

        <TextField
          name="descricao"
          label="Descrição"
          placeholder="Ex.: Reserva de emergência (opcional)"
        />

        {/* Preview da movimentação — segurança visual antes de confirmar
            (seção 7.2 da análise). `key` no valor força o motion a tratar
            "virou válido" como uma entrada nova (fadeIn), e o pulso de
            fundo na confirmação segue motion-principles.md, seção 6.2. */}
        <motion.div
          key={previewValido ? "valido" : "vazio"}
          initial={{ opacity: 0, y: 4 }}
          animate={{
            opacity: 1,
            y: 0,
            backgroundColor: acabouDeConfirmar
              ? ["var(--color-positive-subtle)", "var(--color-surface-2)"]
              : "var(--color-surface-2)",
          }}
          transition={
            acabouDeConfirmar
              ? { backgroundColor: { duration: DURATION.slow, ease: EASE.inOut }, default: { duration: DURATION.base, ease: EASE.out } }
              : { duration: DURATION.base, ease: EASE.out }
          }
          className="rounded-md border border-border-subtle bg-surface-2 p-3"
        >
          {previewValido ? (
            <div className="flex flex-wrap items-center justify-center gap-2 text-sm">
              <span className="font-medium text-text-primary">{nomeContaOrigem}</span>
              <span className="tabular font-semibold text-negative">− {formatMoney(valor)}</span>
              <ArrowRight size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
              <span className="tabular font-semibold text-positive">+ {formatMoney(valor)}</span>
              <span className="font-medium text-text-primary">{nomeContaDestino}</span>
            </div>
          ) : (
            <p className="text-center text-sm text-text-tertiary">
              Selecione as duas contas e o valor para ver o preview da movimentação.
            </p>
          )}
        </motion.div>
      </Form>
    </FormDialog>
  );
}
