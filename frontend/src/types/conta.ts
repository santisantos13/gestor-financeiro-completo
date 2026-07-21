/**
 * Espelha 1:1 `app/schemas/conta.py` — conferido por leitura direta do
 * backend (`ContaCreate`/`ContaUpdate`/`ContaRead`), não de nenhuma
 * documentação (não existe `docs/analise-arquitetural-conta.md` nem
 * `docs/revisao-tecnica-conta.md` — Conta foi a primeira entidade
 * implementada no backend, antes da convenção de doc-por-entidade
 * começar). Todo valor monetário é `string` (nunca `number`), mesmo
 * princípio de `docs/analise-arquitetural-frontend.md`, seção 0.
 *
 * `saldo_atual` existe só em `ContaRead` — não é uma coluna, é calculado
 * pelo `ContaService` a cada leitura (soma de `Transacao`/`Transferencia`
 * ligadas à conta). O frontend nunca recalcula isso, só exibe.
 */
import type { CategoriaMovimentacaoConta, TipoConta, TipoEntidadeReferenciavel } from "./enums";

export type { TipoConta };

export interface ContaRead {
  id: number;
  nome: string;
  tipo: TipoConta;
  saldo_inicial: string;
  saldo_atual: string;
  instituicao: string | null;
  ativo: boolean;
}

export interface ContaCreate {
  nome: string;
  tipo: TipoConta;
  saldo_inicial: string;
  instituicao: string | null;
}

/** Semântica de PATCH no backend — todo campo omitido aqui permanece
 * intocado (nunca sobrescrito com `undefined`/`null` por omissão). Inclui
 * `ativo`: reativar uma conta desativada é um PATCH `{ ativo: true }`, o
 * mesmo endpoint usado para editar qualquer outro campo (não existe um
 * endpoint separado de "reativar"). */
export interface ContaUpdate {
  nome?: string;
  tipo?: TipoConta;
  saldo_inicial?: string;
  instituicao?: string | null;
  ativo?: boolean;
}

/**
 * Espelha `app/schemas/conta.py` (`MovimentacaoContaRead`,
 * `MaiorMovimentacaoRead`, `ContaExtratoResumo`, `ContaResumoMesAtual`,
 * `ContaExtratoRead`) — extrato bancário de uma Conta, painel expansível
 * de `ContaResumoCard`. Ver docs/analise-arquitetural-extrato-conta.md.
 */
export interface MovimentacaoConta {
  data: string;
  descricao: string;
  valor: string;
  positivo: boolean;
  categoria: CategoriaMovimentacaoConta;
  origem_tipo: TipoEntidadeReferenciavel;
  origem_id: number;
}

export interface MaiorMovimentacao {
  data: string;
  descricao: string;
  valor: string;
}

/** Resumo do PERÍODO navegado (`ano`/`mes` da requisição) —
 * `saldo_atual`/`saldo_inicial` são sempre o valor real de agora,
 * independente do período. */
export interface ContaExtratoResumo {
  saldo_atual: string;
  saldo_inicial: string;
  entradas_periodo: string;
  saidas_periodo: string;
  saldo_liquido_periodo: string;
  ultima_movimentacao: string | null;
  quantidade_movimentacoes: number;
}

/** Sempre o mês corrente de verdade — constante independente do período
 * navegado em `ContaExtratoResumo`. */
export interface ContaResumoMesAtual {
  entradas_mes: string;
  saidas_mes: string;
  saldo_mes: string;
  maior_entrada: MaiorMovimentacao | null;
  maior_saida: MaiorMovimentacao | null;
}

export interface ContaExtrato {
  resumo: ContaExtratoResumo;
  resumo_mes_atual: ContaResumoMesAtual;
  movimentacoes: MovimentacaoConta[];
}
