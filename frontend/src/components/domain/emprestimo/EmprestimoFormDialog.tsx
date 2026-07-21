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
import { PercentageField } from "../../ui/PercentageField";
import { NumberField } from "../../ui/NumberField";
import { DateField } from "../../ui/DateField";
import { SelectField } from "../../ui/SelectField";
import { SwitchField } from "../../ui/SwitchField";
import { AccountSelect } from "../conta/AccountSelect";
import { CategorySelect } from "../categoria/CategorySelect";
import {
  emprestimoFormSchema,
  emprestimoFormValuesParaCriacao,
  EMPRESTIMO_VALORES_VAZIOS,
  type EmprestimoFormValues,
} from "../../../schemas/emprestimo";
import { useCriarEmprestimo } from "../../../hooks/useEmprestimoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";

const SISTEMA_AMORTIZACAO_OPTIONS = [
  { value: "PRICE", label: "PRICE (parcelas fixas)" },
  { value: "SAC", label: "SAC (parcelas decrescentes)" },
];

export interface EmprestimoFormDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Criação de Empréstimo — mesmo raciocínio de `FinanciamentoFormDialog`
 * (sem modo edição, `parcelas_ja_pagas` da Etapa de Onboarding). Diferença
 * de Financiamento: `valor_liberado` é sempre o desembolso inteiro (sem
 * entrada), e sempre gera uma Transacao de RECEITA avulsa na conta
 * escolhida, além das parcelas de amortização (DESPESA).
 */
export function EmprestimoFormDialog({ open, onClose }: EmprestimoFormDialogProps) {
  const toast = useToast();
  const criarEmprestimo = useCriarEmprestimo();

  const form = useForm<EmprestimoFormValues>({
    resolver: zodResolver(emprestimoFormSchema),
    mode: "onBlur",
    defaultValues: EMPRESTIMO_VALORES_VAZIOS,
  });

  const numParcelasAtual = useWatch({ control: form.control, name: "num_parcelas" });
  const parcelasJaPagasAtual = useWatch({ control: form.control, name: "parcelas_ja_pagas" });

  useEffect(() => {
    if (open) form.reset(EMPRESTIMO_VALORES_VAZIOS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function onSubmit(values: EmprestimoFormValues) {
    try {
      const payload = emprestimoFormValuesParaCriacao(values);
      await criarEmprestimo.mutateAsync(payload);
      toast.success(`Empréstimo "${values.descricao}" criado.`);
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof EmprestimoFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title="Novo empréstimo"
      description="Registre um empréstimo e o cronograma de parcelas é gerado automaticamente."
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="emprestimo-form-dialog" loading={criarEmprestimo.isPending}>
            Criar empréstimo
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="emprestimo-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <TextField name="descricao" label="Descrição" placeholder="Ex.: Empréstimo pessoal" />

        <div className="grid grid-cols-2 gap-3">
          <TextField name="instituicao_financeira" label="Instituição financeira" placeholder="Ex.: Nubank" />
          <TextField name="numero_contrato" label="Número do contrato" optional />
        </div>

        <AccountSelect name="conta_id" label="Conta (desembolso e débito das parcelas)" />

        <CurrencyField name="valor_liberado" label="Valor liberado" />

        <TextField name="finalidade" label="Finalidade" optional placeholder="Ex.: Reforma, viagem" />

        <div className="grid grid-cols-2 gap-3">
          <PercentageField name="taxa_juros" label="Taxa de juros (% a.m.)" />
          <PercentageField name="cet" label="CET (% a.m.)" optional />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <SelectField name="sistema_amortizacao" label="Sistema de amortização" options={SISTEMA_AMORTIZACAO_OPTIONS} />
          <NumberField name="num_parcelas" label="Número de parcelas" placeholder="Ex.: 24" />
        </div>

        <DateField name="data_inicio" label="Data de início" />

        <CategorySelect name="categoria_id" label="Categoria" optional tipoTransacao="DESPESA" />

        <SwitchField
          name="permite_quitacao_antecipada"
          label="Permite quitação antecipada"
          description="Só informativo — ainda não há ação de quitação antecipada no app."
        />

        <div className="space-y-1.5 rounded-md border border-border bg-surface-2 p-3">
          <NumberField
            name="parcelas_ja_pagas"
            label="Parcelas já pagas antes de usar o app"
            optional
            description="Deixe em branco ou 0 se este é um contrato novo."
            placeholder="Ex.: 6"
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
