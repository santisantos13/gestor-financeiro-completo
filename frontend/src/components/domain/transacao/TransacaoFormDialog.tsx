import { useEffect, useRef } from "react";
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
import { DateField } from "../../ui/DateField";
import { NumberField } from "../../ui/NumberField";
import { AccountSelect } from "../conta/AccountSelect";
import { CardSelect } from "../cartao/CardSelect";
import { CategorySelect } from "../categoria/CategorySelect";
import { TagMultiSelect } from "../tag/TagMultiSelect";
import {
  transacaoFormSchema,
  transacaoFormValuesParaAtualizacao,
  transacaoFormValuesParaCriacao,
  transacaoFormValuesParaParcelamento,
  TRANSACAO_VALORES_VAZIOS,
  type TransacaoFormValues,
} from "../../../schemas/transacao";
import { useAtualizarTransacao, useCriarTransacao } from "../../../hooks/useTransacaoQueries";
import { useCriarParcelamento } from "../../../hooks/useParcelamentoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import { formatMoney } from "../../../utils/format";
import type { TransacaoRead } from "../../../types/transacao";
import type { TipoTransacao } from "../../../types/enums";

const TIPO_OPTIONS = [
  { value: "DESPESA", label: "Despesa" },
  { value: "RECEITA", label: "Receita" },
];

const STATUS_OPTIONS = [
  { value: "PENDENTE", label: "Pendente" },
  { value: "PAGO", label: "Pago" },
];

const MODALIDADE_OPTIONS = [
  { value: "AVISTA", label: "À vista" },
  { value: "PARCELADO", label: "Parcelado" },
];

function transacaoParaFormulario(transacao: TransacaoRead): TransacaoFormValues {
  return {
    tipo: transacao.tipo,
    valor: transacao.valor,
    data: transacao.data,
    descricao: transacao.descricao,
    origem: transacao.conta_id != null ? "CONTA" : "CARTAO",
    conta_id: transacao.conta_id != null ? String(transacao.conta_id) : "",
    cartao_id: transacao.cartao_id != null ? String(transacao.cartao_id) : "",
    status: transacao.status,
    categoria_id: transacao.categoria_id != null ? String(transacao.categoria_id) : "",
    tag_ids: transacao.tags.map((tag) => String(tag.id)),
    // Uma transação já existente nunca "vira" um parcelamento novo — o
    // toggle Parcelado só aparece em modo criação (ver seção 5 da
    // docstring do componente).
    modalidade: "AVISTA",
    num_parcelas: undefined,
  };
}

export interface TransacaoFormDialogProps {
  open: boolean;
  /** `null`/`undefined` = modo criação. */
  transacao?: TransacaoRead | null;
  onClose: () => void;
  /** Etapa de Refinamento de UX/Dashboard/Cartões, seção 6.3 ("ajuste de
   * saldo inicial de fatura"): só usado em modo CRIAÇÃO (`transacao` nulo)
   * — sobrepõe `TRANSACAO_VALORES_VAZIOS` para abrir o formulário já
   * preenchido (ex. origem "Cartão" + o próprio cartão + descrição
   * sugerida), sem criar um formulário/fluxo paralelo só para esse caso.
   * O usuário ainda revisa/edita tudo antes de salvar — nenhum dado é
   * enviado sem confirmação explícita. */
  valoresIniciais?: Partial<TransacaoFormValues>;
}

