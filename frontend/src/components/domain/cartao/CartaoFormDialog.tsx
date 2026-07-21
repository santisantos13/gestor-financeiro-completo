import { useEffect } from "react";
import { useController, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FormDialog } from "../../ui/FormDialog";
import { Form } from "../../ui/Form";
import { FormActions } from "../../ui/FormActions";
import { SubmitButton } from "../../ui/SubmitButton";
import { CancelButton } from "../../ui/CancelButton";
import { TextField } from "../../ui/TextField";
import { CurrencyField } from "../../ui/CurrencyField";
import { NumberField } from "../../ui/NumberField";
import { BankPicker } from "../../ui/BankPicker";
import { CardBrandPicker } from "../../ui/CardBrandPicker";
import { AccountSelect } from "../conta/AccountSelect";
import { CartaoVisual } from "./CartaoVisual";
import { getCardThemeVariants, lerVariantePreferida, salvarVariantePreferida } from "../../../lib/cardThemes";
import { cartaoFormSchema, cartaoFormValuesParaPayload, type CartaoFormValues } from "../../../schemas/cartao";
import { useCriarCartao, useAtualizarCartao } from "../../../hooks/useCartaoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage, getFieldErrors } from "../../../utils/errors";
import type { CartaoRead } from "../../../types/cartao";
import type { Control } from "react-hook-form";

const VALORES_VAZIOS: CartaoFormValues = {
  nome: "",
  conta_pagamento_id: "",
  instituicao: "",
  bandeira: "VISA",
  ultimos_quatro_digitos: "",
  limite: "",
  dia_fechamento: 1,
  dia_vencimento: 10,
  saldo_inicial_utilizado: "",
  variante_tema: null,
};

function cartaoParaFormulario(cartao: CartaoRead): CartaoFormValues {
  return {
    nome: cartao.nome,
    conta_pagamento_id: String(cartao.conta_pagamento_id),
    instituicao: cartao.instituicao,
    bandeira: cartao.bandeira,
    ultimos_quatro_digitos: cartao.ultimos_quatro_digitos,
    limite: cartao.limite,
    dia_fechamento: cartao.dia_fechamento,
    dia_vencimento: cartao.dia_vencimento,
    variante_tema: lerVariantePreferida(cartao.id),
  };
}

/** Preview ao vivo do `CartaoVisual` conforme o usuário preenche o
 * formulário — mesmo `useWatch` escopado de `InstituicaoPreview`
 * (`ContaFormDialog`), só este componente re-renderiza a cada tecla. Em
 * criação (`cartao` nulo), ainda não existe `limite_disponivel` real — usa
 * o próprio `limite` digitado como disponível (0% utilizado), preview
 * honesto do que o cartão vai parecer assim que criado. */
function CartaoPreview({ control, cartao }: { control: Control<CartaoFormValues>; cartao?: CartaoRead | null }) {
  const nome = useWatch({ control, name: "nome" });
  const instituicao = useWatch({ control, name: "instituicao" });
  const bandeira = useWatch({ control, name: "bandeira" });
  const ultimosQuatroDigitos = useWatch({ control, name: "ultimos_quatro_digitos" });
  const limite = useWatch({ control, name: "limite" });
  const diaFechamento = useWatch({ control, name: "dia_fechamento" });
  const diaVencimento = useWatch({ control, name: "dia_vencimento" });
  const varianteTema = useWatch({ control, name: "variante_tema" });

  return (
    <CartaoVisual
      nome={nome || "Nome do cartão"}
      instituicao={instituicao || null}
      bandeira={bandeira || "OUTRA"}
      ultimosQuatroDigitos={ultimosQuatroDigitos || "0000"}
      limite={limite || "0"}
      limiteDisponivel={cartao ? cartao.limite_disponivel : limite || "0"}
      diaFechamento={diaFechamento}
      diaVencimento={diaVencimento}
      variantId={varianteTema}
    />
  );
}

