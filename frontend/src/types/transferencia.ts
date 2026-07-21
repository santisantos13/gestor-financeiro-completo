/**
 * Espelha 1:1 `app/schemas/transferencia.py` (backend). Ver
 * docs/analise-arquitetural-transferencias-frontend.md, seções 0 e 4.
 *
 * Sem `TransferenciaUpdate` - decisão do backend, não uma omissão: os
 * campos estruturais (`conta_origem_id`/`conta_destino_id`/`valor`/`data`)
 * são imutáveis após a criação (editar exigiria refazer o cálculo de saldo
 * das duas contas envolvidas). A única transição de estado é a ação
 * `cancelar` (`POST /transferencias/{id}/cancelar`), sem payload.
 */
export interface TransferenciaRead {
  id: number;
  conta_origem_id: number;
  conta_destino_id: number;
  valor: string;
  data: string;
  descricao: string | null;
  ativo: boolean;
}

export interface TransferenciaCreate {
  conta_origem_id: number;
  conta_destino_id: number;
  valor: string;
  data: string;
  descricao?: string | null;
}

/** `GET /transferencias` - parâmetros reais que o backend aceita além de
 * paginação (diferente de Transação, que filtra por período/tipo/status/
 * categoria/conta/cartão de verdade - aqui o filtro server-side é mais
 * enxuto). `conta_id` (genérico, não específico de Meta) foi acrescentado
 * no Refatoramento de Metas/Transferências
 * (docs/analise-arquitetural-metas-transferencias.md, seção 4.2) - usado
 * para montar o histórico de aportes/resgates do "cofrinho" de uma Meta
 * (`MetaResumoCard`), mas serve qualquer conta. */
export interface TransferenciaFiltros {
  apenas_ativas?: boolean;
  conta_id?: number;
  skip?: number;
  limit?: number;
}
