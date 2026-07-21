/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra real
 * (dia_vencimento × família de frequência, conta XOR cartão, datas) vive
 * no backend (`ContaRecorrenteService`). O formulário condiciona a
 * EXIBIÇÃO do campo dia_vencimento à família da frequência, e este schema
 * só garante que ele foi preenchido quando visível.
 */
import { z } from "zod";
import type {
  ContaRecorrenteCreate,
  ContaRecorrenteUpdate,
  FrequenciaRecorrencia,
} from "../types/contaRecorrente";

/** Espelha `FREQUENCIAS_BASEADAS_EM_DIAS` do backend (`app/core/datas.py`)
 * — nas três, `dia_vencimento` não se aplica (âncora = data_inicio). */
export const FREQUENCIAS_SEM_DIA_VENCIMENTO: readonly FrequenciaRecorrencia[] = [
  "DIARIA",
  "SEMANAL",
  "QUINZENAL",
];

export const OPCOES_FREQUENCIA: { value: FrequenciaRecorrencia; label: string }[] = [
  { value: "DIARIA", label: "Diária" },
  { value: "SEMANAL", label: "Semanal" },
  { value: "QUINZENAL", label: "Quinzenal (a cada 14 dias)" },
  { value: "MENSAL", label: "Mensal" },
  { value: "BIMESTRAL", label: "Bimestral" },
  { value: "TRIMESTRAL", label: "Trimestral" },
  { value: "SEMESTRAL", label: "Semestral" },
  { value: "ANUAL", label: "Anual" },
];

export const LABEL_FREQUENCIA: Record<FrequenciaRecorrencia, string> = {
  DIARIA: "Diária",
  SEMANAL: "Semanal",
  QUINZENAL: "Quinzenal",
  MENSAL: "Mensal",
  BIMESTRAL: "Bimestral",
  TRIMESTRAL: "Trimestral",
  SEMESTRAL: "Semestral",
  ANUAL: "Anual",
};

export const recorrenteFormSchema = z
  .object({
    descricao: z.string().min(1, "Informe a descrição.").max(200, "Use no máximo 200 caracteres."),
    valor: z.string().min(1, "Informe o valor."),
    tipo: z.enum(["RECEITA", "DESPESA"], { message: "Selecione o tipo." }),
    frequencia: z.enum(
      ["DIARIA", "SEMANAL", "QUINZENAL", "MENSAL", "BIMESTRAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL"],
      { message: "Selecione a frequência." },
    ),
    dia_vencimento: z.string(),
    origem: z.enum(["CONTA", "CARTAO"], { message: "Selecione a origem." }),
    conta_id: z.string(),
    cartao_id: z.string(),
    categoria_id: z.string(),
    data_inicio: z.string().min(1, "Informe a data de início."),
    data_fim: z.string(),
  })
  .refine(
    (v) =>
      FREQUENCIAS_SEM_DIA_VENCIMENTO.includes(v.frequencia) || v.dia_vencimento.trim() !== "",
    { message: "Informe o dia do vencimento.", path: ["dia_vencimento"] },
  )
  .refine((v) => v.origem !== "CONTA" || v.conta_id !== "", {
    message: "Selecione a conta.",
    path: ["conta_id"],
  })
  .refine((v) => v.origem !== "CARTAO" || v.cartao_id !== "", {
    message: "Selecione o cartão.",
    path: ["cartao_id"],
  });

export type RecorrenteFormValues = z.infer<typeof recorrenteFormSchema>;

export const RECORRENTE_VALORES_VAZIOS: RecorrenteFormValues = {
  descricao: "",
  valor: "",
  tipo: "DESPESA",
  frequencia: "MENSAL",
  dia_vencimento: "",
  origem: "CONTA",
  conta_id: "",
  cartao_id: "",
  categoria_id: "",
  data_inicio: "",
  data_fim: "",
};

export function recorrenteFormValuesParaPayload(valores: RecorrenteFormValues): ContaRecorrenteCreate {
  const semDia = FREQUENCIAS_SEM_DIA_VENCIMENTO.includes(valores.frequencia);
  return {
    descricao: valores.descricao.trim(),
    valor: valores.valor,
    tipo: valores.tipo,
    frequencia: valores.frequencia,
    dia_vencimento: semDia ? null : Number(valores.dia_vencimento),
    conta_id: valores.origem === "CONTA" ? Number(valores.conta_id) : null,
    cartao_id: valores.origem === "CARTAO" ? Number(valores.cartao_id) : null,
    categoria_id: valores.categoria_id ? Number(valores.categoria_id) : null,
    data_inicio: valores.data_inicio,
    data_fim: valores.data_fim || null,
  };
}

/** PATCH sempre envia o conjunto completo de campos editáveis — mais
 * simples e correto que diff campo a campo (mesmo padrão do restante do
 * projeto; o backend aplica semântica de PATCH sobre o que chega). */
export function recorrenteFormValuesParaUpdate(valores: RecorrenteFormValues): ContaRecorrenteUpdate {
  return recorrenteFormValuesParaPayload(valores);
}
