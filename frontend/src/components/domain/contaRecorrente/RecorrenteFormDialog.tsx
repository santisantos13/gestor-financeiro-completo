import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { TextField } from "../../ui/TextField";
import { CurrencyField } from "../../ui/CurrencyField";
import { DateField } from "../../ui/DateField";
import { NumberField } from "../../ui/NumberField";
import { SelectField } from "../../ui/SelectField";
import { RadioGroupField } from "../../ui/RadioGroupField";
import { AccountSelect } from "../conta/AccountSelect";
import { CardSelect } from "../cartao/CardSelect";
import { CategorySelect } from "../categoria/CategorySelect";
import {
  FREQUENCIAS_SEM_DIA_VENCIMENTO,
  OPCOES_FREQUENCIA,
  RECORRENTE_VALORES_VAZIOS,
  recorrenteFormSchema,
  recorrenteFormValuesParaPayload,
  recorrenteFormValuesParaUpdate,
  type RecorrenteFormValues,
} from "../../../schemas/contaRecorrente";
import {
  useCriarContaRecorrente,
  useAtualizarContaRecorrente,
} from "../../../hooks/useContaRecorrenteQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import type { ContaRecorrenteRead } from "../../../types/contaRecorrente";

export interface RecorrenteFormDialogProps {
  open: boolean;
  /** `null` = criação; preenchido = edição (PATCH — só afeta ocorrências
   * futuras, cada ocorrência já gerada é uma Transacao independente). */
  recorrente?: ContaRecorrenteRead | null;
  onClose: () => void;
}

function recorrenteParaFormulario(recorrente: ContaRecorrenteRead): RecorrenteFormValues {
  return {
    descricao: recorrente.descricao,
    valor: recorrente.valor,
    tipo: recorrente.tipo === "RECEITA" ? "RECEITA" : "DESPESA",
    frequencia: recorrente.frequencia,
    dia_vencimento: recorrente.dia_vencimento ?? undefined,
    origem: recorrente.cartao_id != null ? "CARTAO" : "CONTA",
    conta_id: recorrente.conta_id != null ? String(recorrente.conta_id) : "",
    cartao_id: recorrente.cartao_id != null ? String(recorrente.cartao_id) : "",
    categoria_id: recorrente.categoria_id != null ? String(recorrente.categoria_id) : "",
    data_inicio: recorrente.data_inicio,
    data_fim: recorrente.data_fim ?? "",
  };
}

/**
 * Formulário de Conta Recorrente (expansão 2026-07-20,
 * docs/analise-arquitetural-conta-recorrente-expansao.md, seção 8).
 * Campos condicionais por família de frequência: `dia_vencimento` só
 * aparece nas baseadas em meses (nas baseadas em dias a âncora é a
 * própria data de início — o texto de apoio explica isso no lugar do
 * campo). Origem Conta/Cartão com os pickers de domínio existentes.
 */
export function RecorrenteFormDialog({ open, recorrente, onClose }: RecorrenteFormDialogProps) {
  const toast = useToast();
  const criar = useCriarContaRecorrente();
  const atualizar = useAtualizarContaRecorrente();
  const emEdicao = recorrente != null;

  const form = useForm<RecorrenteFormValues>({
    resolver: zodResolver(recorrenteFormSchema),
    mode: "onBlur",
    defaultValues: RECORRENTE_VALORES_VAZIOS,
  });

  const frequencia = useWatch({ control: form.control, name: "frequencia" });
  const origem = useWatch({ control: form.control, name: "origem" });
  const usaDiaVencimento = !FREQUENCIAS_SEM_DIA_VENCIMENTO.includes(frequencia);

  useEffect(() => {
    if (open) {
      form.reset(recorrente ? recorrenteParaFormulario(recorrente) : RECORRENTE_VALORES_VAZIOS);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, recorrente]);

  async function onSubmit(valores: RecorrenteFormValues) {
    try {
      if (emEdicao && recorrente) {
        await atualizar.mutateAsync({ id: recorrente.id, dados: recorrenteFormValuesParaUpdate(valores) });
        toast.success(`Recorrência "${valores.descricao}" atualizada — vale para as próximas ocorrências.`);
      } else {
        await criar.mutateAsync(recorrenteFormValuesParaPayload(valores));
        toast.success(
          `Recorrência "${valores.descricao}" criada. Ocorrências já vencidas foram lançadas automaticamente.`,
        );
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof RecorrenteFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  const salvando = criar.isPending || atualizar.isPending;

  return (
    <FormDialog
      open={open}
      title={emEdicao ? "Editar recorrência" : "Nova recorrência"}
      description={
        emEdicao
          ? "As mudanças valem só para as próximas ocorrências — lançamentos já gerados não são reescritos."
          : "Um lançamento que se repete sozinho: salário, aluguel, assinatura, academia. Cada ocorrência vira uma transação de verdade."
      }
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="recorrente-form-dialog" loading={salvando}>
            {emEdicao ? "Salvar" : "Criar recorrência"}
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="recorrente-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <TextField name="descricao" label="Descrição" placeholder="Ex.: Aluguel, Salário, Netflix" />

        <div className="grid grid-cols-2 gap-3">
          <CurrencyField name="valor" label="Valor" />
          <RadioGroupField
            name="tipo"
            label="Tipo"
            inline
            options={[
              { value: "DESPESA", label: "Despesa" },
              { value: "RECEITA", label: "Receita" },
            ]}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <SelectField name="frequencia" label="Frequência" options={OPCOES_FREQUENCIA} />
          {usaDiaVencimento ? (
            <NumberField
              name="dia_vencimento"
              label="Dia do vencimento"
              placeholder="1 a 31"
              description="Dia 31 em meses curtos cai no último dia do mês."
            />
          ) : (
            <div className="flex items-end pb-1 text-caption text-text-tertiary">
              A recorrência se repete a partir da data de início — sem dia fixo do mês.
            </div>
          )}
        </div>

        <RadioGroupField
          name="origem"
          label="Origem"
          inline
          options={[
            { value: "CONTA", label: "Conta" },
            { value: "CARTAO", label: "Cartão" },
          ]}
        />
        {origem === "CONTA" ? (
          <AccountSelect name="conta_id" label="Conta" placeholder="Selecione a conta" />
        ) : (
          <CardSelect name="cartao_id" label="Cartão" placeholder="Selecione o cartão" />
        )}

        <CategorySelect name="categoria_id" label="Categoria" optional />

        <div className="grid grid-cols-2 gap-3">
          <DateField name="data_inicio" label="Início" />
          <DateField
            name="data_fim"
            label="Término"
            optional
            description="Em branco = sem data para acabar."
          />
        </div>
      </Form>
    </FormDialog>
  );
}
