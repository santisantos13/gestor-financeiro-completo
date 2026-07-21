/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio
 * real (visibilidade, somente-leitura de categoria de sistema, ciclo de
 * hierarquia, subcategoria ativa) continua exclusiva do backend e chega
 * como 403/422 tratado por `utils/errors.ts`. Ver
 * docs/analise-arquitetural-categoria-frontend.md, seção 6.
 *
 * `categoria_pai_id` fica como `string` aqui (`""` = sem pai), não
 * `number | null` — mesmo raciocínio já usado para `instituicao` em
 * `schemas/conta.ts`: todo componente de seleção do Design System
 * (`Select`/`SearchSelect`, base de `CategorySelect`) trabalha com
 * `SelectOption.value: string`; guardar o id como `number` no formulário
 * faria a comparação `option.value === field.value` nunca bater. A
 * conversão para `number | null` no payload acontece em
 * `categoriaFormValuesParaPayload`, fora do schema.
 *
 * `cor`/`icone` seguem o mesmo padrão: string sempre (nunca `null`) no
 * formulário, `""` vira `null` no payload — `ColorField`/`IconField` não
 * têm uma representação sensata de `null` para um `<input>`/botão nativo,
 * mesma razão de `instituicao`.
 */
import { z } from "zod";
import { eCorHexValida } from "../lib/color";
import type { CategoriaCreate, CategoriaUpdate } from "../types/categoria";

export const categoriaFormSchema = z.object({
  nome: z.string().min(1, "Informe o nome da categoria.").max(80, "Use no máximo 80 caracteres."),
  tipo: z.enum(["RECEITA", "DESPESA", "AMBOS"], {
    error: "Selecione o tipo da categoria.",
  }),
  cor: z
    .string()
    .max(7)
    .refine((valor) => valor === "" || eCorHexValida(valor), "Use um hex válido, ex.: #34D399."),
  icone: z.string().max(40, "Use no máximo 40 caracteres."),
  categoria_pai_id: z.string(),
});

export type CategoriaFormValues = z.infer<typeof categoriaFormSchema>;

/** Converte o valor do formulário para o payload que a API espera —
 * `cor`/`icone` vazios viram `null`; `categoria_pai_id` vazio vira `null`,
 * senão é convertido de volta para `number`. */
export function categoriaFormValuesParaPayload(
  valores: CategoriaFormValues,
): CategoriaCreate & CategoriaUpdate {
  return {
    nome: valores.nome,
    tipo: valores.tipo,
    cor: valores.cor.trim() === "" ? null : valores.cor,
    icone: valores.icone.trim() === "" ? null : valores.icone,
    categoria_pai_id: valores.categoria_pai_id === "" ? null : Number(valores.categoria_pai_id),
  };
}
