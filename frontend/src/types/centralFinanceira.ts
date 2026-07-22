/**
 * Espelha 1:1 os schemas de saída de `app/schemas/central_financeira.py` e
 * das entidades que ela reaproveita (`ContaRead`, `CartaoRead`, `FaturaRead`,
 * `FinanciamentoRead`, `EmprestimoRead`, `MetaRead`) — conferido por leitura
 * direta do backend, não da especificação de produto original. Ver
 * docs/analise-arquitetural-dashboard.md, seção 3 e 6.1.
 *
 * Só os campos de leitura (`Read`) — sem `Create`/`Update` aqui, esta etapa
 * é 100% somente-leitura. Quando o CRUD de cada entidade chegar (F6+), os
 * tipos completos nascem em `types/<entidade>.ts` e estes podem ser
 * re-exportados de lá (sinalizado em analise-arquitetural-dashboard.md,
 * seção 6.1) — `ContaRead` já foi migrado nesse sentido na Etapa F6 (CRUD
 * de Conta): a definição completa mora em `types/conta.ts`, aqui é só
 * reexportada para não quebrar nenhum import existente.
 *
 * Todo valor monetário/decimal é `string` (nunca `number`) — mesmo princípio
 * de `analise-arquitetural-frontend.md`, seção 0.
 */
import type {
  Bandeira,
  CategoriaEventoCalendario,
  SistemaAmortizacao,
  StatusContratoCredito,
  StatusFatura,
  TipoEntidadeReferenciavel,
} from "./enums";
import type { ContaRead } from "./conta";
import type { MetaRead } from "./meta";

export type { ContaRead, MetaRead };

// ---- Entidades reaproveitadas (recorte "Read" mínimo usado pela Central) ----

export interface CartaoRead {
  id: number;
  nome: string;
  conta_pagamento_id: number;
  instituicao: string;
  bandeira: Bandeira;
  ultimos_quatro_digitos: string;
  limite: string;
  limite_disponivel: string;
  dia_fechamento: number;
  dia_vencimento: number;
  ativo: boolean;
}

export interface FaturaRead {
  id: number;
  cartao_id: number;
  mes_referencia: string;
  data_fechamento: string;
  data_vencimento: string;
  valor_pago: string;
  valor_total: string;
  status: StatusFatura;
}

interface ContratoCreditoBase {
  id: number;
  descricao: string;
  instituicao_financeira: string;
  numero_contrato: string | null;
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
  parcelas_pagas: number;
  parcelas_restantes: number;
  valor_total_pago: string;
  proxima_parcela_data: string | null;
  proxima_parcela_valor: string | null;
}

export interface FinanciamentoResumo extends ContratoCreditoBase {
  valor_financiado: string;
  valor_entrada: string | null;
  bem_financiado: string | null;
}

export interface EmprestimoResumo extends ContratoCreditoBase {
  valor_liberado: string;
  finalidade: string | null;
}

// ---- Schemas de saída da Central Financeira (11 endpoints) ----
// `MetaRead` é reexportado de `./meta` (mesma migração já feita para
// `ContaRead` na Etapa F6): o backend de `/central-financeira/metas`
// (`ProgressoMetasRead`) reusa literalmente `app.schemas.meta.MetaRead`,
// então o tipo completo (incluindo os campos do Refinamento de Metas —
// `frequencia_contribuicao`, `situacao_planejamento`, etc.) já chega pronto
// aqui sem precisar de nenhuma alteração no backend.

export interface ContaSaldoResumo {
  id: number;
  nome: string;
  saldo_atual: string;
}

export interface SaldoConsolidadoRead {
  saldo_total: string;
  contas: ContaSaldoResumo[];
}

export interface ResumoContasRead {
  contas: ContaRead[];
}

export interface ResumoCartoesRead {
  cartoes: CartaoRead[];
  total_utilizado: string;
}

/** `/central-financeira/cartoes/agregado` — panorama do "Dashboard de
 * Cartões" (Sprint de Refinamento Premium, item 3): deliberadamente sem
 * nenhum gráfico por cartão individual (isso é `/cartoes/:id`). Todo campo
 * já vem somado/calculado pelo backend a partir de `CartaoRead`/`FaturaRead`
 * — este tipo só espelha a resposta, nenhum cálculo aqui. */
export interface UsoCartao {
  cartao_id: number;
  nome: string;
  percentual_usado: string;
}

export interface ProximoVencimentoFatura {
  cartao_id: number;
  cartao_nome: string;
  fatura_id: number;
  data_vencimento: string;
  valor_total: string;
}

