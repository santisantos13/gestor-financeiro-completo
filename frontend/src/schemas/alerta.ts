/**
 * Validação de FORMATO/obrigatoriedade só para UX — a regra de negócio
 * real (formato de `condicao` por `tipo`, posse da entidade referenciada)
 * continua exclusiva do backend (`AlertaService._normalizar_condicao`) e
 * chega como 422/404 tratado por `utils/errors.ts`.
 *
 * Um único schema de formulário cobre os 5 `tipo` (em vez de 5 schemas
 * separados) porque `AlertaFormDialog` é um único modal que troca de
 * "modo" via `tipo` selecionado — `superRefine` valida só o campo que o
 * `tipo` atual exige, os demais ficam presentes no shape mas ignorados.
 * `entidade_id` chega do `Select` como `string` (mesmo padrão de todo
 * `SelectField` do projeto); `limite_percentual`/`valor_minimo` chegam
 * como string decimal de `PercentageField`/`CurrencyField`
 * (`utils/mask.ts`); `dias_antes` chega como `number | undefined` de
 * `NumberField` (`decimalPlaces=0`).
 */
import { z } from "zod";
import type { AlertaCondicao, AlertaCreate, AlertaUpdate, TipoAlerta } from "../types/alerta";

export const alertaFormSchema = z
  .object({
    tipo: z.enum(["LIMITE_CARTAO", "VENCIMENTO_FATURA", "VENCIMENTO_CONTA_RECORRENTE", "META_ATINGIDA", "SALDO_BAIXO"]),
    entidade_id: z.string().min(1, "Selecione o item que este alerta vai monitorar."),
    limite_percentual: z.string(),
    dias_antes: z.number().optional(),
    valor_minimo: z.string(),
  })
  .superRefine((valores, ctx) => {
    if (valores.tipo === "LIMITE_CARTAO" && valores.limite_percentual.trim() === "") {
      ctx.addIssue({
        path: ["limite_percentual"],
        code: z.ZodIssueCode.custom,
        message: "Informe o percentual do limite.",
      });
    }
    if (valores.tipo === "SALDO_BAIXO" && valores.valor_minimo.trim() === "") {
      ctx.addIssue({
        path: ["valor_minimo"],
        code: z.ZodIssueCode.custom,
        message: "Informe o valor mínimo.",
      });
    }
  });

export type AlertaFormValues = z.infer<typeof alertaFormSchema>;

export const VALORES_VAZIOS_ALERTA: AlertaFormValues = {
  tipo: "LIMITE_CARTAO",
  entidade_id: "",
  limite_percentual: "",
  dias_antes: undefined,
  valor_minimo: "",
};

/** Monta `condicao` a partir dos valores do formulário, no formato exato
 * que cada `tipo` espera (espelha `AlertaService._normalizar_condicao`,
 * sem duplicar a VALIDAÇÃO — só o shape do payload). */
function construirCondicao(valores: AlertaFormValues): AlertaCondicao | undefined {
  switch (valores.tipo) {
    case "LIMITE_CARTAO":
      return { limite_percentual: Number(valores.limite_percentual) };
    case "VENCIMENTO_FATURA":
    case "VENCIMENTO_CONTA_RECORRENTE":
      // `dias_antes` omitido = backend aplica o default (3 dias) - não
      // força um valor aqui à toa.
      return valores.dias_antes != null ? { dias_antes: valores.dias_antes } : undefined;
    case "META_ATINGIDA":
      return undefined;
    case "SALDO_BAIXO":
      return { valor_minimo: Number(valores.valor_minimo) };
    default:
      return undefined;
  }
}

export function alertaFormValuesParaCriar(valores: AlertaFormValues): AlertaCreate {
  return {
    tipo: valores.tipo,
    entidade_id: Number(valores.entidade_id),
    condicao: construirCondicao(valores),
  };
}

/** `tipo`/`entidade_id` são imutáveis após a criação (ver
 * `types/alerta.ts`) - editar um alerta existente só manda `condicao`. */
export function alertaFormValuesParaAtualizar(valores: AlertaFormValues): AlertaUpdate {
  return { condicao: construirCondicao(valores) };
}

function condicaoNumero(condicao: AlertaCondicao, campo: string): string {
  if (condicao && campo in condicao) {
    return String((condicao as unknown as Record<string, number>)[campo]);
  }
  return "";
}

/** Caminho inverso — usado ao abrir o formulário para editar um alerta
 * existente. */
export function alertaParaFormValues(tipo: TipoAlerta, entidadeId: number, condicao: AlertaCondicao): AlertaFormValues {
  return {
    tipo,
    entidade_id: String(entidadeId),
    limite_percentual: condicaoNumero(condicao, "limite_percentual"),
    dias_antes: condicao && "dias_antes" in condicao ? condicao.dias_antes : undefined,
    valor_minimo: condicaoNumero(condicao, "valor_minimo"),
  };
}
