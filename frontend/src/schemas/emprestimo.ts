/**
 * Mesmo raciocínio de `schemas/financiamento.ts` (validação de formato só
 * para UX, `taxa_juros`/`cet` digitados como percentual e convertidos para
 * fração de 4 casas na hora do payload). Diferença de Financiamento:
 * `valor_liberado` é obrigatório (sem `valor_entrada`), `finalidade`
 * substitui `bem_financiado`.
 */
import { z } from "zod";
import type { EmprestimoCreate } from "../types/emprestimo";

function percentualParaFracao(percentual: string): string {
  if (!percentual) return "0";
  return (Number(percentual) / 100).toFixed(4);
}

export const emprestimoFormSchema = z
  .object({
    descricao: z.string().min(1, "Informe a descrição.").max(200, "Use no máximo 200 caracteres."),
    instituicao_financeira: z.string().min(1, "Informe a instituição financeira.").max(120),
    numero_contrato: z.string().max(60).optional(),
    valor_liberado: z.string().min(1, "Informe o valor liberado."),
    finalidade: z.string().max(120).optional(),
    taxa_juros: z.string().min(1, "Informe a taxa de juros mensal."),
    sistema_amortizacao: z.enum(["PRICE", "SAC"]),
    num_parcelas: z.number().optional(),
    cet: z.string().optional(),
    data_inicio: z.string().min(1, "Informe a data de início."),
    permite_quitacao_antecipada: z.boolean(),
    conta_id: z.string().min(1, "Selecione a conta."),
    categoria_id: z.string(),
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

export type EmprestimoFormValues = z.infer<typeof emprestimoFormSchema>;

export const EMPRESTIMO_VALORES_VAZIOS: EmprestimoFormValues = {
  descricao: "",
  instituicao_financeira: "",
  numero_contrato: "",
  valor_liberado: "",
  finalidade: "",
  taxa_juros: "",
  sistema_amortizacao: "PRICE",
  num_parcelas: undefined,
  cet: "",
  data_inicio: "",
  permite_quitacao_antecipada: true,
  conta_id: "",
  categoria_id: "",
  parcelas_ja_pagas: undefined,
};

export function emprestimoFormValuesParaCriacao(valores: EmprestimoFormValues): EmprestimoCreate {
  return {
    descricao: valores.descricao,
    instituicao_financeira: valores.instituicao_financeira,
    numero_contrato: valores.numero_contrato?.trim() ? valores.numero_contrato.trim() : null,
    valor_liberado: valores.valor_liberado,
    finalidade: valores.finalidade?.trim() ? valores.finalidade.trim() : null,
    taxa_juros: percentualParaFracao(valores.taxa_juros),
    sistema_amortizacao: valores.sistema_amortizacao,
    num_parcelas: valores.num_parcelas as number,
    cet: valores.cet?.trim() ? percentualParaFracao(valores.cet) : null,
    data_inicio: valores.data_inicio,
    permite_quitacao_antecipada: valores.permite_quitacao_antecipada,
    conta_id: Number(valores.conta_id),
    categoria_id: valores.categoria_id === "" ? null : Number(valores.categoria_id),
    parcelas_ja_pagas: valores.parcelas_ja_pagas ?? 0,
  };
}
