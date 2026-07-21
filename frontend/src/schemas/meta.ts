/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio real
 * (descrição única por usuário com reativação) continua exclusiva do
 * backend e chega como 409/422 tratado por `utils/errors.ts`. Mesmo padrão
 * de todo `schemas/<entidade>.ts` do projeto. Ver
 * docs/analise-arquitetural-metas-frontend.md, seção 2.1/2.2.
 *
 * `conta_id` NÃO existe mais aqui (Refatoramento de Metas/Transferências,
 * ver docs/analise-arquitetural-metas-transferencias.md) — o "cofrinho" é
 * sempre provisionado automaticamente pelo backend, nunca escolhido pelo
 * usuário no formulário.
 */
import { z } from "zod";
import type { FrequenciaContribuicao, MetaCreate, MetaUpdate } from "../types/meta";

export const metaFormSchema = z.object({
  descricao: z.string().min(1, "Informe a descrição.").max(200, "Use no máximo 200 caracteres."),
  valor_alvo: z.string().min(1, "Informe o valor da meta."),
  // Vazio = "sem prazo definido" (data_alvo é opcional no backend) — mesmo
  // tratamento de campo de data opcional já usado no projeto (`DateField`
  // aceita `""` como "nenhum valor").
  data_alvo: z.string(),
  // "" = nenhuma frequência escolhida (Refinamento de Metas) — mesmo
  // padrão de campo opcional acima; sem frequência, a meta simplesmente
  // não ganha "contribuição sugerida por período".
  frequencia_contribuicao: z.string(),
});

export type MetaFormValues = z.infer<typeof metaFormSchema>;

export const META_VALORES_VAZIOS: MetaFormValues = {
  descricao: "",
  valor_alvo: "",
  data_alvo: "",
  frequencia_contribuicao: "",
};

function frequenciaDoFormulario(valor: string): FrequenciaContribuicao | null {
  return valor === "" ? null : (valor as FrequenciaContribuicao);
}

export function metaFormValuesParaCriacao(valores: MetaFormValues): MetaCreate {
  return {
    descricao: valores.descricao,
    valor_alvo: valores.valor_alvo,
    data_alvo: valores.data_alvo.trim() ? valores.data_alvo : null,
    frequencia_contribuicao: frequenciaDoFormulario(valores.frequencia_contribuicao),
  };
}

export function metaFormValuesParaAtualizacao(valores: MetaFormValues): MetaUpdate {
  return {
    descricao: valores.descricao,
    valor_alvo: valores.valor_alvo,
    data_alvo: valores.data_alvo.trim() ? valores.data_alvo : null,
    frequencia_contribuicao: frequenciaDoFormulario(valores.frequencia_contribuicao),
  };
}