export interface ResumoCartoesAgregadoRead {
  limite_total: string;
  limite_disponivel_total: string;
  limite_usado_total: string;
  percentual_usado_geral: string;
  quantidade_cartoes: number;
  faturas_em_aberto: number;
  proximos_vencimentos: ProximoVencimentoFatura[];
  distribuicao_uso: UsoCartao[];
}

export interface ResumoFaturasRead {
  faturas: FaturaRead[];
}

export interface ResumoFinanciamentosRead {
  financiamentos: FinanciamentoResumo[];
}

export interface ResumoEmprestimosRead {
  emprestimos: EmprestimoResumo[];
}

export interface ProgressoMetasRead {
  metas: MetaRead[];
}

export interface EventoAgenda {
  data: string;
  descricao: string;
  valor: string;
  origem_tipo: TipoEntidadeReferenciavel;
  origem_id: number;
}

export interface AgendaFinanceiraRead {
  eventos: EventoAgenda[];
}

export interface ResumoFinanceiroRead {
  ano: number;
  mes: number;
  saldo_total: string;
  entradas_mes: string;
  saidas_mes: string;
  fluxo_caixa_mes: string;
  patrimonio_liquido: string;
}

export interface VisaoMensalRead {
  ano: number;
  mes: number;
  entradas: string;
  saidas: string;
  fluxo_caixa: string;
}

export interface IndicadoresGeraisRead {
  contas_ativas: number;
  cartoes_ativos: number;
  faturas_em_aberto: number;
  financiamentos_ativos: number;
  emprestimos_ativos: number;
  metas_ativas: number;
  percentual_medio_metas: string;
  parcelas_atrasadas: number;
}

/** `GET /central-financeira/calendario` — endpoint IRMÃO de `agenda` acima
 * (não substitui): escopo é o MÊS inteiro (`ano`/`mes`), qualquer status, e
 * inclui Transferência/Meta/fechamento de fatura, que `agenda` nunca
 * incluiu. Ver docs/analise-arquitetural-transferencias-frontend.md. */
export interface EventoCalendario {
  data: string;
  descricao: string;
  valor: string;
  categoria: CategoriaEventoCalendario;
  origem_tipo: TipoEntidadeReferenciavel;
  origem_id: number;
  status: string | null;
  /** Expansão de Contas Recorrentes (2026-07-20): `true` só para
   * ocorrências FUTURAS projetadas de um template ativo (horizonte de 90
   * dias, nunca persistidas) — a UI as renderiza como previsão (estilo
   * tracejado/atenuado), nunca como história. */
  previsto: boolean;
}

export interface CalendarioFinanceiroRead {
  ano: number;
  mes: number;
  eventos: EventoCalendario[];
}

/** `GET /central-financeira/atividades` — Central de Atividades (Sprint de
 * Refinamento Premium, item 17): feed cronológico de "o que aconteceu
 * recentemente", combinando Transação/Transferência/Meta concluída.
 * `data_hora` é sempre um datetime ISO (mesmo para Meta, cujo backend
 * normaliza `concluida_em` para meia-noite) — único jeito de ordenar as 3
 * fontes de forma consistente. `origem_tipo`/`origem_id` reaproveitam o
 * mesmo discriminador de `EventoCalendario`/`EventoAgenda`
 * (`TipoEntidadeReferenciavel`), então o mesmo mapa `ICONE_POR_ORIGEM`/
 * `ROTA_POR_ORIGEM` de `lib/origemNavegacao.ts` serve aqui também. */
export interface AtividadeRecente {
  data_hora: string;
  descricao: string;
  valor: string | null;
  origem_tipo: TipoEntidadeReferenciavel;
  origem_id: number;
}

export interface CentralAtividadesRead {
  atividades: AtividadeRecente[];
}

/** Etapa de Gráficos (docs/analise-arquitetural-graficos.md) — os 2 novos
 * endpoints agregam exatamente os 4 gráficos da primeira etapa + o 5º
 * (distribuição do saldo atual, que reaproveita `SaldoConsolidadoRead`
 * acima, sem tipo próprio). */
export interface PontoTendenciaMensal {
  ano: number;
  mes: number;
  saldo_total: string;
  entradas: string;
  saidas: string;
}

export interface GraficosTendenciasRead {
  meses: PontoTendenciaMensal[];
}

export interface GastoPorCategoria {
  categoria_id: number | null;
  categoria_nome: string;
  categoria_cor: string | null;
  categoria_icone: string | null;
  total: string;
}

export interface GastoPorCartao {
  cartao_id: number;
  cartao_nome: string;
  total: string;
}

export interface GraficosPeriodoRead {
  ano: number;
  mes: number;
  gastos_por_categoria: GastoPorCategoria[];
  gastos_por_cartao: GastoPorCartao[];
}
