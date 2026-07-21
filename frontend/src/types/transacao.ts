/**
 * Espelha 1:1 `app/schemas/transacao.py` — conferido por leitura direta do
 * backend (`TransacaoCreate`/`TransacaoUpdate`/`TransacaoRead`). Ver
 * docs/analise-arquitetural-transacao-frontend.md, seção 1 e 9.
 *
 * `conta_id`/`cartao_id`: exatamente um dos dois em toda transação (XOR
 * garantido pelo backend), e nenhum dos dois aparece em `TransacaoUpdate` —
 * a origem é imutável após a criação (mesmo princípio de `Fatura.cartao_id`).
 *
 * `parcelamento_id`/`financiamento_id`/`emprestimo_id`/`numero_parcela`/
 * `origem_recorrente_id`/`meta_id` existem aqui só para espelhar o backend
 * fielmente — nenhum formulário os envia (nenhuma dessas entidades tem CRUD
 * próprio que gere uma Transação solta editável por aqui). `meta_id` foi a
 * exceção entre a Etapa F12 e o Refatoramento de Metas/Transferências
 * (`docs/analise-arquitetural-metas-transferencias.md`, seção 6): não existe
 * mais em `TransacaoCreate`/`TransacaoUpdate` — nenhuma Transação nova pode
 * ser marcada com uma Meta (aportes/resgates viram Transferência real para
 * o "cofrinho" da Meta). Continua em `TransacaoRead` e em `TransacaoFiltros`
 * só para sustentar a LEITURA do histórico legado (Transações antigas já
 * marcadas antes do refatoramento, nunca reescritas).
 *
 * `fatura_id`/`fatura_paga_id` só existem em `TransacaoRead`: são sempre
 * derivados pelo backend, nunca aceitos em payload de entrada.
 */
import type { StatusTransacao, TipoTransacao } from "./enums";
import type { TagRead } from "./tag";

export type { StatusTransacao, TipoTransacao };

export interface TransacaoRead {
  id: number;
  tipo: TipoTransacao;
  valor: string;
  data: string;
  descricao: string;
  status: StatusTransacao;

  categoria_id: number | null;
  conta_id: number | null;
  cartao_id: number | null;

  parcelamento_id: number | null;
  financiamento_id: number | null;
  emprestimo_id: number | null;
  numero_parcela: number | null;

  origem_recorrente_id: number | null;
  meta_id: number | null;

  fatura_id: number | null;
  fatura_paga_id: number | null;

  /** True só para parcelas de Financiamento/Empréstimo importadas no
   * onboarding ("parcelas_ja_pagas") — dinheiro que já tinha saído da vida
   * financeira do usuário antes dele usar o app, por isso nunca conta no
   * saldo_atual da Conta (ver `ContaRepository.somar_transacoes_pagas`,
   * backend). Mesmo espírito de `Fatura.importada`. */
  importada: boolean;

  tags: TagRead[];
}

export interface TransacaoCreate {
  tipo: TipoTransacao;
  valor: string;
  data: string;
  descricao: string;
  /** Só relevante para transação de Conta — omitido vira `PENDENTE` no
   * backend. Ignorado (sempre forçado para `PAGO`) numa transação de
   * Cartão. */
  status?: StatusTransacao | null;

  categoria_id?: number | null;
  conta_id?: number | null;
  cartao_id?: number | null;

  parcelamento_id?: number | null;
  financiamento_id?: number | null;
  emprestimo_id?: number | null;
  numero_parcela?: number | null;

  origem_recorrente_id?: number | null;

  tag_ids: number[];
}

/** Semântica de PATCH — todo campo omitido permanece intocado. Nunca
 * inclui `conta_id`/`cartao_id` (imutáveis após a criação — seção 3 do
 * documento). */
export interface TransacaoUpdate {
  tipo?: TipoTransacao;
  valor?: string;
  data?: string;
  descricao?: string;
  status?: StatusTransacao;

  categoria_id?: number | null;
  parcelamento_id?: number | null;
  financiamento_id?: number | null;
  emprestimo_id?: number | null;
  numero_parcela?: number | null;

  origem_recorrente_id?: number | null;

  tag_ids?: number[];
}

/** Parâmetros de `GET /transacoes` — todos opcionais, repassados 1:1 como
 * query string por `transacaoService.listar` (nenhum filtro é só
 * client-side aqui, diferente de toda entidade anterior — seção 2 do
 * documento). */
export interface TransacaoFiltros {
  conta_id?: number;
  cartao_id?: number;
  /** Histórico de compras de UMA fatura (`FaturaDrawer`, pedido do usuário
   * 2026-07-20: "seria interessante se cada fatura tivesse o histórico de
   * compras dela"). Compras lançadas naquele ciclo — nunca inclui o
   * pagamento da fatura em si (`fatura_paga_id`, uma Transacao separada). */
  fatura_id?: number;
  categoria_id?: number;
  /** Etapa de Onboarding: usado só pelo Drawer de cronograma de
   * Financiamento/Empréstimo (`FinanciamentosPage`/`EmprestimosPage`) para
   * listar as parcelas (`Transacao`) de um contrato específico — nenhum
   * outro formulário desta etapa envia esses dois filtros. */
  financiamento_id?: number;
  emprestimo_id?: number;
  /** Etapa F12 (Meta): usado pelo histórico de aportes expandido dentro de
   * `MetaResumoCard` — lista as `Transacao` marcadas com `meta_id` apontando
   * para uma meta específica, mesmo raciocínio de `financiamento_id`/
   * `emprestimo_id` acima. */
  meta_id?: number;
  tipo?: TipoTransacao;
  status?: StatusTransacao;
  data_inicio?: string;
  data_fim?: string;
  /** Pedido explícito do usuário (2026-07-20): a tela de Transações não
   * deve listar compras de cartão, só o que sai de uma Conta (lançamento
   * direto ou pagamento de fatura). `TransacoesPage` sempre envia `true`;
   * nenhum outro consumidor (Financiamento/Empréstimo/Meta acima, Central
   * Financeira) usa este filtro. */
  apenas_conta?: boolean;
  skip?: number;
  limit?: number;
}
