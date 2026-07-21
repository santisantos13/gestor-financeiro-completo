/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio real
 * (conta_id obrigatório, parcelas_ja_pagas <= num_parcelas) continua
 * exclusiva do backend e chega como 422 tratado por `utils/errors.ts`.
 * Mesmo princípio de todo `schemas/*.ts` do projeto.
 *
 * Formulário simplificado (pedido do usuário: "não peça informações
 * burocráticas, apenas o valor da parcela, quantidade de parcelas totais e
 * pagas, data, instituição financeira, bem financiado, nome e se permite
 * quitação antecipada") — em vez de pedir `valor_financiado`/`taxa_juros`/
 * `cet`/`sistema_amortizacao`/`valor_entrada`/`numero_contrato`/
 * `categoria_id` (o backend continua exigindo alguns desses campos, mas
 * nenhum usuário comum pensa em "financiamento" como uma fórmula de
 * amortização — pensa em "pago R$X por mês"), o usuário digita direto o
 * valor de CADA parcela. `financiamentoFormValuesParaCriacao` reconstrói o
 * payload completo que o backend espera: `valor_financiado = valor_parcela
 * × num_parcelas` (multiplicação em centavos, sem risco de ponto
 * flutuante) e `taxa_juros = 0` — com taxa zero, PRICE degenera em divisão
 * simples (`test_cronograma_price_sem_juros_degenera_em_divisao_simples`,
 * backend), ou seja, TODAS as parcelas do cronograma saem exatamente iguais
 * ao valor digitado aqui. Nenhuma mudança de backend foi necessária.
 *
 * `conta_id` continua no formulário mesmo não tendo sido citado no pedido:
 * é a única informação estruturalmente obrigatória no backend
 * (`FinanciamentoService._validar_conta_obrigatoria`) que não é
 * "burocracia" — é de onde as parcelas realmente saem.
 */
import { z } from "zod";
import type { FinanciamentoCreate } from "../types/financiamento";

export const financiamentoFormSchema = z
  .object({
    descricao: z.string().min(1, "Informe o nome.").max(200, "Use no máximo 200 caracteres."),
    instituicao_financeira: z.string().min(1, "Informe a instituição financeira.").max(120),
    bem_financiado: z.string().max(200).optional(),
    conta_id: z.string().min(1, "Selecione a conta."),
    valor_parcela: z.string().min(1, "Informe o valor da parcela."),
    num_parcelas: z.number().optional(),
    data_inicio: z.string().min(1, "Informe a data de início."),
    permite_quitacao_antecipada: z.boolean(),
    /** Etapa de Onboarding — ver docstring de `FinanciamentoCreate`
     * (backend) e ponto 2 da docstring de `FinanciamentoFormDialog`. */
    parcelas_ja_pagas: z.number().optional(),
  })
  .refine((valores) => valores.num_parcelas != null && valores.num_parcelas >= 2, {
    message: "Informe o número de parcelas (mínimo 2).",
    path: ["num_parcelas"],
  })
  .refine(
    (valores) =>
      valores.parcelas_ja_pagas == null ||
      valores.num_parcelas == null ||
      valores.parcelas_ja_pagas <= valores.num_parcelas,
    {
      message: "Não pode ser maior que o número de parcelas.",
      path: ["parcelas_ja_pagas"],
    },
  );

export type FinanciamentoFormValues = z.infer<typeof financiamentoFormSchema>;

export const FINANCIAMENTO_VALORES_VAZIOS: FinanciamentoFormValues = {
  descricao: "",
  instituicao_financeira: "",
  bem_financiado: "",
  conta_id: "",
  valor_parcela: "",
  num_parcelas: undefined,
  data_inicio: "",
  permite_quitacao_antecipada: true,
  parcelas_ja_pagas: undefined,
};

/** `valor_parcela × num_parcelas` em centavos (inteiros) — evita qualquer
 * imprecisão de ponto flutuante que uma multiplicação direta de `Number`
 * decimal poderia introduzir. */
function valorFinanciadoTotal(valorParcela: string, numParcelas: number): string {
  const centavosPorParcela = Math.round(Number(valorParcela) * 100);
  const totalCentavos = centavosPorParcela * numParcelas;
  return (totalCentavos / 100).toFixed(2);
}

export function financiamentoFormValuesParaCriacao(valores: FinanciamentoFormValues): FinanciamentoCreate {
  const numParcelas = valores.num_parcelas as number;
  return {
    descricao: valores.descricao,
    instituicao_financeira: valores.instituicao_financeira,
    numero_contrato: null,
    valor_financiado: valorFinanciadoTotal(valores.valor_parcela, numParcelas),
    valor_entrada: null,
    bem_financiado: valores.bem_financiado?.trim() ? valores.bem_financiado.trim() : null,
    // taxa zero => PRICE degenera em parcelas fixas e iguais ao valor
    // digitado (ver docstring do arquivo) — nenhum juro é cobrado além do
    // que o próprio valor da parcela já embute.
    taxa_juros: "0",
    sistema_amortizacao: "PRICE",
    num_parcelas: numParcelas,
    cet: null,
    data_inicio: valores.data_inicio,
    permite_quitacao_antecipada: valores.permite_quitacao_antecipada,
    conta_id: Number(valores.conta_id),
    categoria_id: null,
    parcelas_ja_pagas: valores.parcelas_ja_pagas ?? 0,
  };
}