/** Seletor de variante visual (Ajustes de UX/UI, item 2) — só aparece
 * quando a instituição reconhecida tem mais de uma variante de tema
 * (`lib/cardThemes.ts`); a maioria das instituições tem só a variante de
 * marca padrão, e uma instituição não reconhecida não tem nenhuma escolha
 * real a fazer. Preferência é puramente visual, nunca enviada ao backend —
 * persistida em `localStorage` só no submit bem-sucedido (`onSubmit`
 * abaixo), não a cada clique aqui (evita gravar uma preferência para um
 * cartão que o usuário pode acabar não salvando). */
function VariantePicker({ control }: { control: Control<CartaoFormValues> }) {
  const instituicao = useWatch({ control, name: "instituicao" });
  const { field } = useController({ control, name: "variante_tema" });
  const variantes = getCardThemeVariants(instituicao);

  if (variantes.length <= 1) return null;

  return (
    <div>
      <p className="mb-1.5 text-sm text-text-secondary">Variante visual</p>
      <div className="flex flex-wrap gap-2">
        {variantes.map((variante, index) => {
          const selecionada = field.value === variante.id || (!field.value && index === 0);
          return (
            <button
              key={variante.id}
              type="button"
              title={variante.label}
              onClick={() => field.onChange(variante.id)}
              aria-pressed={selecionada}
              className={`h-8 w-8 rounded-full border-2 transition-transform duration-fast ease-out hover:scale-110 ${
                selecionada ? "border-accent" : "border-transparent"
              }`}
              style={{ background: `linear-gradient(135deg, ${variante.gradiente[0]}, ${variante.gradiente[1]})` }}
            />
          );
        })}
      </div>
    </div>
  );
}

export interface CartaoFormDialogProps {
  open: boolean;
  cartao?: CartaoRead | null;
  onClose: () => void;
  /** Chamado só em modo CRIAÇÃO, com o cartão recém-criado — usado por
   * `CartoesPage` para levar o usuário direto à página de detalhes do
   * cartão novo, onde fica "Registrar saldo já gasto neste cartão" (ajuste
   * de saldo inicial, seção 6.3 do Refinamento de UX/Dashboard/Cartões).
   * Pedido do usuário: quem já usava o cartão antes de entrar no app
   * precisa achar essa ação sem precisar já saber que ela existe — landing
   * direto no detalhe do cartão novo resolve isso sem nenhum componente ou
   * regra nova. Opcional para não quebrar nenhum outro uso deste diálogo. */
  onCriado?: (cartao: CartaoRead) => void;
}

/**
 * Modal de criar/editar Cartão — compõe integralmente a infraestrutura de
 * Conta/Categoria/Tag (`FormDialog`/`Form`/`*Field`,
 * `useCriarCartao`/`useAtualizarCartao`) mais os componentes de domínio de
 * Cartão (`CartaoVisual`, `VariantePicker`). Nenhuma regra de negócio
 * aqui: o schema Zod só valida formato/obrigatoriedade; um 422/409 real do
 * backend é mapeado campo a campo via `getFieldErrors` + `form.setError`,
 * mesma mecânica de todo formulário do projeto.
 *
 * Revisão de UX de Cartões
 * (`docs/analise-arquitetural-revisao-ux-cartoes.md`, seção 8): o modo
 * "somente leitura"/toggle "Editar" que este componente tinha desde a
 * Etapa F9 foi removido — com o card inteiro clicável no grid de
 * `/cartoes` e a página de detalhes cobrindo toda a visualização, abrir
 * este modal só para "ver" (sem editar) virou fricção redundante. Este
 * diálogo agora serve só para **criar** e **editar**.
 */
