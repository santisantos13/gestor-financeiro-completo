/**
 * Validação de FORMATO/obrigatoriedade só para UX — mesmo espírito de
 * `schemas/cartao.ts`. Dois formulários pequenos (nunca um
 * `FaturaFormDialog` genérico — Fatura não tem PATCH, seção 6 de
 * `docs/analise-arquitetural-fatura-frontend.md`): criar um ciclo novo, e
 * registrar um pagamento numa fatura existente.
 */
import { z } from "zod";
import type {
  FaturaAjusteManualUpdate,
  FaturaAjustePosFechamentoCreate,
  FaturaCreate,
  FaturaImportarCreate,
  FaturaPagamentoCreate,
  FaturaPagamentoEmLoteCreate,
} from "../types/fatura";

/** `mes_referencia` no formulário é só `"AAAA-MM"` (o `<input type="month">`
 * nativo do navegador não expõe dia) — o dia 1 é adicionado só na hora de
 * montar o payload (`novaFaturaFormValuesParaPayload`), nunca guardado no
 * estado do formulário.
 *
 * `historica`/`valor_total` (Etapa de Onboarding, pedido do usuário: "só
 * o valor da fatura que ele já pagou antes") são campos que só existem no
 * formulário, mesmo raciocínio de `modalidade`/`num_parcelas` em
 * `schemas/transacao.ts` — `historica: true` desvia a submissão inteira
 * para `POST /faturas/importar` (`FaturaImportarCreate`) em vez de
 * `POST /faturas` (`FaturaCreate`, que não tem `valor_total`). */
export const novaFaturaFormSchema = z
  .object({
    mes_referencia: z.string().min(1, "Selecione o mês de referência."),
    historica: z.boolean(),
    valor_total: z.string(),
  })
  .refine((valores) => !valores.historica || valores.valor_total.trim() !== "", {
    message: "Informe o valor total da fatura.",
    path: ["valor_total"],
  });

export type NovaFaturaFormValues = z.infer<typeof novaFaturaFormSchema>;

export function novaFaturaFormValuesParaPayload(
  valores: NovaFaturaFormValues,
  cartaoId: number,
): FaturaCreate {
  return { cartao_id: cartaoId, mes_referencia: `${valores.mes_referencia}-01` };
}

/** Payload de `POST /faturas/importar` — só chamado quando
 * `historica === true` (ver docstring do schema acima). */
export function novaFaturaFormValuesParaImportPayload(
  valores: NovaFaturaFormValues,
  cartaoId: number,
): FaturaImportarCreate {
  return {
    cartao_id: cartaoId,
    mes_referencia: `${valores.mes_referencia}-01`,
    valor_total: valores.valor_total,
  };
}

export const pagamentoFormSchema = z.object({
  valor: z.string().min(1, "Informe o valor."),
  data: z.string().min(1, "Informe a data."),
  descricao: z.string().max(200, "Use no máximo 200 caracteres.").optional(),
});

export type PagamentoFormValues = z.infer<typeof pagamentoFormSchema>;

export function pagamentoFormValuesParaPayload(valores: PagamentoFormValues): FaturaPagamentoCreate {
  return {
    valor: valores.valor,
    data: valores.data,
    descricao: valores.descricao?.trim() ? valores.descricao.trim() : undefined,
  };
}

/** Pedido explícito do usuário: "seria interessante poder pagar todas
 * selecionadas". Só a data do pagamento — nenhum valor aqui, cada fatura
 * é paga pelo seu próprio restante, calculado pelo backend (ver
 * `FaturaPagamentoEmLoteCreate`). */
export const pagamentoEmLoteFormSchema = z.object({
  data: z.string().min(1, "Informe a data."),
});

export type PagamentoEmLoteFormValues = z.infer<typeof pagamentoEmLoteFormSchema>;

export function pagamentoEmLoteFormValuesParaPayload(
  valores: PagamentoEmLoteFormValues,
  faturaIds: number[],
): FaturaPagamentoEmLoteCreate {
  return { fatura_ids: faturaIds, data: valores.data };
}

/** Pedido explícito do usuário: informar o saldo já utilizado do cartão
 * independentemente de transações. Um único campo, sem nenhuma decisão de
 * negócio aqui (o backend rejeita valor negativo e fatura não-ABERTA). */
export const ajusteSaldoInicialFormSchema = z.object({
  ajuste_manual: z.string().min(1, "Informe o valor já utilizado."),
});

export type AjusteSaldoInicialFormValues = z.infer<typeof ajusteSaldoInicialFormSchema>;

export function ajusteSaldoInicialFormValuesParaPayload(
  valores: AjusteSaldoInicialFormValues,
): FaturaAjusteManualUpdate {
  return { ajuste_manual: valores.ajuste_manual };
}

/** Pedido explícito do usuário (2026-07-20): "quero adicionar uma
 * transação em uma fatura que já foi fechada e paga, porém tinha
 * esquecido dela antes" - só o valor esquecido, sem nenhuma decisão de
 * negócio aqui (o backend rejeita valor <= 0 e fatura ainda ABERTA). */
export const ajustePosFechamentoFormSchema = z.object({
  valor: z.string().min(1, "Informe o valor esquecido."),
});

export type AjustePosFechamentoFormValues = z.infer<typeof ajustePosFechamentoFormSchema>;

export function ajustePosFechamentoFormValuesParaPayload(
  valores: AjustePosFechamentoFormValues,
): FaturaAjustePosFechamentoCreate {
  return { valor: valores.valor };
}
