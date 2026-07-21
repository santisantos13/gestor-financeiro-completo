/**
 * Espelha 1:1 `app/schemas/emprestimo.py` — mesmo raciocínio de
 * `types/financiamento.ts` (sem Update, única transição é `pagar_parcela`).
 * Diferença de Financiamento: `valor_liberado` é obrigatório (não há
 * "entrada" — o valor inteiro é sempre desembolsado na conta do usuário),
 * `finalidade` substitui `bem_financiado` (campo livre, só descritivo).
 */
import type { SistemaAmortizacao, StatusContratoCredito } from "./enums";

export type { SistemaAmortizacao, StatusContratoCredito };

export interface EmprestimoRead {
  id: number;
  descricao: string;
  instituicao_financeira: string;
  numero_contrato: string | null;

  valor_liberado: string;
  finalidade: string | null;

  taxa_juros: string;
  sistema_amortizacao: SistemaAmortizacao;
  num_parcelas: number;
  cet: string | null;
  data_inicio: string;

  saldo_devedor: string;
  permite_quitacao_antecipada: boolean;
  status: StatusContratoCredito;

  conta_id: number | null;
  categoria_id: number | null;
}

export interface EmprestimoCreate {
  descricao: string;
  instituicao_financeira: string;
  numero_contrato?: string | null;

  valor_liberado: string;
  finalidade?: string | null;

  taxa_juros: string;
  sistema_amortizacao: SistemaAmortizacao;
  num_parcelas: number;
  cet?: string | null;
  data_inicio: string;

  permite_quitacao_antecipada: boolean;

  conta_id: number;
  categoria_id?: number | null;

  /** Etapa de Onboarding: mesmo raciocínio de `FinanciamentoCreate`. */
  parcelas_ja_pagas?: number;
}
