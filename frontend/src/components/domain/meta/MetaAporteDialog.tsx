import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { TextField } from "../../ui/TextField";
import { CurrencyField } from "../../ui/CurrencyField";
import { DateField } from "../../ui/DateField";
import { AccountSelect } from "../conta/AccountSelect";
import { useCriarTransferencia } from "../../../hooks/useTransferenciaQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import { formatMoney } from "../../../utils/format";
import type { TransferenciaCreate } from "../../../types/transferencia";
import type { MetaRead } from "../../../types/meta";

const aporteFormSchema = z.object({
  conta_id: z.string().min(1, "Selecione a conta."),
  valor: z.string().min(1, "Informe o valor."),
  data: z.string().min(1, "Informe a data."),
  descricao: z.string().max(200, "Use no máximo 200 caracteres.").optional(),
});

type AporteFormValues = z.infer<typeof aporteFormSchema>;

const VALORES_VAZIOS: AporteFormValues = { conta_id: "", valor: "", data: "", descricao: "" };

export type DirecaoAporteMeta = "APORTE" | "RESGATE";

export interface MetaAporteDialogProps {
  open: boolean;
  /** `null` só enquanto o dialog está fechando (evita flash de conteúdo
   * vazio) — nunca aberto com `meta: null`. */
  meta: MetaRead | null;
  direcao: DirecaoAporteMeta;
  onClose: () => void;
}

/**
 * Aporte/Resgate de Meta = uma Transferência real entre uma Conta do
 * usuário e o "cofrinho" da Meta (`meta.conta_id`, sempre oculto). Reusa
 * 100% `POST /transferencias` (`useCriarTransferencia`) — nenhum endpoint
 * dedicado foi criado para isso (decisão documentada em
 * docs/analise-arquitetural-metas-transferencias.md, seção 4.1). Por isso
 * este formulário só pede a OUTRA conta: o cofrinho é sempre o lado fixo,
 * decidido por `direcao` — aporte = cofrinho é destino (dinheiro entra na
 * meta), resgate = cofrinho é origem (dinheiro sai da meta).
 *
 * Mesma infraestrutura `Form`/`*Field`/`FormDialog` de todo o projeto, mas
 * SEM um `schemas/meta-aporte.ts` próprio — este não é um formulário de uma
 * nova entidade, é só uma composição de UI sobre `TransferenciaCreate` já
 * existente, então o schema de validação vive aqui mesmo.
 */
export function MetaAporteDialog({ open, meta, direcao, onClose }: MetaAporteDialogProps) {
  const toast = useToast();
  const criarTransferencia = useCriarTransferencia();

  const form = useForm<AporteFormValues>({
    resolver: zodResolver(aporteFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      form.reset({ ...VALORES_VAZIOS, data: new Date().toISOString().slice(0, 10) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function onSubmit(values: AporteFormValues) {
    if (!meta) return;
    try {
      const outraContaId = Number(values.conta_id);
      const payload: TransferenciaCreate = {
        conta_origem_id: direcao === "APORTE" ? outraContaId : meta.conta_id,
        conta_destino_id: direcao === "APORTE" ? meta.conta_id : outraContaId,
        valor: values.valor,
        data: values.data,
        descricao: values.descricao?.trim()
          ? values.descricao.trim()
          : `${direcao === "APORTE" ? "Aporte" : "Resgate"} — ${meta.descricao}`,
      };
      await criarTransferencia.mutateAsync(payload);
      toast.success(
        direcao === "APORTE"
          ? `Aporte de ${formatMoney(payload.valor)} registrado em "${meta.descricao}".`
          : `Resgate de ${formatMoney(payload.valor)} registrado de "${meta.descricao}".`,
      );
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          // O backend erra em `conta_origem_id`/`conta_destino_id` — os dois
          // mapeiam pro único campo de conta deste formulário.
          const campoDoFormulario =
            campo === "conta_origem_id" || campo === "conta_destino_id" ? "conta_id" : campo;
          form.setError(campoDoFormulario as keyof AporteFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  if (!meta) return null;

  const aporte = direcao === "APORTE";

  return (
    <FormDialog
      open={open}
      title={aporte ? `Aportar em "${meta.descricao}"` : `Resgatar de "${meta.descricao}"`}
      description={
        aporte
          ? "Move dinheiro de uma conta sua para esta meta — não é uma despesa, o valor continua contando no seu patrimônio."
          : "Move dinheiro desta meta de volta para uma conta sua — não é uma receita, o valor só troca de lugar."
      }
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="meta-aporte-dialog" loading={criarTransferencia.isPending}>
            {aporte ? "Aportar" : "Resgatar"}
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="meta-aporte-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <AccountSelect
          name="conta_id"
          label={aporte ? "De qual conta sai o dinheiro?" : "Para qual conta vai o dinheiro?"}
        />
        <div className="grid grid-cols-2 gap-3">
          <CurrencyField name="valor" label="Valor" />
          <DateField name="data" label="Data" />
        </div>
        <TextField
          name="descricao"
          label="Descrição"
          optional
          placeholder={aporte ? "Ex.: Aporte mensal (opcional)" : "Ex.: Resgate para emergência (opcional)"}
        />
      </Form>
    </FormDialog>
  );
}
