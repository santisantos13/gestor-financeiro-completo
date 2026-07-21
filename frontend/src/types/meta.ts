/**
 * Espelha 1:1 `app/schemas/meta.py` — conferido por leitura direta do
 * backend. `valor_acumulado`/`percentual` existem só em `MetaRead` (sempre
 * calculados pelo `MetaService`, nunca colunas do model — mesmo princípio
 * de `CartaoRead.limite_disponivel`/`ContaRead.saldo_atual`). O Frontend
 * NUNCA reproduz essa conta — só lê, formata e anima o valor já pronto
 * (ver docs/analise-arquitetural-metas-frontend.md, seção 1).
 *
 * `criado_em` foi acrescentado ao `MetaRead` na Etapa F12.
 *
 * Refinamento de Metas (`docs/analise-arquitetural-metas-refinamento.md`):
 * `frequencia_contribuicao` é o único campo genuinamente novo e
 * PERSISTIDO (escolha do usuário); `concluida_em` também é persistido
 * (gravado lazily pelo backend na primeira vez que `percentual` cruza
 * 100%). Todos os demais campos novos (`contribuicao_sugerida_por_periodo`,
 * `valor_planejado_ate_hoje`, `diferenca_planejado_realizado`,
 * `situacao_planejamento`, `data_prevista_conclusao`) são CALCULADOS pelo
 * `MetaService` a cada leitura — o Frontend nunca reproduz essas fórmulas,
 * só lê/formata/anima o valor já pronto, mesmo princípio de
 * `valor_acumulado`/`percentual`.
 *
 * Refatoramento de Metas/Transferências
 * (`docs/analise-arquitetural-metas-transferencias.md`): `conta_id` deixou
 * de ser uma escolha do usuário — não existe mais em `MetaCreate`/
 * `MetaUpdate`. Toda Meta ganha automaticamente um "cofrinho" (Conta
 * dedicada e oculta) no backend; `MetaRead.conta_id` agora é sempre
 * `number` (nunca `null`) e o Frontend só usa esse id para montar o
 * payload de aporte/resgate (`POST /transferencias`) — nunca mostra essa
 * conta ao usuário diretamente (ela nem aparece em `GET /contas`, oculta
 * por padrão no backend).
 */
export type FrequenciaContribuicao = "DIARIA" | "SEMANAL" | "QUINZENAL" | "MENSAL";

export type SituacaoPlanejamentoMeta = "ADIANTADO" | "DENTRO_DO_PLANEJADO" | "ATRASADO";

export interface MetaRead {
  id: number;
  descricao: string;
  valor_alvo: string;
  data_alvo: string | null;
  /** Sempre preenchido — id do "cofrinho" automático desta Meta. Nunca
   * mostrado ao usuário diretamente, só usado para montar o payload de
   * aporte/resgate (ver docstring do módulo). */
  conta_id: number;
  ativo: boolean;
  frequencia_contribuicao: FrequenciaContribuicao | null;
  valor_acumulado: string;
  percentual: string;
  criado_em: string;
  /** Data em que a meta foi concluída (percentual >= 100%) PELA PRIMEIRA
   * VEZ — nunca desfeita depois, mesmo que o percentual caia (ver seção
   * 4.1 da análise). Usada tanto para o histórico ("data de conclusão",
   * "tempo até concluir") quanto para disparar a celebração uma única vez
   * (controle de "já mostrei" fica em `localStorage`, nunca aqui). */
  concluida_em: string | null;
  /** Quanto guardar por período (na frequência escolhida) para chegar no
   * prazo — `null` sem frequência/prazo definidos, com o prazo já vencido
   * ou com a meta já concluída (seção 1.2). Informação de apoio, nunca
   * substitui `valor_acumulado`/`percentual`. */
  contribuicao_sugerida_por_periodo: string | null;
  /** Projeção linear de quanto já deveria estar acumulado hoje, considerando
   * `criado_em`→`data_alvo` (seção 2.1). `null` sem `data_alvo`. */
  valor_planejado_ate_hoje: string | null;
  /** `valor_acumulado - valor_planejado_ate_hoje` — positivo = acima do
   * planejado, negativo = abaixo (seção 2.2). `null` quando
   * `valor_planejado_ate_hoje` for `null`. */
  diferenca_planejado_realizado: string | null;
  /** Classificação com banda de tolerância de 2% do valor_alvo (seção
   * 2.3). `null` sem `data_alvo` ou com a meta já concluída. */
  situacao_planejamento: SituacaoPlanejamentoMeta | null;
  /** No ritmo atual (desde `criado_em`), quando a meta seria concluída —
   * `null` sem nenhum progresso real ainda, com a meta já concluída, ou
   * quando o ritmo for baixo demais para uma previsão confiável (seção
   * 3.1). */
  data_prevista_conclusao: string | null;
}

export interface MetaCreate {
  descricao: string;
  valor_alvo: string;
  data_alvo?: string | null;
  frequencia_contribuicao?: FrequenciaContribuicao | null;
}

/** Semântica de PATCH — todo campo omitido permanece intocado. Reativar
 * uma meta desativada é `PATCH { ativo: true }`, mesmo endpoint de edição
 * (mesma decisão de Conta/Categoria/Tag/Cartão). */
export interface MetaUpdate {
  descricao?: string;
  valor_alvo?: string;
  data_alvo?: string | null;
  ativo?: boolean;
  frequencia_contribuicao?: FrequenciaContribuicao | null;
}
