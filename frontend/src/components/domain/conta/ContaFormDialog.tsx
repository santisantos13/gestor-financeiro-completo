import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/TextField";
import { SelectField } from "../../ui/SelectField";
import { CurrencyField } from "../../ui/CurrencyField";
import { InstitutionBadge } from "../../ui/InstitutionBadge";
import { BankPicker } from "../../ui/BankPicker";
import { contaFormSchema, contaFormValuesParaPayload, type ContaFormValues } from "../../../schemas/conta";
import { useCriarConta, useAtualizarConta } from "../../../hooks/useContaQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import { formatMoney } from "../../../utils/format";
import { LABEL_TIPO_CONTA } from "./contaTableColumns";
import type { ContaRead } from "../../../types/conta";
import type { Control } from "react-hook-form";

const TIPO_OPTIONS = Object.entries(LABEL_TIPO_CONTA).map(([value, label]) => ({ value, label }));

const VALORES_VAZIOS: ContaFormValues = {
  nome: "",
  tipo: "CORRENTE",
  saldo_inicial: "",
  instituicao: "",
};

function contaParaFormulario(conta: ContaRead): ContaFormValues {
  return {
    nome: conta.nome,
    tipo: conta.tipo,
    saldo_inicial: conta.saldo_inicial,
    instituicao: conta.instituicao ?? "",
  };
}

/** Preview ao vivo do `InstitutionBadge` conforme o usuário digita em
 * "Instituição" — isolado num componente próprio para que só ele
 * re-renderize a cada tecla (`useWatch` escopado), não o `ContaFormDialog`
 * inteiro. Mesma peça visual usada na coluna de tabela e no Dashboard —
 * nenhum componente de preview novo, só reaproveitamento. */
function InstituicaoPreview({ control }: { control: Control<ContaFormValues> }) {
  const instituicao = useWatch({ control, name: "instituicao" });
  return <InstitutionBadge nome={instituicao} size="sm" />;
}

export interface ContaFormDialogProps {
  open: boolean;
  /** `null`/`undefined` = modo criação. Uma `ContaRead` = criação não se aplica. */
  conta?: ContaRead | null;
  /** Quando `true` (só faz sentido com `conta` definida), abre em modo
   * leitura ("visualizar conta" da Etapa F6) — os campos ficam
   * desabilitados e o rodapé mostra "Editar" em vez de "Salvar". Reaproveita
   * o mesmo `Form`/`*Field` inteiro (todo campo aqui já aceita `disabled`)
   * em vez de um componente de detalhe separado — evita duplicar o layout
   * dos campos em dois lugares diferentes. */
  somenteLeitura?: boolean;
  onClose: () => void;
}

/**
 * Modal único de criar/visualizar/editar Conta — compõe inteiramente a
 * infraestrutura das Etapas F5 (`FormDialog`/`Form`/`*Field`) e F6
 * (`useCriarConta`/`useAtualizarConta`). Nenhuma regra de negócio aqui: o
 * schema Zod só valida formato/obrigatoriedade (`schemas/conta.ts`); um 422
 * real do backend é mapeado campo a campo via `getFieldErrors` +
 * `form.setError` (mesma mecânica já demonstrada em `/dev/forms`).
 */
export function ContaFormDialog({ open, conta, somenteLeitura, onClose }: ContaFormDialogProps) {
  const toast = useToast();
  const criarConta = useCriarConta();
  const atualizarConta = useAtualizarConta();
  const emEdicao = conta != null;
  const salvando = criarConta.isPending || atualizarConta.isPending;

  const [editando, setEditando] = useState(!(somenteLeitura && emEdicao));

  const form = useForm<ContaFormValues>({
    resolver: zodResolver(contaFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  // Reseta o formulário (e o modo visualizar/editar) sempre que o modal
  // abre - com os dados da conta em questão, ou vazio em criação. `open`
  // como dependência (não só `conta`) porque reabrir o modal para a MESMA
  // conta duas vezes seguidas também precisa voltar ao estado original,
  // descartando qualquer digitação anterior não salva e voltando ao modo
  // leitura se foi assim que o modal foi aberto.
  useEffect(() => {
    if (open) {
      form.reset(conta ? contaParaFormulario(conta) : VALORES_VAZIOS);
      setEditando(!(somenteLeitura && emEdicao));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, conta, somenteLeitura]);

  async function onSubmit(values: ContaFormValues) {
    const payload = contaFormValuesParaPayload(values);
    try {
      if (emEdicao) {
        await atualizarConta.mutateAsync({ id: conta.id, dados: payload });
        toast.success(`Conta "${values.nome}" atualizada.`);
      } else {
        await criarConta.mutateAsync(payload);
        toast.success(`Conta "${values.nome}" criada.`);
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof ContaFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  const titulo = !emEdicao ? "Nova conta" : editando ? "Editar conta" : "Detalhes da conta";
  const descricao = !emEdicao
    ? "Cadastre uma conta onde seu dinheiro fica guardado (corrente, poupança, carteira, investimento)."
    : editando
      ? "Altere os dados da conta. O saldo atual continua calculado pelo histórico de transações."
      : "O saldo atual é calculado a partir do histórico de transações da conta.";

  return (
    <FormDialog
      open={open}
      title={titulo}
      description={descricao}
      isDirty={editando && form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) =>
        editando ? (
          <FormActions>
            <CancelButton onClick={requestClose}>Cancelar</CancelButton>
            <SubmitButton form="conta-form-dialog" loading={salvando}>
              {emEdicao ? "Salvar alterações" : "Criar conta"}
            </SubmitButton>
          </FormActions>
        ) : (
          <FormActions>
            <CancelButton onClick={requestClose}>Fechar</CancelButton>
            <Button type="button" onClick={() => setEditando(true)}>
              Editar
            </Button>
          </FormActions>
        )
      }
    >
      <Form id="conta-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <TextField name="nome" label="Nome" placeholder="Ex.: Nubank, Carteira, Poupança Itaú" disabled={!editando} />
        <SelectField name="tipo" label="Tipo" options={TIPO_OPTIONS} disabled={!editando} />
        <CurrencyField name="saldo_inicial" label="Saldo inicial" disabled={!editando} />
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <BankPicker name="instituicao" label="Instituição" optional disabled={!editando} />
          </div>
          <div className="pb-2">
            <InstituicaoPreview control={form.control} />
          </div>
        </div>
        {emEdicao && (
          <div className="rounded-sm border border-border bg-surface-2 px-3 py-2 text-sm text-text-secondary">
            Saldo atual: <span className="font-mono tabular text-text-primary">{formatMoney(conta.saldo_atual)}</span>
          </div>
        )}
      </Form>
    </FormDialog>
  );
}