export function CartaoFormDialog({ open, cartao, onClose, onCriado }: CartaoFormDialogProps) {
  const toast = useToast();
  const criarCartao = useCriarCartao();
  const atualizarCartao = useAtualizarCartao();
  const emEdicao = cartao != null;
  const salvando = criarCartao.isPending || atualizarCartao.isPending;

  const form = useForm<CartaoFormValues>({
    resolver: zodResolver(cartaoFormSchema),
    mode: "onBlur",
    defaultValues: VALORES_VAZIOS,
  });

  useEffect(() => {
    if (open) {
      form.reset(cartao ? cartaoParaFormulario(cartao) : VALORES_VAZIOS);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, cartao]);

  async function onSubmit(values: CartaoFormValues) {
    const payload = cartaoFormValuesParaPayload(values);
    try {
      let cartaoSalvo: CartaoRead;
      if (emEdicao) {
        // O campo "Saldo já utilizado" não aparece no modo edição (só
        // existe no diálogo de criação) - remover do payload antes do
        // PATCH evita que `saldo_inicial_utilizado` seja resetado para
        // "0" ao editar qualquer outro campo do cartão (o valor já
        // declarado só muda via `AjusteSaldoInicialDialog`, nunca aqui).
        delete payload.saldo_inicial_utilizado;
        cartaoSalvo = await atualizarCartao.mutateAsync({ id: cartao.id, dados: payload });
        toast.success(`Cartão "${values.nome}" atualizado.`);
      } else {
        cartaoSalvo = await criarCartao.mutateAsync(payload);
        toast.success(`Cartão "${values.nome}" criado.`);
      }
      if (values.variante_tema) {
        salvarVariantePreferida(cartaoSalvo.id, values.variante_tema);
      }
      onClose();
      if (!emEdicao) {
        onCriado?.(cartaoSalvo);
      }
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors) {
        for (const [campo, mensagem] of Object.entries(fieldErrors)) {
          form.setError(campo as keyof CartaoFormValues, { type: "server", message: mensagem });
        }
      }
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <FormDialog
      open={open}
      title={emEdicao ? "Editar cartão" : "Novo cartão"}
      description={
        emEdicao
          ? "Altere os dados do cartão. O limite disponível continua calculado pelo histórico de gastos."
          : "Cadastre um cartão de crédito ligado a uma conta de pagamento."
      }
      isDirty={form.formState.isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <FormActions>
          <CancelButton onClick={requestClose}>Cancelar</CancelButton>
          <SubmitButton form="cartao-form-dialog" loading={salvando}>
            {emEdicao ? "Salvar alterações" : "Criar cartão"}
          </SubmitButton>
        </FormActions>
      )}
    >
      <div className="mb-4">
        <CartaoPreview control={form.control} cartao={cartao} />
      </div>
      <Form id="cartao-form-dialog" form={form} onSubmit={onSubmit} className="space-y-4">
        <TextField name="nome" label="Nome" placeholder="Ex.: Nubank Roxinho, Inter Gold" />
        <AccountSelect name="conta_pagamento_id" label="Conta de pagamento" />
        <BankPicker name="instituicao" label="Instituição" />
        <VariantePicker control={form.control} />
        <CardBrandPicker name="bandeira" label="Bandeira" />
        <TextField name="ultimos_quatro_digitos" label="Últimos 4 dígitos" placeholder="1234" />
        <CurrencyField name="limite" label="Limite" />
        <div className="grid grid-cols-2 gap-3">
          <NumberField name="dia_fechamento" label="Dia de fechamento" decimalPlaces={0} />
          <NumberField name="dia_vencimento" label="Dia de vencimento" decimalPlaces={0} />
        </div>
        {/* "Estado Inicial do Cartão" (Sprint de Refinamento Premium) - só
            aparece na CRIAÇÃO: quem já usava o cartão antes de entrar no
            app diz de cara quanto já está gasto, sem nenhuma Fatura sendo
            criada nos bastidores. Depois de criado, esse valor é editado
            via "Informar saldo já utilizado" (AjusteSaldoInicialDialog,
            CartaoDetalhePage) - não duplicamos o campo aqui no modo
            edição para não ter dois lugares editando a mesma coisa. */}
        {!emEdicao && (
          <CurrencyField
            name="saldo_inicial_utilizado"
            label="Saldo já utilizado (opcional)"
            placeholder="Quanto já está gasto neste cartão hoje"
          />
        )}
      </Form>
    </FormDialog>
  );
}
