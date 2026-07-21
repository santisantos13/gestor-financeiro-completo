/**
 * Espelha 1:1 `app/schemas/financiamento.py` — conferido por leitura direta
 * do backend. Sem `FinanciamentoUpdate`: todo campo é estrutural (determina
 * o cronograma de amortização inteiro, gerado de uma vez na criação) —
 * editar qualquer um depois desincronizaria as parcelas já geradas e o
 * `saldo_devedor`. A única transição de estado é a ação dedicada
 * `pagar_parcela` (`POST /financiamentos/{id}/parcelas/{numero}/pagar`).
 *
 * `parcelas_ja_pagas` (Etapa de Onboarding) só existe em `FinanciamentoCreate`
 * — nunca aparece em `FinanciamentoRead` (o backend já "consome" esse valor
 * na criação, aplicando-o via `pagar_parcela` internamente; depois disso, o
 * progresso real já está refletido em `saldo_devedor`/nas próprias
 * `Transacao` de parcela, sem precisar de um campo próprio no retorno).
 */
import type { SistemaAmortizacao, StatusContratoCredito } from "./enums";

export type { SistemaAmortizacao, StatusContratoCredito };

export interface FinanciamentoRead {
  id: number;
  descricao: string;
  instituicao_financeira: string;
  numero_contrato: string | null;

  valor_financiado: string;
  valor_entrada: string | null;
  bem_financiado: string | null;

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

export interface FinanciamentoCreate {
  descricao: string;
  instituicao_financeira: string;
  numero_contrato?: string | null;

  valor_financiado: string;
  valor_entrada?: string | null;
  bem_financiado?: string | null;

  taxa_juros: string;
  sistema_amortizacao: SistemaAmortizacao;
  num_parcelas: number;
  cet?: string | null;
  data_inicio: string;

  permite_quitacao_antecipada: boolean;

  conta_id: number;
  categoria_id?: number | null;

  /** Etapa de Onboarding: quantas parcelas já foram pagas ANTES de
   * contratar este financiamento no app. `0` (padrão) = comportamento de
   * sempre. */
  parcelas_ja_pagas?: number;
}
