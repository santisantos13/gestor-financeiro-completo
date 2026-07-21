/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio
 * real (nome único por usuário, reativação implícita ao colidir com tag
 * desativada) continua exclusiva do backend e chega como 409 tratado por
 * `utils/errors.ts`, mesmo caminho já usado para e-mail duplicado em
 * `RegistrarPage.tsx` desde a F1. Ver
 * docs/analise-arquitetural-tag-frontend.md, seção 2.2.
 *
 * `cor` segue o mesmo padrão de `schemas/categoria.ts`: string sempre
 * (nunca `null`) no formulário, `""` vira `null` no payload —
 * `ColorField` não tem uma representação sensata de `null` para um
 * `<input>` nativo.
 */
import { z } from "zod";
import { eCorHexValida } from "../lib/color";
import type { TagCreate, TagUpdate } from "../types/tag";

export const tagFormSchema = z.object({
  nome: z.string().min(1, "Informe o nome da tag.").max(60, "Use no máximo 60 caracteres."),
  cor: z
    .string()
    .max(7)
    .refine((valor) => valor === "" || eCorHexValida(valor), "Use um hex válido, ex.: #34D399."),
});

export type TagFormValues = z.infer<typeof tagFormSchema>;

/** Converte o valor do formulário para o payload que a API espera — `cor`
 * vazia vira `null`. */
export function tagFormValuesParaPayload(valores: TagFormValues): TagCreate & TagUpdate {
  return {
    nome: valores.nome,
    cor: valores.cor.trim() === "" ? null : valores.cor,
  };
}
