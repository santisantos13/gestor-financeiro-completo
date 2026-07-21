/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio real
 * (posse da conta, etc.) continua exclusiva do backend e chega como 422
 * tratado por `utils/errors.ts`. Ver docs/analise-arquitetural-frontend.md,
 * seção 5.
 *
 * Um único schema serve criação e edição: o formulário (`ContaFormDialog`)
 * sempre coleta o conjunto completo de campos, mesmo editando — a
 * diferença entre `ContaCreate`/`ContaUpdate` é responsabilidade de
 * `hooks/useContaQueries.ts` (que decide se chama `criar` ou `atualizar`),
 * não do schema de formulário.
 *
 * `instituicao` fica como `string` aqui (nunca `string | null`) de
 * propósito: um `<input>` nativo não tem uma representação sensata para
 * `null` (RHF atribuiria a string literal "null" ao DOM se o valor
 * default fosse `null`). A conversão "campo vazio → `null`" para bater com
 * `ContaCreate`/`ContaUpdate` acontece em `contaFormValuesParaPayload`,
 * fora do schema — mantém o schema livre de transform, que já teria
 * exigido tipos de entrada/saída separados no `useForm` (o `Form`
 * genérico da Etapa F5 assume um único `TFieldValues`).
 */
import { z } from "zod";
import type { ContaCreate, ContaUpdate } from "../types/conta";

export const contaFormSchema = z.object({
  nome: z.string().min(1, "Informe o nome da conta.").max(120, "Use no máximo 120 caracteres."),
  tipo: z.enum(["CORRENTE", "POUPANCA", "CARTEIRA", "INVESTIMENTO"], {
    error: "Selecione o tipo da conta.",
  }),
  saldo_inicial: z.string().min(1, "Informe o saldo inicial."),
  instituicao: z.string().max(120, "Use no máximo 120 caracteres."),
});

export type ContaFormValues = z.infer<typeof contaFormSchema>;

/** Converte o valor do formulário (`instituicao: string`, sempre) para o
 * payload que a API espera (`instituicao: string | null`) — string vazia
 * vira `null`, nunca uma string vazia enviada ao backend. */
export function contaFormValuesParaPayload(valores: ContaFormValues): ContaCreate & ContaUpdate {
  return {
    ...valores,
    instituicao: valores.instituicao.trim() === "" ? null : valores.instituicao,
  };
}