/**
 * Modal único de criar/editar Transação — compõe a mesma infraestrutura de
 * `Form`/`*Field`/`FormDialog` de todo o projeto. Ver
 * docs/analise-arquitetural-transacao-frontend.md, seções 3, 5, 7 e 8.
 *
 * Três comportamentos específicos desta entidade, nenhum genérico o
 * suficiente para virar componente à parte:
 *
 * 1. Origem (Conta × Cartão) — seção 3: alternância local via dois
 *    botões, decide qual dos dois selects "inteligentes" aparece. Na
 *    edição, os dois botões e o select ficam desabilitados (o backend não
 *    aceita `conta_id`/`cartao_id` em `TransacaoUpdate` — a origem é
 *    imutável depois de criada).
 * 2. `status` só aparece (editável) quando a origem é Conta — seção 7: em
 *    Cartão o backend sempre força `PAGO`, mostrar o controle seria
 *    redundante ou enganoso.
 * 3. Trocar `tipo` limpa `categoria_id` — seção 5: evita ficar com uma
 *    categoria de Receita numa transação de Despesa (ou vice-versa) só
 *    porque o tipo mudou depois de escolher a categoria. Implementado com
 *    um `ref` que guarda o `tipo` anterior e só limpa em mudanças reais
 *    (nunca no reset inicial do próprio `useEffect` de abertura).
 * 4. `valoresIniciais` (Etapa de Refinamento de UX/Dashboard/Cartões, seção
 *    6.3) — único jeito de pré-preencher o formulário em modo criação
 *    (ex. "ajuste de saldo inicial de fatura" a partir de
 *    `CartaoDetalhePage`); o backend continua vendo exatamente a mesma
 *    `Transacao` normal de sempre, nenhum endpoint/regra nova.
 * 5. À vista × Parcelado (pedido do usuário) — só aparece quando
 *    `origem === "CARTAO"` E é modo criação (uma parcela já gerada nunca
 *    "vira" um parcelamento novo). "Parcelado" revela `NumberField` de
 *    número de parcelas + `CurrencyField` opcional "Valor da parcela"
 *    (pedido do usuário: "ajuda caso a compra tenha sido parcelada com
 *    juros ou sem juros" — vazio deixa o backend dividir `valor_total`
 *    igualmente, como sempre; preenchido usa esse valor exato em cada
 *    parcela) + preview "Nx de R$ Y" (cálculo puro no cliente — reflete o
 *    valor customizado quando presente, senão a divisão automática; o
 *    backend recalcula/arredonda de verdade de qualquer forma). Ao
 *    submeter com `modalidade: "PARCELADO"`, a chamada inteira desvia para
 *    `useCriarParcelamento`/`POST /parcelamentos` em vez de
 *    `POST /transacoes` — o backend gera as N `Transacao` reais
 *    (`ParcelamentoService._gerar_parcelas`). `TagMultiSelect` some nesse
 *    modo porque `ParcelamentoCreate` não aceita tags (aplicariam a
 *    nenhuma parcela específica) — omitir é mais honesto que mostrar um
 *    campo que seria silenciosamente ignorado. Trocar `origem` para
 *    "Conta" reseta `modalidade`/`num_parcelas`/`valor_parcela` de volta
 *    para o estado inicial automaticamente. `TagMultiSelect` some nesse
 *    modo — não existe em `ParcelamentoCreate`.
 * 6. Sem campo de Meta aqui (Refatoramento de Metas/Transferências, ver
 *    docs/analise-arquitetural-metas-transferencias.md, seção 6) — uma
 *    Transação nova não pode mais ser vinculada a uma Meta; aportes/
 *    resgates viram Transferência real para o "cofrinho" da Meta
 *    (`MetaAporteDialog`), fora deste formulário. O antigo `MetaSelect` foi
 *    removido.
 */
