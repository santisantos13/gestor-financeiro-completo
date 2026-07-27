/**
 * Modal único de criar/editar Alerta — mesma estrutura de
 * `TagFormDialog`/`ContaFormDialog`, mas com uma particularidade: `tipo` +
 * `entidade_id` só são editáveis na CRIAÇÃO (imutáveis depois, ver
 * docstring de `types/alerta.ts`/`AlertaUpdate` no backend) — em modo de
 * edição eles aparecem desabilitados, só `condicao` é de fato editável.
 *
 * O picker de entidade troca de fonte conforme `tipo` (Cartão para
 * LIMITE_CARTAO/VENCIMENTO_FATURA, Conta Recorrente para
 * VENCIMENTO_CONTA_RECORRENTE, Meta para META_ATINGIDA, Conta para
 * SALDO_BAIXO) — e o campo de `condicao` troca junto (percentual/dias/
 * valor mínimo/nenhum). Ver docs/analise-arquitetural-alertas.md, seção 8.
 */
import { useEffect, useRef } from "react";
import { useForm, useWatch } from "react-hook-form";
import type { Control } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { SelectField } from "../../ui/SelectField";
import { PercentageField } from "../../ui/PercentageField";
import { NumberField } from "../../ui/NumberField";
import { CurrencyField } from "../../ui/CurrencyField";
import {
  alertaFormSchema,
  alertaFormValuesParaAtualizar,
  alertaFormValuesParaCriar,
  alertaParaFormValues,
  VALORES_VAZIOS_ALERTA,
  type AlertaFormValues,
} from "../../../schemas/alerta";
import { TIPO_ALERTA_LABEL, descreverCondicaoAlerta } from "../../../lib/alertaDescricao";
import { useCriarAlerta, useAtualizarAlerta } from "../../../hooks/useAlertaQueries";
import { useCartoes } from "../../../hooks/useCartaoQueries";
import { useContas } from "../../../hooks/useContaQueries";
import { useMetas } from "../../../hooks/useMetaQueries";
import { useContasRecorrentes } from "../../../hooks/useContaRecorrenteQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import type { AlertaRead, TipoAlerta } from "../../../types/alerta";
import type { SelectOption } from "../../ui/Select";

const OPCOES_TIPO: SelectOption[] = (Object.keys(TIPO_ALERTA_LABEL) as TipoAlerta[]).map((tipo) => ({
  value: tipo,
  label: TIPO_ALERTA_LABEL[tipo],
}));

/** Isolado num componente próprio para que só ele re-renderize a cada
 * troca de `tipo`/campo de condição (mesmo padrão de `TagPreview`). */
function CondicaoFields({ control }: { control: Control<AlertaFormValues> }) {
  const tipo = useWatch({ control, name: "tipo" });

  if (tipo === "LIMITE_CARTAO") {
    return <PercentageField name="limite_percentual" label="Avisar ao atingir (% do limite)" placeholder="90,00" />;
  }
  if (tipo === "VENCIMENTO_FATURA" || tipo === "VENCIMENTO_CONTA_RECORRENTE") {
    return (
      <NumberField
        name="dias_antes"
        label="Avisar quantos dias antes do vencimento"
        optional
        description="Deixe em branco para usar o padrão (3 dias)."
        placeholder="3"
      />
    );
  }
  if (tipo === "SALDO_BAIXO") {
    return <CurrencyField name="valor_minimo" label="Avisar quando o saldo ficar abaixo de" />;
  }
  return null; // META_ATINGIDA não tem condição configurável.
}

/** Também isolado: usa os 4 hooks de listagem (um por tipo de entidade),
 * mas só o `useQuery` do `tipo` atual importa de verdade para o usuário -
 * os outros continuam rodando em background (cache compartilhado com o
 * resto do app, nenhum custo extra de rede visível). */
