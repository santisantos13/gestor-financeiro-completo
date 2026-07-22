/**
 * Todas as chaves de query do React Query, centralizadas. Hooks e
 * invalidacoes sempre importam daqui - nunca escrevem `["contas"]` literal
 * inline (ver docs/analise-arquitetural-frontend.md, secao 9). Cada
 * entidade ganha sua secao quando a etapa dela comeca.
 *
 * `dashboard` (Etapa F3, docs/analise-arquitetural-dashboard.md secao 6.3):
 * uma chave por endpoint de `/central-financeira/*`. `resumo`/`visaoMensal`
 * sao funcoes (dependem de `ano`/`mes`); `agenda` depende de `dias`; as
 * demais 8 sao constantes (sem parametro que mude a query).
 *
 * `contas` (Etapa F6, CRUD real via `/contas/*`, diferente de
 * `dashboard.contas`, que le de `/central-financeira/contas`, um endpoint
 * agregador somente-leitura separado): `list` depende de `apenasAtivas`
 * (o unico parametro de listagem que o backend aceita), `detail` depende
 * do `id`.
 */
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  dashboard: {
    resumo: (ano?: number, mes?: number) => ["dashboard", "resumo", ano, mes] as const,
    saldoConsolidado: ["dashboard", "saldo-consolidado"] as const,
    contas: ["dashboard", "contas"] as const,
    cartoes: ["dashboard", "cartoes"] as const,
    cartoesAgregado: ["dashboard", "cartoes-agregado"] as const,
    faturas: ["dashboard", "faturas"] as const,
    financiamentos: ["dashboard", "financiamentos"] as const,
    emprestimos: ["dashboard", "emprestimos"] as const,
    metas: ["dashboard", "metas"] as const,
    agenda: (dias: number) => ["dashboard", "agenda", dias] as const,
    /** Etapa de Calendário Financeiro - `GET /central-financeira/calendario`,
     * endpoint IRMÃO de `agenda` (não substitui), escopado por mês/ano
     * (mesmo padrão de `resumo`/`visaoMensal`). Ver
     * docs/analise-arquitetural-transferencias-frontend.md. */
    calendario: (ano: number, mes: number) => ["dashboard", "calendario", ano, mes] as const,
    /** Central de Atividades (Sprint de Refinamento Premium, item 17) -
     * `GET /central-financeira/atividades`, feed cronológico. */
    atividades: (limit: number) => ["dashboard", "atividades", limit] as const,
    visaoMensal: (ano?: number, mes?: number) => ["dashboard", "visao-mensal", ano, mes] as const,
    indicadores: ["dashboard", "indicadores"] as const,
    /** Etapa de Gráficos — `GET /central-financeira/graficos/tendencias`,
     * janela dos últimos `meses` meses. */
    graficosTendencias: (meses: number) => ["dashboard", "graficos-tendencias", meses] as const,
    /** `GET /central-financeira/graficos/periodo` — escopo de um único mês
     * (mesmo padrão de `calendario`). */
    graficosPeriodo: (ano?: number, mes?: number) =>
      ["dashboard", "graficos-periodo", ano, mes] as const,
  },
  contas: {
    all: ["contas"] as const,
    list: (apenasAtivas: boolean) => ["contas", "list", apenasAtivas] as const,
    detail: (id: number) => ["contas", "detail", id] as const,
    /** Extrato (histórico expansível) de uma Conta - escopado por
     * `ano`/`mes` (undefined = mês atual, mesma chave "sem período"
     * definido continua estável entre renders). Prefixo `["contas",
     * "extrato", id]` já casa com `queryKeys.contas.all` (`["contas"]`),
     * então nenhuma invalidação extra precisou ser adicionada em
     * `useContaQueries.ts` - toda mutation que já invalida `contas.all`
     * também invalida o extrato de qualquer conta aberta. */
    extrato: (id: number, ano?: number, mes?: number) => ["contas", "extrato", id, ano, mes] as const,
  },
  /** Etapa F7, CRUD real via `/categorias/*`. Nenhuma chave de Dashboard e
   * invalidada por mutation de Categoria - diferente de `contas`, nenhum
   * dos 11 endpoints de `/central-financeira/*` agrega Categoria (ver
   * docs/analise-arquitetural-categoria-frontend.md, secao 6). */
  categorias: {
    all: ["categorias"] as const,
    list: (apenasAtivas: boolean, incluirOcultas = false) =>
      ["categorias", "list", apenasAtivas, incluirOcultas] as const,
    detail: (id: number) => ["categorias", "detail", id] as const,
  },
  /** Etapa F8, CRUD real via `/tags/*`. Mesmo raciocinio de `categorias`:
   * nenhuma chave de Dashboard e invalidada por mutation de Tag. */
  tags: {
    all: ["tags"] as const,
    list: (apenasAtivas: boolean) => ["tags", "list", apenasAtivas] as const,
    detail: (id: number) => ["tags", "detail", id] as const,
    /** Etapa F10 (Exclusão definitiva) — `GET /tags/{id}/uso`, só
     * informativo, nunca invalidado por outra mutation (consultado sob
     * demanda ao abrir a confirmação de excluir). */
    uso: (id: number) => ["tags", "uso", id] as const,
  },
  /** Etapa F9, CRUD real via `/cartoes/*`. Diferente de `categorias`/`tags`,
   * mutation de Cartão invalida `dashboard.cartoes` e `dashboard.indicadores`
   * (mesmo raciocinio de `contas` — ver docs/analise-arquitetural-cartao-frontend.md,
   * seção 6). */
  cartoes: {
    all: ["cartoes"] as const,
    list: (apenasAtivas: boolean) => ["cartoes", "list", apenasAtivas] as const,
    detail: (id: number) => ["cartoes", "detail", id] as const,
  },
  /** Etapa F10, CRUD real via `/faturas/*`. Diferente de todas as
   * entidades anteriores, `list` é sempre escopada a um `cartaoId` (o
   * backend exige — nunca existe uma chave "todas as faturas do usuário"
   * aqui, ver docs/analise-arquitetural-fatura-frontend.md, seção 0).
   * Mutation de Fatura também invalida `dashboard.faturas`/
   * `dashboard.cartoes` (a Central Financeira agrega os mesmos dados). */
  faturas: {
    list: (cartaoId: number) => ["faturas", "list", cartaoId] as const,
    detail: (id: number) => ["faturas", "detail", id] as const,
  },
  /** Etapa de Transação, CRUD real via `/transacoes/*`. Diferente de toda
   * entidade anterior, `list` depende do objeto de filtros inteiro (não só
   * um booleano `apenasAtivas`) — o backend filtra de verdade por período/
   * tipo/status/categoria/conta/cartão (ver
   * docs/analise-arquitetural-transacao-frontend.md, seção 2), então cada
   * combinação de filtros é uma query diferente de verdade, não uma
   * derivação client-side de uma lista já carregada. */
  transacoes: {
    all: ["transacoes"] as const,
    list: (filtros: object) => ["transacoes", "list", filtros] as const,
    detail: (id: number) => ["transacoes", "detail", id] as const,
  },
  /** Etapa de Transferências, CRUD real via `/transferencias/*`. Sem
   * `Update` (imutável após criação - ver `types/transferencia.ts`);
   * mutation de Transferência invalida `contas.all` (afeta o saldo de DUAS
   * contas) e as chaves de Dashboard/Calendário que dependem de saldo -
   * mesmo raciocínio de `transacoes` (ver
   * `hooks/useTransferenciaQueries.ts`). */
  transferencias: {
    all: ["transferencias"] as const,
    list: (apenasAtivas: boolean) => ["transferencias", "list", apenasAtivas] as const,
    detail: (id: number) => ["transferencias", "detail", id] as const,
    /** Refatoramento de Metas/Transferências: histórico de aportes/resgates
     * do "cofrinho" de uma Meta (`MetaResumoCard`) - casa por PREFIXO com
     * `all` (mesmo raciocínio de `list`/`detail` acima), então qualquer
     * mutation de Transferência já invalida isso de graça. */
    porConta: (contaId: number) => ["transferencias", "porConta", contaId] as const,
  },
  /** `detail(id)` existe desde o diálogo de confirmação de exclusão de
   * compra parcelada (`TransacoesPage`, ver
   * docs/analise-arquitetural-escopo-parcelamento.md, seção 4) — precisa
   * ler `num_parcelas` para mostrar "Esta compra possui N parcelas" antes
   * de excluir. `all` continua sendo o único alvo de invalidação (nenhuma
   * mutation própria de Parcelamento existe além de `criar`/o cancelamento
   * implícito via exclusão de Transação) — casa `detail(id)` por prefixo
   * automaticamente, mesmo padrão de `cartoes`/`contas`. Ainda não existe
   * listagem própria de Parcelamento no frontend. */
  parcelamentos: {
    all: ["parcelamentos"] as const,
    detail: (id: number) => ["parcelamentos", "detail", id] as const,
  },
  /** Etapa de Onboarding, CRUD real via `/financiamentos/*`. `list` usa o
   * endpoint próprio (não `dashboard.financiamentos`/central-financeira,
   * que hardcoda `apenas_ativos=True` no backend e nunca mostraria um
   * contrato QUITADO — ver `CentralFinanceiraService.resumo_financiamentos`
   * — errado para a página de CRUD, cujo objetivo é ser o lar de TODOS os
   * contratos). `detail` é usado pelo Drawer de cronograma. */
  financiamentos: {
    list: (apenasAtivos: boolean) => ["financiamentos", "list", apenasAtivos] as const,
    detail: (id: number) => ["financiamentos", "detail", id] as const,
  },
  /** Etapa de Onboarding, CRUD real via `/emprestimos/*`. Mesmo raciocínio
   * de `financiamentos`. */
  emprestimos: {
    list: (apenasAtivos: boolean) => ["emprestimos", "list", apenasAtivos] as const,
    detail: (id: number) => ["emprestimos", "detail", id] as const,
  },
  /** Etapa F12, CRUD real via `/metas/*`. `list` sempre busca TODAS
   * (`apenasAtivas=false`) — volume baixo por natureza (poucas metas de
   * vida ativas por usuário), então os filtros rápidos (Em andamento/
   * Concluídas/Atrasadas/Desativadas) e a ordenação são 100% client-side
   * sobre a lista já em memória (ver docs/analise-arquitetural-metas-frontend.md,
   * seção 2.4/2.5) — evita uma segunda chamada de API só para "mostrar
   * desativadas". */
  metas: {
    all: ["metas"] as const,
    list: (apenasAtivas: boolean) => ["metas", "list", apenasAtivas] as const,
    detail: (id: number) => ["metas", "detail", id] as const,
  },
  /** Expansão de Contas Recorrentes (2026-07-20). `list` sempre busca
   * TODAS (sem filtro de status) — volume baixo (dezenas no máximo), e os
   * filtros por status (Ativas/Pausadas/Encerradas) são client-side sobre
   * a lista em memória, mesmo raciocínio de `metas`. */
  recorrentes: {
    all: ["recorrentes"] as const,
    list: () => ["recorrentes", "list"] as const,
    detail: (id: number) => ["recorrentes", "detail", id] as const,
  },
  /** CRUD frontend de Anexo (docs/analise-arquitetural-anexo-frontend.md).
   * Diferente de toda entidade anterior, não existe `all`/`detail` — o
   * backend não expõe uma listagem global (`AnexoRepository` só tem
   * `listar_por_transacao`, posse é sempre transitiva via Transação), então
   * a única chave é a lista escopada por `transacaoId`. */
  anexos: {
    list: (transacaoId: number) => ["anexos", "list", transacaoId] as const,
  },
} as const;
