/**
 * Validação de FORMATO/obrigatoriedade só para UX - a regra de negócio real
 * (origem ≠ destino, posse/ativo das duas contas) continua exclusiva do
 * backend e chega como 422 tratado por `utils/errors.ts`. Ver
 * docs/analise-arquitetural-transferencias-frontend.md, seções 5 e 9.
 *
 * A checagem "origem ≠ destino" feita aqui via `.refine` é só uma
 * antecipação de UX (feedback imediato antes de bater no backend) - a
 * validação real e definitiva continua sendo
 * `TransferenciaService._validar_estrutura` no servidor, mesmo princípio já
 * usado em todo `schemas/*.ts` do projeto.
 */
import { z } from "zod";
import type { TransferenciaCreate } from "../types/transferencia";

export const transferenciaFormSchema = z
  .object({
    conta_origem_id: z.string().min(1, "Selecione a conta de origem."),
    conta_destino_id: z.string().min(1, "Selecione a conta de destino."),
    valor: z.string().min(1, "Informe o valor."),
    data: z.string().min(1, "Informe a data."),
    descricao: z.string().max(200, "Use no máximo 200 caracteres.").optional(),
  })
  .refine((valores) => valores.conta_origem_id === "" || valores.conta_origem_id !== valores.conta_destino_id, {
    message: "A conta de destino precisa ser diferente da origem.",
    path: ["conta_destino_id"],
  });

export type TransferenciaFormValues = z.infer<typeof transferenciaFormSchema>;

export const TRANSFERENCIA_VALORES_VAZIOS: TransferenciaFormValues = {
  conta_origem_id: "",
  conta_destino_id: "",
  valor: "",
  data: "",
  descricao: "",
};

export function transferenciaFormValuesParaCriacao(valores: TransferenciaFormValues): TransferenciaCreate {
  return {
    conta_origem_id: Number(valores.conta_origem_id),
    conta_destino_id: Number(valores.conta_destino_id),
    valor: valores.valor,
    data: valores.data,
    descricao: valores.descricao?.trim() ? valores.descricao.trim() : null,
  };
}
