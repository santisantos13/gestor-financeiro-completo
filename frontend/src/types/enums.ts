/**
 * Espelha app/models/enums.py 1:1 - valores exatos, nenhum reinterpretado.
 * Union types literais (não `enum` do TypeScript) porque os valores já são
 * string no backend ((str, enum.Enum)) - um `enum` do TS adicionaria uma
 * camada de indireção sem necessidade.
 *
 * Atualizado apenas quando o backend adicionar/remover um enum ou um valor
 * - nunca "melhorado" ou reordenado por gosto do frontend.
 */

export type Bandeira =
  | "VISA"
  | "MASTERCARD"
  | "ELO"
  | "AMERICAN_EXPRESS"
  | "HIPERCARD"
  | "DINERS_CLUB"
  | "OUTRA";

export type TipoConta = "CORRENTE" | "POUPANCA" | "CARTEIRA" | "INVESTIMENTO";

export type TipoCategoria = "RECEITA" | "DESPESA" | "AMBOS";

export type TipoTransacao = "RECEITA" | "DESPESA";

/** Em transação de Conta, `status` é autoritativo (PENDENTE = não
 * aconteceu, PAGO = já moveu dinheiro), editável livremente. Em transação
 * de Cartão, `status` é sempre forçado a PAGO na criação - a autoridade
 * real sobre pagamento é a Fatura, não este campo. */
export type StatusTransacao = "PENDENTE" | "PAGO";

/** Duas famílias (expansão de Contas Recorrentes, 2026-07-20): baseadas
 * em DIAS (DIARIA/SEMANAL/QUINZENAL - `dia_vencimento` não se aplica, a
 * âncora é a própria `data_inicio`; QUINZENAL = 14 dias fixos) e baseadas
 * em MESES (MENSAL/BIMESTRAL/TRIMESTRAL/SEMESTRAL/ANUAL - `dia_vencimento`
 * obrigatório, com clamp de fim de mês no backend). */
export type FrequenciaRecorrencia =
  | "DIARIA"
  | "SEMANAL"
  | "QUINZENAL"
  | "MENSAL"
  | "BIMESTRAL"
  | "TRIMESTRAL"
  | "SEMESTRAL"
  | "ANUAL";

/** Ciclo de vida de uma ContaRecorrente. ENCERRADA é terminal (inclusive
 * o DELETE encerra, nunca apaga - histórico preservado). */
export type StatusRecorrencia = "ATIVA" | "PAUSADA" | "ENCERRADA";

/** Só ABERTA/FECHADA são persistidos no banco - PARCIALMENTE_PAGA, PAGA e
 * ATRASADA são DERIVADOS em runtime pelo FaturaService (vocabulário de API
 * apenas). O frontend trata os 5 como estados possíveis vindos da API sem
 * precisar saber quais são coluna real. */
export type StatusFatura =
  | "ABERTA"
  | "FECHADA"
  | "PARCIALMENTE_PAGA"
  | "PAGA"
  | "ATRASADA";

/** PRICE = parcelas fixas (Tabela Price). SAC = parcelas decrescentes. */
export type SistemaAmortizacao = "PRICE" | "SAC";

export type StatusContratoCredito = "ATIVO" | "QUITADO" | "INADIMPLENTE";

/** Único valor hoje - arquitetura já prevê múltiplos papéis no futuro. */
export type TipoPapel = "USER";

export type TipoAlerta =
  | "LIMITE_CARTAO"
  | "VENCIMENTO_FATURA"
  | "VENCIMENTO_CONTA_RECORRENTE"
  | "META_ATINGIDA"
  | "SALDO_BAIXO";

/** Usado polimorficamente por Alerta e Anexo (par entidade_tipo +
 * entidade_id) e pela Agenda Financeira da Central (origem_tipo). */
export type TipoEntidadeReferenciavel =
  | "CONTA"
  | "CARTAO"
  | "FATURA"
  | "TRANSACAO"
  | "PARCELAMENTO"
  | "FINANCIAMENTO"
  | "EMPRESTIMO"
  | "CONTA_RECORRENTE"
  | "META"
  | "TRANSFERENCIA";

/** Discriminador de EXIBIÇÃO do Calendário Financeiro (cor do dot) —
 * propositalmente separado de `TipoEntidadeReferenciavel` (que decide para
 * ONDE navegar). Espelha `CategoriaEventoCalendario` (backend,
 * `models/enums.py`). Ver docs/analise-arquitetural-transferencias-frontend.md. */
export type CategoriaEventoCalendario =
  | "RECEITA"
  | "DESPESA"
  | "FATURA_FECHAMENTO"
  | "FATURA_VENCIMENTO"
  | "TRANSFERENCIA"
  | "META";

/** Discriminador de exibição/filtro do extrato de uma Conta (`GET
 * /contas/{id}/extrato`) — espelha `CategoriaMovimentacaoConta` (backend,
 * `models/enums.py`). Ver docs/analise-arquitetural-extrato-conta.md. */
export type CategoriaMovimentacaoConta =
  | "RECEITA"
  | "DESPESA"
  | "TRANSFERENCIA_ENVIADA"
  | "TRANSFERENCIA_RECEBIDA"
  | "PAGAMENTO_FATURA"
  | "PAGAMENTO_FINANCIAMENTO"
  | "PAGAMENTO_EMPRESTIMO";
