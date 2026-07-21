import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { CancelButton } from "../../ui/CancelButton";
import { SubmitButton } from "../../ui/SubmitButton";
import { TextField } from "../../ui/TextField";
import { CurrencyField } from "../../ui/CurrencyField";
import { NumberField } from "../../ui/NumberField";
import { DateField } from "../../ui/DateField";
import { SwitchField } from "../../ui/SwitchField";
import { AccountSelect } from "../conta/AccountSelect";
import {
  financiamentoFormSchema,
  financiamentoFormValuesParaCriacao,
  FINANCIAMENTO_VALORES_VAZIOS,
  type FinanciamentoFormValues,
} from "../../../schemas/financiamento";
import { useCriarFinanciamento } from "../../../hooks/useFinanciamentoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";

export interface FinanciamentoFormDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Criação de Financiamento — sem modo edição (backend não tem
 * `FinanciamentoUpdate`, ver docstring de `types/financiamento.ts`): todo
 * campo estrutural determina o cronograma de parcelas inteiro, gerado de
 * uma vez. Depois de criado, a única mudança de estado é pagar uma parcela
 * (ação dedicada no Drawer de cronograma, `FinanciamentosPage`).
 *
 * Formulário deliberadamente enxuto (pedido do usuário): sem taxa de
 * juros/CET/sistema de amortização/valor financiado/entrada/número de
 * contrato/categoria — só o que qualquer pessoa já sabe de cabeça sobre um
 * financiamento que está pagando. `financiamentoFormValuesParaCriacao`
 * (schemas/financiamento.ts) reconstrói o payload completo que o backend
 * ainda espera a partir do valor da parcela, sem exigir nenhuma mudança de
 * backend. `conta_id` é a única exceção mantida: é estruturalmente
 * obrigatória (de onde as parcelas são debitadas), não "burocracia".
 *
 * `parcelas_ja_pagas` (Etapa de Onboarding) — campo opcional, só existe na
 * criação. Quando preenchido, o backend marca as N primeiras parcelas como
 * PAGO e ajusta `saldo_devedor` automaticamente — nenhum cálculo acontece
 * aqui no cliente, só um aviso textual do que vai acontecer.
 */
export function FinanciamentoFormDialog({ open, onClose }: FinanciamentoFormDialogProps) {
  const toast = useToast();
  const criarFinanciamento = useCriarFinanciamento();

  const form = useForm<FinanciamentoFormValues>({
    resolver: zodResolver(financiamentoFormSchema),
    mode: "onBlur",
    defaultValues: FINANCIAMENTO_VALORES_VAZIOS,
  });

  const numParcelasAtual = useWatch({ control: form.control, name: "num_parcelas" });
  const parcelasJaPagasAtual = useWatch({ control: form.control, name: "parcelas_ja_pagas" });

  useEffect(() => {
    if (open) form.reset(FINANCIAMENTO_VALORES_VAZIOS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function onSubmit(values: FinanciamentoFormValues) {
    try {
      const payload = financiamentoFormValuesParaCriacao(values);
      await criarFinanciamento.mutateAsync(payload);
      toast.success(`Financiamento "${values.descricao}" criado.`);
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof FinanciamentoFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title="Novo financiamento"
      description="Registre um financiamento (imóvel, veículo, etc.) e o cronograma de parcelas é gerado automaticamente."
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="financiamento-form-dialog" loading={criarFinanciamento.isPending}>
            Criar financiamento
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="financiamento-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <TextField name="descricao" label="Nome" placeholder="Ex.: Financiamento do apartamento" />

        <TextField name="instituicao_financeira" label="Instituição financeira" placeholder="Ex.: Caixa" />

        <TextField name="bem_financiado" label="Bem financiado" optional placeholder="Ex.: Apartamento, carro" />

        <AccountSelect name="conta_id" label="Conta (débito das parcelas)" />

        <div className="grid grid-cols-2 gap-3">
          <CurrencyField name="valor_parcela" label="Valor da parcela" />
          <NumberField name="num_parcelas" label="Número de parcelas" placeholder="Ex.: 360" />
        </div>

        <DateField name="data_inicio" label="Data de início" />

        <SwitchField
          name="permite_quitacao_antecipada"
          label="Permite quitação antecipada"
          description="Só informativo — ainda não há ação de quitação antecipada no app."
        />

        {/* Etapa de Onboarding — ver ponto 2 da docstring do componente. */}
        <div className="space-y-1.5 rounded-md border border-border bg-surface-2 p-3">
          <NumberField
            name="parcelas_ja_pagas"
            label="Parcelas já pagas antes de usar o app"
            optional
            description="Deixe em branco ou 0 se este é um contrato novo."
            placeholder="Ex.: 12"
          />
          {!!parcelasJaPagasAtual && !!numParcelasAtual && (
            <p className="text-sm text-text-secondary">
              As parcelas 1 a {parcelasJaPagasAtual} de {numParcelasAtual} serão marcadas como pagas
              automaticamente.
            </p>
          )}
        </div>
      </Form>
    </FormDialog>
  );
}
