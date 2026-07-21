/**
 * Espelha 1:1 `app/schemas/fatura.py` — conferido por leitura direta do
 * backend. Diferente de Conta/Categoria/Tag/Cartão, não existe
 * `FaturaUpdate`: os campos de Fatura são imutáveis por design (datas
 * derivadas na criação, nunca editadas depois) — as únicas mudanças de
 * estado são as ações de negócio (`fechar`/`registrar pagamento`), cada
 * uma com seu próprio payload/endpoint. Ver
 * docs/analise-arquitetural-fatura-frontend.md, seção 0.
 */
import type { StatusFatura } from "./enums";

export type { StatusFatura };

export interface FaturaRead {
  id: number;
  cartao_id: number;
  mes_referencia: string;
  data_fechamento: string;
  data_vencimento: string;
  valor_pago: string;
  valor_total: string;
  status: StatusFatura;
  /** Etapa de Onboarding: true só para faturas criadas via `POST
   * /faturas/importar` — um ciclo histórico (já fechado/pago antes do
   * usuário começar a usar o app) com `valor_total` informado
   * diretamente, nunca derivado de Transacao real. Usado só para exibir
   * um selo "Importada" — nenhum cálculo depende disso no frontend. */
  importada: boolean;
  /** Valor que o usuário declarou diretamente como "já gasto neste
   * ciclo" — SEM nenhuma Transacao por trás (pedido explícito do
   * usuário: "poder informar o saldo já utilizado do cartão
   * independentemente de transações"). Só editável enquanto `status ===
   * "ABERTA"` (ver `faturaService.ajustarSaldoInicial`); depois de
   * fechada, já está embutido em `valor_total` para sempre. */
  ajuste_manual: string;
}

/** Payload de `PATCH /faturas/{id}/ajuste-manual` — ver docstring de
 * `FaturaAjusteManualUpdate` no backend. Editar sempre DEFINE o total
 * (nunca soma/subtrai em cima do que já estava salvo). */
export interface FaturaAjusteManualUpdate {
  ajuste_manual: string;
}

/** Payload de `PATCH /faturas/{id}/ajuste-pos-fechamento` — pedido
 * explícito do usuário (2026-07-20): "quero adicionar uma transação em
 * uma fatura que já foi fechada e paga, porém tinha esquecido dela
 * antes". Diferente de `FaturaAjusteManualUpdate` (define o total, só
 * ABERTA), este SOMA `valor` ao total de uma fatura já FECHADA (ou paga/
 * atrasada/parcial) — sem criar nenhuma Transacao. Ver
 * `FaturaAjustePosFechamentoCreate` no backend. */
export interface FaturaAjustePosFechamentoCreate {
  valor: string;
}

export interface FaturaCreate {
  cartao_id: number;
  /** Primeiro dia do mês de referência (`AAAA-MM-01`) — único formato
   * aceito pelo backend (`FaturaCreate._validar_primeiro_dia_do_mes`). */
  mes_referencia: string;
}

/** Payload de `POST /faturas/importar` — ver docstring de
 * `FaturaImportarCreate` no backend. Diferente de `FaturaCreate`, a
 * fatura resultante já nasce FECHADA com `valor_total` informado aqui
 * (nunca recalculado a partir de Transacao). */
export interface FaturaImportarCreate {
  cartao_id: number;
  mes_referencia: string;
  valor_total: string;
}

export interface FaturaPagamentoCreate {
  valor: string;
  data: string;
  descricao?: string | null;
}

/** Payload de `POST /faturas/pagar-em-lote` — pedido explícito do usuário:
 * "seria interessante poder pagar todas selecionadas". Diferente de
 * `FaturaPagamentoCreate`, não tem `valor`: cada fatura é paga pelo seu
 * próprio restante (`valor_total - valor_pago`), nunca um valor único
 * para todas — ver `FaturaService.pagar_em_lote` no backend. */
export interface FaturaPagamentoEmLoteCreate {
  fatura_ids: number[];
  data: string;
}

/** Resposta de `POST /faturas/pagar-em-lote` — `pagas` pode ser menor que
 * `fatura_ids.length`: faturas ABERTAS ou já quitadas são puladas
 * silenciosamente pelo backend, nunca derrubam o lote inteiro. */
export interface FaturaPagamentoEmLoteResult {
  pagas: number;
}