function EntidadeField({ control, disabled }: { control: Control<AlertaFormValues>; disabled?: boolean }) {
  const tipo = useWatch({ control, name: "tipo" });

  const { data: cartoes } = useCartoes(true);
  const { data: contas } = useContas(true);
  const { data: metas } = useMetas(true);
  const { data: recorrentes } = useContasRecorrentes();

  let opcoes: SelectOption[] = [];
  let label = "Item monitorado";
  if (tipo === "LIMITE_CARTAO" || tipo === "VENCIMENTO_FATURA") {
    label = "Cartão";
    opcoes = (cartoes ?? []).map((c) => ({ value: String(c.id), label: c.nome }));
  } else if (tipo === "VENCIMENTO_CONTA_RECORRENTE") {
    label = "Conta recorrente";
    opcoes = (recorrentes ?? []).map((r) => ({ value: String(r.id), label: r.descricao }));
  } else if (tipo === "META_ATINGIDA") {
    label = "Meta";
    opcoes = (metas ?? []).map((m) => ({ value: String(m.id), label: m.descricao }));
  } else if (tipo === "SALDO_BAIXO") {
    label = "Conta";
    opcoes = (contas ?? []).map((c) => ({ value: String(c.id), label: c.nome }));
  }

  return (
    <SelectField
      name="entidade_id"
      label={label}
      options={opcoes}
      placeholder={opcoes.length === 0 ? "Nenhum item disponível" : "Selecione"}
      disabled={disabled || opcoes.length === 0}
    />
  );
}

/** Preview textual da regra (mesmo texto que a `AlertasDrawer` mostraria
 * para este alerta) — reaproveita `descreverCondicaoAlerta`, nunca
 * duplica o texto. */
function CondicaoPreview({ control }: { control: Control<AlertaFormValues> }) {
  const valores = useWatch({ control });
  const tipo = valores.tipo as TipoAlerta;
  const condicao =
    tipo === "LIMITE_CARTAO"
      ? { limite_percentual: Number(valores.limite_percentual || 0) }
      : tipo === "VENCIMENTO_FATURA" || tipo === "VENCIMENTO_CONTA_RECORRENTE"
        ? { dias_antes: valores.dias_antes ?? 3 }
        : tipo === "SALDO_BAIXO"
          ? { valor_minimo: Number(valores.valor_minimo || 0) }
          : null;

  return <p className="text-sm text-text-tertiary">{descreverCondicaoAlerta(tipo, condicao)}</p>;
}

export interface AlertaFormDialogProps {
  open: boolean;
  /** `null`/`undefined` = modo criação. */
  alerta?: AlertaRead | null;
  onClose: () => void;
}

export function AlertaFormDialog({ open, alerta, onClose }: AlertaFormDialogProps) {
  const toast = useToast();
  const criarAlerta = useCriarAlerta();
  const atualizarAlerta = useAtualizarAlerta();
  const emEdicao = alerta != null;
  const salvando = criarAlerta.isPending || atualizarAlerta.isPending;

  const form = useForm<AlertaFormValues>({
    resolver: zodResolver(alertaFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS_ALERTA,
  });

  useEffect(() => {
    if (open) {
      form.reset(
        alerta ? alertaParaFormValues(alerta.tipo, alerta.entidade_id ?? 0, alerta.condicao) : VALORES_VAZIOS_ALERTA,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, alerta]);

  // Trocar `tipo` na criação muda a lista de entidades disponível (Cartão
  // → Conta, por exemplo) - o `entidade_id` antigo quase certamente não
  // existe na nova lista, então esvazia a seleção em vez de deixar um id
  // "fantasma" no formulário. Ignora a primeira renderização (o `reset`
  // acima já define `tipo` sem que isso deva mexer em `entidade_id`).
  const tipoSelecionado = useWatch({ control: form.control, name: "tipo" });
  const primeiraRenderizacao = useRef(true);
  useEffect(() => {
    if (primeiraRenderizacao.current) {
      primeiraRenderizacao.current = false;
      return;
    }
    if (!emEdicao) form.setValue("entidade_id", "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipoSelecionado]);

  async function onSubmit(values: AlertaFormValues) {
    try {
      if (emEdicao) {
        await atualizarAlerta.mutateAsync({ id: alerta.id, dados: alertaFormValuesParaAtualizar(values) });
        toast.success("Alerta atualizado.");
      } else {
        await criarAlerta.mutateAsync(alertaFormValuesParaCriar(values));
        toast.success("Alerta criado.");
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof AlertaFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title={emEdicao ? "Editar alerta" : "Novo alerta"}
      description={
        emEdicao
          ? "O tipo e o item monitorado não podem ser trocados - exclua e crie outro se precisar mudar o alvo."
          : "Escolha o que monitorar e quando avisar."
      }
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="alerta-form-dialog" loading={salvando}>
            {emEdicao ? "Salvar alterações" : "Criar alerta"}
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="alerta-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <SelectField name="tipo" label="Tipo de alerta" options={OPCOES_TIPO} disabled={emEdicao} />
        <EntidadeField control={form.control} disabled={emEdicao} />
        <CondicaoFields control={form.control} />
        <CondicaoPreview control={form.control} />
      </Form>
    </FormDialog>
  );
}