export function TransacaoFormDialog({ open, transacao, onClose, valoresIniciais }: TransacaoFormDialogProps) {
  const toast = useToast();
  const emEdicao = transacao != null;
  const criarTransacao = useCriarTransacao();
  const atualizarTransacao = useAtualizarTransacao(transacao?.conta_id, transacao?.cartao_id);
  const criarParcelamento = useCriarParcelamento();
  const salvando = criarTransacao.isPending || atualizarTransacao.isPending || criarParcelamento.isPending;

  const form = useForm<TransacaoFormValues>({
    resolver: zodResolver(transacaoFormSchema),
    mode: "onBlur",
    defaultValues: TRANSACAO_VALORES_VAZIOS,
  });

  const tipoAtual = useWatch({ control: form.control, name: "tipo" }) as TipoTransacao;
  const origemAtual = useWatch({ control: form.control, name: "origem" });
  const modalidadeAtual = useWatch({ control: form.control, name: "modalidade" });
  const numParcelasAtual = useWatch({ control: form.control, name: "num_parcelas" });
  const valorAtual = useWatch({ control: form.control, name: "valor" });
  const valorParcelaAtual = useWatch({ control: form.control, name: "valor_parcela" });
  const tipoAnteriorRef = useRef<TipoTransacao | null>(null);

  useEffect(() => {
    if (open) {
      const valores = transacao
        ? transacaoParaFormulario(transacao)
        : { ...TRANSACAO_VALORES_VAZIOS, ...valoresIniciais };
      form.reset(valores);
      tipoAnteriorRef.current = valores.tipo;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, transacao]);

  useEffect(() => {
    if (tipoAnteriorRef.current !== null && tipoAnteriorRef.current !== tipoAtual) {
      form.setValue("categoria_id", "");
    }
    tipoAnteriorRef.current = tipoAtual;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipoAtual]);

  // Parcelado só faz sentido em Cartão — trocar para Conta volta sempre
  // para À vista (seção 5 da docstring acima), nunca deixa um estado
  // "parcelado numa conta" pendurado que a UI nem oferece mais.
  useEffect(() => {
    if (origemAtual === "CONTA" && modalidadeAtual === "PARCELADO") {
      form.setValue("modalidade", "AVISTA");
      form.setValue("num_parcelas", undefined);
      form.setValue("valor_parcela", "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [origemAtual]);

  const parcelado = origemAtual === "CARTAO" && !emEdicao && modalidadeAtual === "PARCELADO";
  // Preview: se o usuário digitou um valor de parcela customizado (compra
  // com juros embutidos, onde a parcela real não é valor_total/N), o
  // preview reflete ELE, não a divisão automática - mesmo valor que o
  // backend vai efetivamente usar em cada parcela (ver
  // `transacaoFormValuesParaParcelamento`/`ParcelamentoCreate.valor_parcela`).
  const valorParcelaCustomizado =
    valorParcelaAtual?.trim() && Number(valorParcelaAtual) > 0 ? Number(valorParcelaAtual) : null;
  const valorPorParcela =
    valorParcelaCustomizado ??
    (parcelado && numParcelasAtual && numParcelasAtual >= 2 && valorAtual
      ? Number(valorAtual) / numParcelasAtual
      : null);

  async function onSubmit(values: TransacaoFormValues) {
    try {
      if (emEdicao) {
        const payload = transacaoFormValuesParaAtualizacao(values);
        await atualizarTransacao.mutateAsync({ id: transacao.id, dados: payload });
        toast.success("Transação atualizada.");
      } else if (values.origem === "CARTAO" && values.modalidade === "PARCELADO") {
        const payload = transacaoFormValuesParaParcelamento(values);
        await criarParcelamento.mutateAsync(payload);
        const valorDaParcela = payload.valor_parcela
          ? Number(payload.valor_parcela)
          : Number(payload.valor_total) / payload.num_parcelas;
        toast.success(
          `Compra "${values.descricao}" parcelada em ${payload.num_parcelas}x de ${formatMoney(valorDaParcela)}.`,
        );
      } else {
        const payload = transacaoFormValuesParaCriacao(values);
        await criarTransacao.mutateAsync(payload);
        toast.success(`Transação "${values.descricao}" criada.`);
      }
      onClose();
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof TransacaoFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title={emEdicao ? "Editar transação" : "Nova transação"}
      description={
        emEdicao
          ? "A origem (conta ou cartão) não pode ser alterada — exclua e crie uma nova transação se precisar mudar."
          : "Registre uma receita, despesa ou movimentação."
      }
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="transacao-form-dialog" loading={salvando}>
            {emEdicao ? "Salvar alterações" : "Criar transação"}
          </SubmitButton>
        </FormActions>
      )}
    >
      <Form id="transacao-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <div className="flex gap-2">
          {TIPO_OPTIONS.map((opcao) => (
            <Button
              key={opcao.value}
              type="button"
              variant={tipoAtual === opcao.value ? "primary" : "secondary"}
              size="sm"
              className="flex-1"
              onClick={() => form.setValue("tipo", opcao.value as TipoTransacao, { shouldDirty: true })}
            >
              {opcao.label}
            </Button>
          ))}
        </div>

        <TextField name="descricao" label="Descrição" placeholder="Ex.: Supermercado, Salário, Aluguel" />
        <div className="grid grid-cols-2 gap-3">
          <CurrencyField name="valor" label="Valor" />
          <DateField name="data" label="Data" />
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-text-primary">Origem</p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={origemAtual === "CONTA" ? "primary" : "secondary"}
              size="sm"
              className="flex-1"
              disabled={emEdicao}
              onClick={() => form.setValue("origem", "CONTA", { shouldDirty: true })}
            >
              Conta
            </Button>
            <Button
              type="button"
              variant={origemAtual === "CARTAO" ? "primary" : "secondary"}
              size="sm"
              className="flex-1"
              disabled={emEdicao}
              onClick={() => form.setValue("origem", "CARTAO", { shouldDirty: true })}
            >
              Cartão de crédito
            </Button>
          </div>
          {origemAtual === "CONTA" ? (
            // `apenasAtivas={!emEdicao}` — na edição a conta pode ter sido
            // desativada desde que a transação foi criada; o campo é
            // somente leitura de qualquer forma, mas incluir inativas
            // garante que o nome continue resolvendo em vez de mostrar o
            // placeholder vazio para um id que existe, só não está na
            // lista "ativas".
            <AccountSelect name="conta_id" label="Conta" disabled={emEdicao} apenasAtivas={!emEdicao} />
          ) : (
            <CardSelect name="cartao_id" label="Cartão" disabled={emEdicao} apenasAtivas={!emEdicao} />
          )}
        </div>

        {origemAtual === "CONTA" && (
          <SelectField name="status" label="Status" options={STATUS_OPTIONS} />
        )}

        {/* À vista × Parcelado — só em criação, só no cartão (seção 5 da
            docstring do componente). */}
        {origemAtual === "CARTAO" && !emEdicao && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-text-primary">Como foi a compra?</p>
            <div className="flex gap-2">
              {MODALIDADE_OPTIONS.map((opcao) => (
                <Button
                  key={opcao.value}
                  type="button"
                  variant={modalidadeAtual === opcao.value ? "primary" : "secondary"}
                  size="sm"
                  className="flex-1"
                  onClick={() =>
                    form.setValue("modalidade", opcao.value as "AVISTA" | "PARCELADO", { shouldDirty: true })
                  }
                >
                  {opcao.label}
                </Button>
              ))}
            </div>
            {modalidadeAtual === "PARCELADO" && (
              <div className="space-y-1.5">
                <NumberField name="num_parcelas" label="Em quantas vezes" placeholder="Ex.: 12" />
                <CurrencyField
                  name="valor_parcela"
                  label="Valor da parcela"
                  optional
                  description="Deixe em branco para dividir o valor total igualmente. Preencha se a loja já cobra um valor fixo por parcela (com ou sem juros embutidos)."
                />
                {valorPorParcela != null && (
                  <p className="text-sm text-text-secondary">
                    {numParcelasAtual}x de{" "}
                    <span className="tabular font-medium text-text-primary">{formatMoney(valorPorParcela)}</span>
                    {valorParcelaCustomizado != null && " (valor informado)"}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        <CategorySelect
          name="categoria_id"
          label="Categoria"
          optional
          tipoTransacao={tipoAtual}
          apenasAtivas={!emEdicao}
        />
        {!parcelado && <TagMultiSelect name="tag_ids" label="Tags" optional apenasAtivas={!emEdicao} />}
      </Form>
    </FormDialog>
  );
}
