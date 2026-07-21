import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { TextField } from "../../ui/TextField";
import { CurrencyField } from "../../ui/CurrencyField";
import { DateField } from "../../ui/DateField";
import { SelectField } from "../../ui/SelectField";
import {
  metaFormSchema,
  metaFormValuesParaAtualizacao,
  metaFormValuesParaCriacao,
  META_VALORES_VAZIOS,
  type MetaFormValues,
} from "../../../schemas/meta";
import { useAtualizarMeta, useCriarMeta } from "../../../hooks/useMetaQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import { FREQUENCIA_CONTRIBUICAO_LABEL } from "../../../utils/meta";
import type { MetaRead } from "../../../types/meta";

const FREQUENCIA_CONTRIBUICAO_OPTIONS = (
  Object.entries(FREQUENCIA_CONTRIBUICAO_LABEL) as [keyof typeof FREQUENCIA_CONTRIBUICAO_LABEL, string][]
).map(([value, label]) => ({ value, label }));

function metaParaFormulario(meta: MetaRead): MetaFormValues {
  return {
    descricao: meta.descricao,
    valor_alvo: meta.valor_alvo,
    data_alvo: meta.data_alvo ?? "",
    frequencia_contribuicao: meta.frequencia_contribuicao ?? "",
  };
}

export interface MetaFormDialogProps {
  open: boolean;
  /** `null`/`undefined` = modo criação. */
  meta?: MetaRead | null;
  onClose: () => void;
}

/**
 * Modal único de criar/editar Meta — mesma infraestrutura de
 * `Form`/`*Field`/`FormDialog` de toda entidade do projeto. Ver
 * docs/analise-arquitetural-metas-frontend.md, seção 3.3.
 *
 * Sem campo de conta aqui (Refatoramento de Metas/Transferências, ver
 * docs/analise-arquitetural-metas-transferencias.md) — o "cofrinho" é
 * sempre provisionado automaticamente pelo backend, nunca escolhido pelo
 * usuário. Aportes/resgates viram Transferência real para essa conta
 * oculta, feitos por `MetaAporteDialog`, não por aqui.
 *
 * Reativação por nome (backend) é transparente aqui: se `descricao`
 * colidir com uma Meta desativada, o backend reativa e devolve 201 normal,
 * sem nenhuma lógica especial neste componente. Colisão com uma Meta ATIVA
 * (ou renomear para um nome já usado por uma Meta inativa) vira 409,
 * tratado como qualquer outro conflito do projeto via `getFieldErrors`.
 */
export function MetaFormDialog({ open, meta, onClose }: MetaFormDialogProps) {
  const toast = useToast();
  const emEdicao = meta != null;
  const criarMeta = useCriarMeta();
  const atualizarMeta = useAtualizarMeta();
  const salvando = criarMeta.isPending || atualizarMeta.isPending;

  const form = useForm<MetaFormValues>({
    resolver: zodResolver(metaFormSchema),
    mode: "onBlur",
    defaultValues: META_VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      form.reset(meta ? metaParaFormulario(meta) : META_VALORES_VAZIOS);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, meta]);

  async function onSubmit(values: MetaFormValues) {
    try {
      if (emEdicao) {
        const payload = metaFormValuesParaAtualizacao(values);
        await atualizarMeta.mutateAsync({ id: meta.id, dados: payload });
        toast.success("Meta atualizada.");
      } else {
        const payload = metaFormValuesParaCriacao(values);
        await criarMeta.mutateAsync(payload);
        toast.success(`Meta "${values.descricao}" criada.`);
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof MetaFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title={emEdicao ? "Editar meta" : "Nova meta"}
      description="Defina um objetivo de economia. Depois de criar, use Aportar/Resgatar para movimentar dinheiro de uma conta sua para esta meta."
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="meta-form-dialog" loading={salvando}>
            {emEdicao ? "Salvar alterações" : "Criar meta"}
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="meta-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <TextField name="descricao" label="Descrição" placeholder="Ex.: Viagem para o Japão, Reserva de emergência" />
        <CurrencyField name="valor_alvo" label="Valor da meta" />
        <DateField name="data_alvo" label="Prazo" optional description="Deixe em branco para uma meta sem prazo definido." />
        <SelectField
          name="frequencia_contribuicao"
          label="Frequência de contribuição"
          options={FREQUENCIA_CONTRIBUICAO_OPTIONS}
          optional
          placeholder="Nenhuma"
          description="Com um prazo definido, mostramos quanto guardar por período para chegar na meta — apenas uma sugestão, nunca substitui o progresso real."
        />
      </Form>
    </FormDialog>
  );
}
