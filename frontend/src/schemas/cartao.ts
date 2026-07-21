/**
 * Validação de FORMATO/obrigatoriedade só para UX — regra de negócio real
 * (posse de `conta_pagamento_id`, 409 de nome duplicado, reativação
 * implícita) continua exclusiva do backend. Mesmo espírito de
 * `schemas/conta.ts`: um único schema serve criação e edição, a diferença
 * entre `CartaoCreate`/`CartaoUpdate` é responsabilidade de
 * `hooks/useCartaoQueries.ts`.
 *
 * Diferente de Conta (`instituicao` opcional), em Cartão `instituicao` é
 * OBRIGATÓRIA no backend (`Field(min_length=1, ...)`, sem `| None` em
 * `CartaoCreate`) — reflete essa obrigatoriedade real, não uma escolha de
 * UX independente (ver docs/analise-arquitetural-cartao-frontend.md, seção
 * 12).
 */
import { z } from "zod";
import type { CartaoCreate, CartaoUpdate } from "../types/cartao";

export const cartaoFormSchema = z.object({
  nome: z.string().min(1, "Informe o nome do cartão.").max(120, "Use no máximo 120 caracteres."),
  conta_pagamento_id: z.string().min(1, "Selecione a conta de pagamento."),
  instituicao: z.string().min(1, "Informe a instituição.").max(120, "Use no máximo 120 caracteres."),
  bandeira: z.enum(["VISA", "MASTERCARD", "ELO", "AMERICAN_EXPRESS", "HIPERCARD", "DINERS_CLUB", "OUTRA"], {
    error: "Selecione a bandeira.",
  }),
  ultimos_quatro_digitos: z.string().regex(/^\d{4}$/, "Informe os 4 últimos dígitos."),
  limite: z.string().min(1, "Informe o limite."),
  dia_fechamento: z.number({ error: "Informe o dia de fechamento." }).min(1, "Mínimo 1.").max(31, "Máximo 31."),
  dia_vencimento: z.number({ error: "Informe o dia de vencimento." }).min(1, "Mínimo 1.").max(31, "Máximo 31."),
  /** "Estado Inicial do Cartão" — opcional, default vazio (tratado como 0
   * no payload). Só aparece no formulário de CRIAÇÃO (ver
   * `CartaoFormDialog`) - depois de criado, é editado por
   * `AjusteSaldoInicialDialog`. */
  saldo_inicial_utilizado: z.string().optional(),
  /** Só existe no formulário — nunca enviado ao backend (ver
   * `cartaoFormValuesParaPayload`). Preferência puramente visual persistida
   * em `localStorage` por `lib/cardThemes.ts`. */
  variante_tema: z.string().nullable(),
});

export type CartaoFormValues = z.infer<typeof cartaoFormSchema>;

/** Converte o valor do formulário para o payload que a API espera —
 * `conta_pagamento_id` vira `number` (`AccountSelect` devolve `string`,
 * mesmo tratamento de qualquer `SearchSelect`); `variante_tema` nunca é
 * enviado (persistido à parte via `lib/cardThemes.ts`). */
export function cartaoFormValuesParaPayload(valores: CartaoFormValues): CartaoCreate & CartaoUpdate {
  return {
    nome: valores.nome,
    conta_pagamento_id: Number(valores.conta_pagamento_id),
    instituicao: valores.instituicao,
    bandeira: valores.bandeira,
    ultimos_quatro_digitos: valores.ultimos_quatro_digitos,
    limite: valores.limite,
    dia_fechamento: valores.dia_fechamento,
    dia_vencimento: valores.dia_vencimento,
    saldo_inicial_utilizado: valores.saldo_inicial_utilizado || "0",
  };
}
