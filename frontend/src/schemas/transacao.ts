/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio real
 * (XOR conta/cartão de verdade, compatibilidade de categoria, posse de
 * tag/conta/cartão) continua exclusiva do backend e chega como 422 tratado
 * por `utils/errors.ts`. Ver docs/analise-arquitetural-transacao-frontend.md,
 * seções 3 e 9.
 *
 * `origem` (`"CONTA" | "CARTAO"`) é um campo que só existe no formulário —
 * não faz parte de `TransacaoCreate`/`TransacaoUpdate` — usado só para
 * decidir qual dos dois selects (`AccountSelect`/`CardSelect`) fica visível
 * e qual dos dois ids (`conta_id`/`cartao_id`) é de fato enviado. Mesmo
 * raciocínio de `categoria_pai_id` em `schemas/categoria.ts`: todo id de
 * seleção fica como `string` no formulário (`""` = nenhum), nunca
 * `number | null` — comparação de `SelectOption.value` exige string.
 *
 * Um único schema serve criação e edição (mesmo padrão de todo o projeto),
 * mas os dois PAYLOADS divergem de verdade aqui — `TransacaoUpdate` nunca
 * aceita `conta_id`/`cartao_id` (imutáveis após a criação), então existem
 * duas funções de conversão (`paraCriacao`/`paraAtualizacao`) em vez de uma
 * só.
 *
 * `modalidade`/`num_parcelas` (pedido do usuário: "à vista ou parcelado em
 * X vezes" ao lançar uma compra no cartão) são campos que só existem no
 * formulário, igual `origem` — nunca fazem parte de `TransacaoCreate`.
 * `modalidade: "PARCELADO"` desvia a submissão inteira para
 * `POST /parcelamentos` (que gera as N `Transacao` reais no backend —
 * `ParcelamentoService._gerar_parcelas`), nunca para `POST /transacoes`.
 * Só relevante em modo CRIAÇÃO com `origem: "CARTAO"` — edição continua
 * 100% como antes (uma parcela já gerada não "vira" um parcelamento novo).
 *
 * `valor_parcela` (opcional, pedido do usuário: "permita que o usuário
 * escolha também o valor da parcela, caso ele não escolha, seja o valor
 * calculado pelo sistema... ajuda caso a compra tenha sido parcelada com
 * juros ou sem juros") — só aparece/importa quando `modalidade ===
 * "PARCELADO"`. Vazio = comportamento padrão (`valor_total / num_parcelas`,
 * calculado pelo backend); preenchido = esse valor exato é usado em TODAS
 * as parcelas (`ParcelamentoCreate.valor_parcela`, ver docstring lá).
 *
 * Não existe mais campo `meta_id` neste formulário (Refatoramento de
 * Metas/Transferências, ver
 * docs/analise-arquitetural-metas-transferencias.md, seção 6) — vincular
 * uma Transação nova a uma Meta não é mais possível; aportes/resgates
 * agora são Transferência real para o "cofrinho" da Meta
 * (`MetaAporteDialog`).
 */
import { z } from "zod";
import type { TransacaoCreate, TransacaoUpdate } from "../types/transacao";
import type { ParcelamentoCreate } from "../types/parcelamento";

export const transacaoFormSchema = z
  .object({
    tipo: z.enum(["RECEITA", "DESPESA"], { error: "Selecione o tipo da transação." }),
    valor: z.string().min(1, "Informe o valor."),
    data: z.string().min(1, "Informe a data."),
    descricao: z.string().min(1, "Informe a descrição.").max(200, "Use no máximo 200 caracteres."),
    origem: z.enum(["CONTA", "CARTAO"], { error: "Selecione a origem." }),
    conta_id: z.string(),
    cartao_id: z.string(),
    status: z.enum(["PENDENTE", "PAGO"]),
    categoria_id: z.string(),
    tag_ids: z.array(z.string()),
    modalidade: z.enum(["AVISTA", "PARCELADO"]),
    num_parcelas: z.number().optional(),
    valor_parcela: z.string().optional(),
  })
  .refine((valores) => valores.origem !== "CONTA" || valores.conta_id !== "", {
    message: "Selecione a conta.",
    path: ["conta_id"],
  })
  .refine((valores) => valores.origem !== "CARTAO" || valores.cartao_id !== "", {
    message: "Selecione o cartão.",
    path: ["cartao_id"],
  })
  .refine(
    (valores) =>
      valores.modalidade !== "PARCELADO" || (valores.num_parcelas != null && valores.num_parcelas >= 2),
    { message: "Informe em quantas vezes (mínimo 2).", path: ["num_parcelas"] },
  );

export type TransacaoFormValues = z.infer<typeof transacaoFormSchema>;

export const TRANSACAO_VALORES_VAZIOS: TransacaoFormValues = {
  tipo: "DESPESA",
  valor: "",
  data: "",
  descricao: "",
  origem: "CONTA",
  conta_id: "",
  cartao_id: "",
  status: "PENDENTE",
  categoria_id: "",
  tag_ids: [],
  modalidade: "AVISTA",
  num_parcelas: undefined,
  valor_parcela: "",
};

/** Payload de `POST /transacoes` — único momento em que `conta_id`/
 * `cartao_id` são enviados (seção 3 do documento: imutáveis depois). */
export function transacaoFormValuesParaCriacao(valores: TransacaoFormValues): TransacaoCreate {
  return {
    tipo: valores.tipo,
    valor: valores.valor,
    data: valores.data,
    descricao: valores.descricao,
    status: valores.origem === "CONTA" ? valores.status : undefined,
    categoria_id: valores.categoria_id === "" ? null : Number(valores.categoria_id),
    conta_id: valores.origem === "CONTA" ? Number(valores.conta_id) : null,
    cartao_id: valores.origem === "CARTAO" ? Number(valores.cartao_id) : null,
    tag_ids: valores.tag_ids.map(Number),
  };
}

/** Payload de `POST /parcelamentos` — só chamado quando
 * `modalidade === "PARCELADO"` (sempre `origem === "CARTAO"` na prática,
 * já que a UI só oferece o toggle nesse caso). Diferente de
 * `transacaoFormValuesParaCriacao`: não envia `tipo`/`status`/`tag_ids`
 * (o schema `ParcelamentoCreate` não tem esses campos — toda parcela
 * gerada é sempre `DESPESA`, `PAGO`, sem tags, decisão do backend, não
 * uma omissão daqui). */
export function transacaoFormValuesParaParcelamento(valores: TransacaoFormValues): ParcelamentoCreate {
  return {
    descricao: valores.descricao,
    valor_total: valores.valor,
    num_parcelas: valores.num_parcelas as number,
    // vazio = deixa o backend calcular (valor_total / num_parcelas, padrão
    // de sempre); preenchido = usa esse valor exato em cada parcela (ver
    // docstring do arquivo e de `ParcelamentoCreate.valor_parcela`).
    valor_parcela: valores.valor_parcela?.trim() ? valores.valor_parcela : null,
    data_inicio: valores.data,
    categoria_id: valores.categoria_id === "" ? null : Number(valores.categoria_id),
    cartao_id: valores.origem === "CARTAO" ? Number(valores.cartao_id) : null,
    conta_id: valores.origem === "CONTA" ? Number(valores.conta_id) : null,
  };
}

/** Payload de `PATCH /transacoes/{id}` — nunca inclui `conta_id`/
 * `cartao_id` (o backend rejeitaria/ignoraria; o schema `TransacaoUpdate`
 * nem declara esses campos). */
export function transacaoFormValuesParaAtualizacao(valores: TransacaoFormValues): TransacaoUpdate {
  return {
    tipo: valores.tipo,
    valor: valores.valor,
    data: valores.data,
    descricao: valores.descricao,
    status: valores.origem === "CONTA" ? valores.status : undefined,
    categoria_id: valores.categoria_id === "" ? null : Number(valores.categoria_id),
    tag_ids: valores.tag_ids.map(Number),
  };
}
