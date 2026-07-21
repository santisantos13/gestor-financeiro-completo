# Análise arquitetural — Dashboard (Central Financeira)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Mesma convenção
usada em todo o projeto: esta análise é lida e aprovada antes da primeira linha de código,
mesmo rigor de `docs/analise-arquitetural-frontend.md` e `docs/central-financeira-especificacao.md`
(backend). Escopo: consumir os endpoints de `/central-financeira/*` e construir o Dashboard
principal da aplicação — a primeira tela com dado financeiro real.

**Backend encerrado, mesmo princípio de sempre**: nenhum endpoint, contrato ou regra de
negócio é alterado por esta etapa. Tudo abaixo foi conferido por leitura direta do código
real do backend (`app/api/routes/central_financeira.py`, `app/schemas/central_financeira.py`
e os schemas `Read` de cada entidade referenciada) — não da especificação funcional original
(`docs/central-financeira-especificacao.md`), que é um documento de produto anterior à
implementação e diverge do que foi de fato construído em alguns pontos (seção 4 detalha
cada divergência encontrada).

## 0. Decisões que divergem de documentos já aprovados — sinalizadas antes de prosseguir

1. **Renumeração de etapa.** `docs/analise-arquitetural-frontend.md` (seção 16) planejava
   `F3 — Sistema de formulários` → `F4 — Sistema de tabelas` → `F5 — Dashboard`. Você pediu
   esta etapa como **"Etapa F3"**, ou seja, o Dashboard passa a vir logo depois do Design
   System (F2), antes de Formulários e Tabelas. Entendo isso como uma reordenação
   deliberada do roteiro (Formulários e Tabelas só fazem falta quando o app precisar
   *escrever* dado — Dashboard é 100% leitura, então faz sentido validar a experiência
   visual completa primeiro). Não altero o texto de `analise-arquitetural-frontend.md`
   seção 16 a menos que você quera — só registro aqui que a ordem real de execução diverge
   do roteiro escrito lá.
2. **`docs/central-financeira-especificacao.md` descreve mais do que o backend implementou.**
   O documento de produto original previa Alertas, Insights e um card de Parcelamentos.
   Conferido por leitura direta do router (`central_financeira.py`, docstring: "11 endpoints
   agregadores, 100% somente-leitura"): **não existem rotas `/alertas`, `/insights` nem
   `/parcelamentos`** — só os 11 endpoints da seção 3 abaixo. Alertas/Insights/Parcelamentos
   ficam fora do escopo desta etapa por não terem dado nenhum para consumir (não é uma
   omissão de UI, é ausência de endpoint) — seção 4 detalha.
3. **Nenhuma biblioteca de gráfico foi escolhida.** `docs/design-system.md` (seção 16)
   registra isso explicitamente: *"Biblioteca de gráfico: decisão adiada para a Etapa
   F5 [Dashboard], fora do escopo [do Design System]"*. Ou seja, a decisão foi adiada para
   *esta* etapa, não para depois dela — mas escolher e instalar uma lib nova de gráfico é
   uma decisão de dependência que prefiro sinalizar em vez de decidir sozinho no meio de uma
   implementação já grande. Proposta desta análise (seção 8.6): a seção "Visão Mensal" usa
   uma barra comparativa simples feita com `div`s estilizados (sem nova dependência) nesta
   etapa; gráficos de verdade (fluxo de caixa histórico, evolução de financiamento) ficam
   para uma etapa futura dedicada, quando fizer sentido escolher a lib com calma. Avise se
   preferir decidir a lib agora.

## 1. Objetivo desta etapa

Construir `pages/dashboard/DashboardPage.tsx` consumindo os 11 endpoints reais de
`/central-financeira/*`, substituindo o placeholder da Etapa F1. Junto: a rota permanente
`/dev` (laboratório visual de componentes, seção 12) e o utilitário de formatação de
dinheiro/data que nenhuma etapa anterior precisou construir ainda (seção 7.4).

Fora de escopo (reafirmando o pedido original): nenhuma tela de CRUD, nenhuma edição de
dado, nenhuma regra financeira nova — o frontend só formata e exibe o que os 11 endpoints
já calculam.

## 2. Pré-requisitos confirmados (o que já existe, por leitura direta)

- **F1 (fundação)**: `react-router-dom`, `@tanstack/react-query`, `httpClient`,
  `AuthContext`, `ProtectedRoute`, estrutura de pastas definitiva (`api/`, `types/`,
  `services/`, `hooks/`, `components/{ui,layout,domain}`, `pages/`, `routes/`, `utils/`).
- **F2 (Design System)**: tokens (cor/tipografia/espaço/radius/sombra/blur/motion) como
  CSS custom properties + `tailwind.config.js`; `lib/motion.ts` (`DURATION`, `EASE`,
  `SPRING`, `fadeIn`, `modalBackdrop`, `modalPanel`, `toastVariants`); `MotionConfig
  reducedMotion="user"` no `App.tsx`; componentes base já prontos em `components/ui/`:
  `Avatar`, `Badge`, `Button`, `Checkbox`, `Divider`, `ErrorMessage`, `Input`, `Kbd`,
  `ProgressBar`, `Select`, `Spinner`, `Switch`, `Textarea`, `Tooltip`; `Sidebar`/`Header`
  em `components/layout/`.
- **O que NÃO existe ainda** (confirmado por busca no projeto, não assumido): `Card` (
  superfície base reutilizável), `EmptyState`, `Skeleton`, `StatCard` e qualquer outro
  componente específico de dashboard (nenhum foi construído na F2 — a seção 14 do
  design-system especifica visual, não implementa); `utils/format.ts`/`utils/date.ts`
  (a F1/F2 nunca precisaram formatar dinheiro real); `queryKeys.ts` só tem a seção `auth`
  hoje; `App.tsx` já configura `staleTime: 30_000` e retry (4xx nunca re-tenta, 5xx/rede
  tenta 1x) — nada a mudar aqui, os hooks novos herdam isso automaticamente.

## 3. Contrato real da API — 11 endpoints (fonte: leitura direta do backend)

Nenhuma rota aceita `usuario_id` (vem do token, `CurrentUser`). Todos `GET`, somente
leitura. Todo `Decimal` chega como `string` (herdado de `analise-arquitetural-frontend.md`,
seção 0 — nunca convertido para `number`, nunca recalculado no cliente).

| # | Endpoint | Query params | Schema de resposta |
|---|---|---|---|
| 1 | `/central-financeira/resumo` | `ano?`, `mes?` (default: mês corrente, resolvido no backend) | `ResumoFinanceiroRead`: `ano`, `mes`, `saldo_total`, `entradas_mes`, `saidas_mes`, `fluxo_caixa_mes`, `patrimonio_liquido` |
| 2 | `/central-financeira/saldo-consolidado` | — | `SaldoConsolidadoRead`: `saldo_total`, `contas: {id, nome, saldo_atual}[]` |
| 3 | `/central-financeira/contas` | — | `ResumoContasRead`: `contas: ContaRead[]` (`id`, `nome`, `tipo`, `saldo_inicial`, `saldo_atual`, `instituicao`, `ativo`) |
| 4 | `/central-financeira/cartoes` | — | `ResumoCartoesRead`: `cartoes: CartaoRead[]` (`id`, `nome`, `conta_pagamento_id`, `instituicao`, `bandeira`, `ultimos_quatro_digitos`, `limite`, `limite_disponivel`, `dia_fechamento`, `dia_vencimento`, `ativo`) + `total_utilizado` |
| 5 | `/central-financeira/faturas` | — | `ResumoFaturasRead`: `faturas: FaturaRead[]` (`id`, `cartao_id`, `mes_referencia`, `data_fechamento`, `data_vencimento`, `valor_pago`, `valor_total`, `status`) |
| 6 | `/central-financeira/financiamentos` | — | `ResumoFinanciamentosRead`: `financiamentos: FinanciamentoResumo[]` (todos os campos de `FinanciamentoRead` + `parcelas_pagas`, `parcelas_restantes`, `valor_total_pago`, `proxima_parcela_data`, `proxima_parcela_valor`) |
| 7 | `/central-financeira/emprestimos` | — | `ResumoEmprestimosRead`: `emprestimos: EmprestimoResumo[]` (mesma forma de `FinanciamentoResumo`, campos de `EmprestimoRead`) |
| 8 | `/central-financeira/metas` | — | `ProgressoMetasRead`: `metas: MetaRead[]` (`id`, `descricao`, `valor_alvo`, `data_alvo`, `conta_id`, `ativo`, `valor_acumulado`, `percentual`) |
| 9 | `/central-financeira/agenda` | `dias` (default 30, 0-3650) | `AgendaFinanceiraRead`: `eventos: {data, descricao, valor, origem_tipo, origem_id}[]`, já ordenado por data pelo backend |
| 10 | `/central-financeira/visao-mensal` | `ano?`, `mes?` | `VisaoMensalRead`: `ano`, `mes`, `entradas`, `saidas`, `fluxo_caixa` |
| 11 | `/central-financeira/indicadores` | — | `IndicadoresGeraisRead`: `contas_ativas`, `cartoes_ativos`, `faturas_em_aberto`, `financiamentos_ativos`, `emprestimos_ativos`, `metas_ativas`, `percentual_medio_metas`, `parcelas_atrasadas` (todos `int`, exceto `percentual_medio_metas` que é `Decimal`) |

`FinanciamentoResumo`/`EmprestimoResumo` também trazem `saldo_devedor` e `status`
(`StatusContratoCredito`) herdados de `FinanciamentoRead`/`EmprestimoRead` — já contados
acima como "todos os campos de".

### 3.1 Sobre `#1` vs `#10` (resumo × visão mensal)

Os dois trazem `entradas`/`saidas`/`fluxo_caixa` do mesmo período — não é engano de leitura,
são dois endpoints reais e distintos no backend. Tratamento nesta análise: `#1 resumo`
alimenta os StatCards de destaque no topo (seção 8.2); `#10 visao-mensal` alimenta a
comparação visual "Entradas vs. Saídas" (seção 8.6) — visualmente diferentes, mesmo dado
por trás, sem chamada duplicada desnecessária evitada (cada card usa seu próprio endpoint,
consistente com "um endpoint por seção" já decidido no backend).

### 3.2 Sobre `#2` vs `#3` (saldo consolidado × contas)

Também não são duplicados: `#2` é o recorte mínimo (`id`, `nome`, `saldo_atual`) pensado
para a "fotografia rápida" do topo; `#3` é a listagem completa (`tipo`, `saldo_inicial`,
`instituicao`, `ativo`) para o card de detalhamento por domínio. Tratados como duas seções
visuais diferentes (seção 8.2 e 8.5).

## 4. Fora de escopo desta etapa (confirmado por ausência real no backend)

- **Alertas** — endpoint `/central-financeira/alertas` não existe. `docs/analise-arquitetural-frontend.md`
  (seção 0) já registrava isso para a entidade `Alerta` de forma geral ("sem router nem
  schema no backend ainda").
- **Insights** — endpoint `/central-financeira/insights` não existe.
- **Parcelamentos** — sem endpoint próprio na Central Financeira (`ParcelamentoService`
  existe no backend para o CRUD direto, mas a Central não agrega isso hoje).
- **Gráficos de verdade** (linha do tempo de fluxo de caixa, evolução de financiamento) —
  sem lib escolhida (seção 0.3). A "Visão Mensal" desta etapa é uma comparação visual
  simples, não um gráfico de biblioteca.
- **Seletor de período avançado** — a especificação original (central-financeira-especificacao.md,
  seção 3) menciona navegação livre mês a mês. Esta etapa implementa isso de forma simples
  (seção 8.1: anterior/próximo mês, sem seletor de calendário/range) — suficiente para o
  que os endpoints `resumo`/`visao-mensal` aceitam (`ano`, `mes` únicos).

## 5. Estrutura de arquivos novos

```
frontend/src/
├── types/
│   └── centralFinanceira.ts        # espelha os 11 schemas da seção 3, 1:1
├── services/
│   └── centralFinanceiraService.ts # 11 funções finas, uma por endpoint
├── api/
│   └── queryKeys.ts                 # ganha a seção `dashboard` (11 chaves)
├── hooks/
│   └── useCentralFinanceiraQueries.ts  # 11 hooks useQuery, um por endpoint
├── utils/
│   ├── format.ts                    # formatMoney(string) -> "R$ 1.234,56", formatPercent, etc.
│   └── date.ts                      # formatDate, próxima ocorrência de um dia-do-mês (seção 8.5)
├── components/
│   ├── ui/                          # peças genéricas novas (seção 9.1)
│   │   ├── Card.tsx
│   │   ├── EmptyState.tsx
│   │   ├── Skeleton.tsx
│   │   ├── StatCard.tsx
│   │   ├── AnimatedNumber.tsx
│   │   ├── TrendIndicator.tsx
│   │   ├── FinancialBadge.tsx
│   │   ├── LoadingCard.tsx
│   │   ├── SectionTitle.tsx
│   │   └── MetricCard.tsx
│   └── domain/dashboard/            # peças que conhecem os DTOs da Central (seção 9.2)
│       ├── ResumoFinanceiroSection.tsx
│       ├── SaldoPorContaCard.tsx
│       ├── ContasCard.tsx
│       ├── CartoesCard.tsx
│       ├── FaturasCard.tsx
│       ├── FinanciamentosCard.tsx
│       ├── EmprestimosCard.tsx
│       ├── MetasCard.tsx
│       ├── AgendaFinanceiraCard.tsx
│       ├── VisaoMensalCard.tsx
│       ├── IndicadoresStrip.tsx
│       ├── PeriodoSeletor.tsx
│       └── DashboardOnboarding.tsx
├── pages/
│   ├── dashboard/DashboardPage.tsx  # reescrita completa, monta o Bento Grid
│   └── dev/DevPage.tsx              # laboratório visual (seção 12)
└── routes/
    └── AppRoutes.tsx                 # ganha a rota /dev
```

## 6. Camada de dados

### 6.1 `types/centralFinanceira.ts`

Um `interface` por schema da seção 3, nomeados igual ao backend (`ResumoFinanceiroRead`,
`SaldoConsolidadoRead`, etc. — mesma convenção 1:1 já usada em `types/auth.ts`). Reaproveita
`ContaRead`/`CartaoRead`/`FaturaRead`/`FinanciamentoRead`/`EmprestimoRead`/`MetaRead` — que
ainda **não existem** em `types/` (só foram criados os schemas Zod/TS de `auth` até agora,
já que nenhuma entidade de domínio teve tela ainda). Esta etapa cria o mínimo necessário
desses tipos (só os campos que `Read` expõe, sem `Create`/`Update` — não há formulário
nesta etapa) diretamente em `types/centralFinanceira.ts`, para não duplicar trabalho: quando
a Etapa de CRUD de cada entidade chegar (F6+), esses tipos completos (`Create`/`Update`)
nascem em `types/<entidade>.ts` próprios, e os tipos `Read` usados aqui podem ser
re-exportados de lá em vez de duplicados — sinalizado para revisão nessa hora futura, não
uma decisão a se preocupar agora.

### 6.2 `services/centralFinanceiraService.ts`

Onze funções finas, mesmo padrão de `authService.ts` — só chamam `httpClient.get`, zero
decisão:

```ts
export const centralFinanceiraService = {
  resumo: (ano?: number, mes?: number) =>
    httpClient.get<ResumoFinanceiroRead>("/central-financeira/resumo", { ano, mes }),
  saldoConsolidado: () =>
    httpClient.get<SaldoConsolidadoRead>("/central-financeira/saldo-consolidado"),
  // ...as demais 9, mesmo padrão
};
```

### 6.3 `queryKeys.ts` — nova seção `dashboard`

```ts
export const queryKeys = {
  auth: { me: ["auth", "me"] as const },
  dashboard: {
    resumo: (ano?: number, mes?: number) => ["dashboard", "resumo", ano, mes] as const,
    saldoConsolidado: ["dashboard", "saldo-consolidado"] as const,
    contas: ["dashboard", "contas"] as const,
    cartoes: ["dashboard", "cartoes"] as const,
    faturas: ["dashboard", "faturas"] as const,
    financiamentos: ["dashboard", "financiamentos"] as const,
    emprestimos: ["dashboard", "emprestimos"] as const,
    metas: ["dashboard", "metas"] as const,
    agenda: (dias: number) => ["dashboard", "agenda", dias] as const,
    visaoMensal: (ano?: number, mes?: number) => ["dashboard", "visao-mensal", ano, mes] as const,
    indicadores: ["dashboard", "indicadores"] as const,
  },
} as const;
```

### 6.4 `hooks/useCentralFinanceiraQueries.ts`

Onze `useQuery`, mesmo formato já documentado em `analise-arquitetural-frontend.md` (seção
9) — nenhum `useState` de loading/erro escrito à mão:

```ts
export function useResumoFinanceiroQuery(ano?: number, mes?: number) {
  return useQuery({
    queryKey: queryKeys.dashboard.resumo(ano, mes),
    queryFn: () => centralFinanceiraService.resumo(ano, mes),
  });
}
// ...as demais 10, mesmo padrão. useAgendaFinanceiraQuery(dias = 30) tem parâmetro;
// os outros 9 não recebem argumento.
```

Nenhuma mutation aqui — a Central é 100% leitura, sem `useCriarXMutation`/invalidação.

## 7. Orquestração de carregamento

### 7.1 Gate de onboarding

`indicadores.contas_ativas === 0` é o sinal mais barato e confiável de "usuário sem
nenhuma conta cadastrada ainda" — usado para decidir entre o Dashboard normal e a tela de
onboarding (seção 9.3, `DashboardOnboarding`), evitando a "parede de zeros" que
`central-financeira-especificacao.md` (seção 2) já apontava como erro a evitar.
`DashboardPage` busca `useIndicadoresGeraisQuery()` primeiro; enquanto carrega, mostra um
skeleton de página inteira; ao resolver, decide entre as duas árvores — as outras 10
queries só montam (e disparam) depois dessa decisão, dentro da árvore escolhida.

### 7.2 Paralelização das 10 queries restantes

Cada seção do Bento Grid (seção 8) é seu próprio componente com seu próprio hook — React
Query dispara as 10 chamadas em paralelo naturalmente (nenhum `Promise.all` manual
necessário, mesmo comportamento já descrito em `central-financeira-especificacao.md`, seção
11: "o frontend já paraleliza naturalmente fazendo as N chamadas ao mesmo tempo"). Uma
seção lenta (ex. Agenda, que funde 3 fontes no backend) nunca atrasa uma seção rápida (ex.
Saldo Consolidado) — cada `<XCard />` tem seu próprio estado de loading/erro/sucesso,
nunca um spinner global bloqueando a tela inteira.

### 7.3 Período compartilhado

`ResumoFinanceiroSection` e `VisaoMensalCard` são os dois consumidores de `ano`/`mes`.
Estado local em `DashboardPage` (`useState<{ano: number; mes: number}>`, inicializado com
o mês corrente via `new Date()`), passado como prop para os dois — não vai para a URL
(YAGNI: app de usuário único, sem necessidade de compartilhar/bookmarkar um período
específico agora; fácil de promover para query string depois se isso mudar).
`PeriodoSeletor` (seção 9.2) expõe `‹ Julho 2026 ›`, cada seta decrementa/incrementa `mes`
(com rollover de `ano` em janeiro/dezembro).

### 7.4 `utils/format.ts` / `utils/date.ts` — infraestrutura que esta etapa cria

Nenhuma etapa anterior precisou formatar dinheiro de verdade (só texto/e-mail/senha em
formulário). Criados agora porque o Dashboard é a primeira tela com número financeiro real:

- `formatMoney(valor: string): string` — `Intl.NumberFormat("pt-BR", { style: "currency",
  currency: "BRL" })` sobre `Number(valor)` só na hora de formatar a exibição (nunca guarda
  o valor como `number` em estado — o dado continua trafegando como `string` até o último
  passo antes de virar texto na tela, mesmo princípio de `analise-arquitetural-frontend.md`
  seção 0).
- `formatPercent(valor: string): string` — mesmo princípio, usado em `percentual_medio_metas`
  e `MetaRead.percentual`.
- `formatDate(iso: string): string` — `dd/mm/aaaa`, `Intl.DateTimeFormat("pt-BR")`.
- `proximaOcorrenciaDoDia(dia: number): Date` (`utils/date.ts`) — dado um dia-do-mês
  (`Cartao.dia_fechamento`/`dia_vencimento`, `1-31`), calcula a próxima data de calendário
  em que esse dia ocorre (hoje ou próximo mês). **Isto é aritmética de calendário, não regra
  financeira** — o dado autoritativo (`dia_fechamento`) já vem pronto do backend; esta função
  só converte "dia 15" em "próxima ocorrência: 15/08/2026" para exibição, sem calcular nada
  sobre dinheiro. Usado só pelo `CartoesCard` (seção 8.5).

## 8. Layout — Bento Grid

Container `max-width: 1440px` (design-system.md, seção 8), 12 colunas, `gap: var(--space-4)`.
Ordem de leitura de cima para baixo segue a "camada de urgência decrescente" de
`central-financeira-especificacao.md` (seção 2), adaptada aos 11 endpoints reais (sem
Alertas/Insights, seção 4):

### 8.1 Cabeçalho

Saudação (`Olá, {usuario.nome}.`, já existia no placeholder) + `PeriodoSeletor`
(seção 7.3).

### 8.2 Resumo Financeiro — linha de StatCards (12 colunas, 5 células)

`ResumoFinanceiroSection` usa `useResumoFinanceiroQuery(ano, mes)`. Cinco `StatCard`
(saldo total, entradas do mês, saídas do mês, fluxo de caixa, patrimônio líquido) — a
única seção sem opção de "esconder vazia" (números sempre fazem sentido, mesmo zero, dado
que o gate de onboarding da seção 7.1 já cobre o caso de usuário totalmente novo).

### 8.3 Indicadores Gerais — faixa compacta (12 colunas, 8 `MetricCard` pequenos)

`IndicadoresStrip` usa `useIndicadoresGeraisQuery()`. Números pequenos, sem `AnimatedNumber`
grande (design-system.md, seção 16, `StatCard` é para os números "hero" — indicadores são
contagens de apoio, mesmo princípio do `--text-caption` da seção 7 do design-system para
informação de densidade menor).

### 8.4 Saldo por Conta (4 colunas) + Visão Mensal (8 colunas)

- `SaldoPorContaCard` (`useSaldoConsolidadoQuery`): lista compacta nome+saldo por conta,
  total no topo do card. Some se `contas.length === 0`.
- `VisaoMensalCard` (`useVisaoMensalQuery(ano, mes)`): comparação Entradas vs. Saídas — duas
  barras horizontais (`div` com `width` proporcional ao maior valor dos dois, cores
  `--color-positive`/`--color-negative`, seção 6.4 do design-system), sem lib de gráfico
  (seção 0.3).

### 8.5 Detalhamento por domínio — grade condicional

`ContasCard`, `CartoesCard`, `FaturasCard`, `FinanciamentosCard`, `EmprestimosCard`,
`MetasCard` — cada um 4 ou 6 colunas dependendo de quantos estão visíveis simultaneamente
(regra de esconder vazio, seção 10). `CartoesCard` é o único que usa
`proximaOcorrenciaDoDia` (seção 7.4) para mostrar "fecha em X dias"/"vence em X dias" a
partir de `dia_fechamento`/`dia_vencimento`.

### 8.6 Agenda Financeira (12 colunas, largura total)

`AgendaFinanceiraCard` (`useAgendaFinanceiraQuery(30)`): lista vertical compacta, ícone por
`origem_tipo` (mapa 1:1 `TipoEntidadeReferenciavel → lucide-react`, tabela na seção 9.2) +
data + descrição + valor. Some se `eventos.length === 0`.

### 8.7 Colapso em mobile/tablet

Segue exatamente `design-system.md` seção 24 — nada novo decidido aqui: abaixo de `md`
(768px) o Bento Grid colapsa para coluna única, na mesma ordem de prioridade visual descrita
acima (Resumo primeiro, Agenda por último). Sidebar já colapsa (ícones sem label) conforme
`Sidebar.tsx` já implementado na F2.

## 9. Componentes novos

### 9.1 `components/ui/` — genéricos, sem noção de domínio

| Componente | Responsabilidade | Notas |
|---|---|---|
| `Card` | Superfície base (`--color-surface-2`, `--radius-lg`, `--color-border-default`) — todo card de dashboard usa este por baixo | Substitui divs soltas ad-hoc; primeira peça genuinamente nova de "superfície" desde a F2 |
| `EmptyState` | Ícone + título + descrição + ação opcional, formato já especificado em design-system.md seção 20.1 | Implementação, não decisão nova de visual |
| `Skeleton` | Retângulo no formato exato do conteúdo final, shimmer sutil, respeita `prefers-reduced-motion` | design-system.md seção 20.2 |
| `StatCard` | `label` + `value` (via `AnimatedNumber`) + `TrendIndicator` opcional | design-system.md seção 16 |
| `AnimatedNumber` | Count-up spring `gentle`, uma vez por valor "novo" (motion-principles.md, seção 6.1) — nunca ao revisitar com dado em cache | Recebe `value: string` (Decimal), formata com `formatMoney`/`formatPercent` a cada frame |
| `TrendIndicator` | Seta + variação percentual, tons positive/negative | Só usado onde o backend já mandar uma variação calculada — nenhum StatCard desta etapa tem isso hoje (os 11 endpoints não expõem "variação vs. mês anterior"); componente construído e pronto, mas sem uso real ainda nesta etapa. Sinalizado para não inventar um cálculo de variação no frontend. |
| `FinancialBadge` | Badge (já existe) especializado: recebe `StatusFatura`/`StatusContratoCredito`/`StatusTransacao` e resolve `tone`+label automaticamente | Evita repetir o mapeamento enum→tone em cada card (tabela abaixo) |
| `LoadingCard` | `Card` + `Skeleton` interno, formato de um card de dashboard genérico | Usado como fallback de qualquer seção enquanto `isLoading` |
| `SectionTitle` | `--text-h2` + espaçamento padrão acima de cada bloco do Bento Grid | |
| `MetricCard` | Versão compacta do `StatCard` sem `AnimatedNumber` grande, usado nos Indicadores (seção 8.3) | |

Mapeamento `FinancialBadge` (única fonte, evita 3 `switch` diferentes espalhados):

| Enum | Valor | Tone |
|---|---|---|
| `StatusFatura` | `ABERTA` | `neutral` |
| | `FECHADA` | `warning` |
| | `PARCIALMENTE_PAGA` | `warning` |
| | `PAGA` | `positive` |
| | `ATRASADA` | `negative` |
| `StatusContratoCredito` | `ATIVO` | `neutral` |
| | `QUITADO` | `positive` |
| | `INADIMPLENTE` | `negative` |
| `StatusTransacao` | `PENDENTE` | `warning` |
| | `PAGO` | `positive` |

### 9.2 `components/domain/dashboard/` — conhecem os DTOs da Central

Um componente por seção da seção 8, cada um: chama seu hook, trata `isLoading` (→
`LoadingCard`) / `error` (→ `ErrorMessage` + retry via `refetch`) / lista vazia (→ `null`,
regra da seção 10) / sucesso (→ conteúdo real). `PeriodoSeletor` e `DashboardOnboarding`
completam a lista (seção 7.3 e 7.1 respectivamente).

Mapa `TipoEntidadeReferenciavel → lucide-react` usado por `AgendaFinanceiraCard`:

| `origem_tipo` | Ícone |
|---|---|
| `CONTA` | `Wallet` |
| `CARTAO` | `CreditCard` |
| `FATURA` | `Receipt` |
| `TRANSACAO` | `ArrowLeftRight` |
| `PARCELAMENTO` | `Layers` |
| `FINANCIAMENTO` | `Home` |
| `EMPRESTIMO` | `Banknote` |
| `CONTA_RECORRENTE` | `Repeat` |
| `META` | `Target` |

### 9.3 `DashboardOnboarding`

Tela cheia (substitui o Bento Grid inteiro quando `indicadores.contas_ativas === 0`,
seção 7.1): `EmptyState` grande, título "Comece cadastrando sua primeira conta", descrição
curta. **Sem botão de ação com link real** — a tela de CRUD de Conta ainda não existe
(Etapa F6+, fora do roteiro F1→F2→F3 atual). Mostra o texto explicativo sem CTA clicável
(ou um `Button` `disabled` com `Tooltip` "Disponível em breve") em vez de linkar para uma
rota inexistente. Revisitado quando a Etapa de CRUD de Conta acontecer.

## 10. Regra "esconder card vazio" — quem decide

`central-financeira-especificacao.md` (seção 4) descreve a regra como decisão do backend
("a API já vai retornar `null`/omitir a seção quando vazia"). Isso valia para a arquitetura
*monolítica* originalmente cogitada; a arquitetura real (seção 10 do mesmo documento,
efetivamente implementada) é **11 endpoints granulares independentes** — cada um sempre
responde 200 com sua estrutura completa, e uma lista vazia (`contas: []`) é o jeito desse
formato representar "nada aqui". Consequência direta e inevitável dessa escolha
arquitetural (já aprovada, não uma reversão): **o frontend decide não renderizar a seção
quando `lista.length === 0`** — isso continua sendo puramente apresentacional (nenhum
cálculo, nenhuma regra nova), o equivalente exato a "não desenhar uma `EmptyState` quando o
dado computado pelo backend já é vazio". Aplicado a: Saldo por Conta, Contas, Cartões,
Faturas, Financiamentos, Empréstimos, Metas, Agenda. **Não** aplicado a Resumo/Visão
Mensal/Indicadores (números sempre presentes, mesmo que zero — seção 8.2).

## 11. Motion aplicado — nada novo, só mapeamento

Toda animação desta etapa já está especificada em `docs/motion-principles.md` — nenhuma
duração/curva/spring nova é inventada:

| Evento | Padrão (motion-principles.md) |
|---|---|
| Entrada da página | fade da seção 5.10 (transição de rota já existente) |
| Entrada escalonada dos StatCards (primeira carga real) | stagger seção 9 (≤10 itens, `--duration-slow` total, `--ease-out`), nunca se repete com dado em cache |
| `AnimatedNumber` | count-up seção 6.1, `--duration-slow`, spring `gentle`, uma vez |
| Troca de período (`PeriodoSeletor`) | os StatCards afetados usam o padrão de "valor que muda depois de visível" (seção 6.2: interpolação direta + pulso de fundo `--duration-base`), não um novo count-up do zero |
| Hover de card | transição de cor/borda CSS simples, `--duration-fast` |
| Skeleton → conteúdo | crossfade `--duration-base` (seção 5.3) |
| `FinancialBadge` mudando (não aplicável nesta etapa — sem ação de escrita) | N/A, reservado para quando uma ação do usuário mudar um status em tela (F6+) |
| Card entrando/saindo por causa da regra da seção 10 | mount/unmount padrão seção 5.1 (fade + 4-8px), nunca instantâneo |

## 12. Rota `/dev` — laboratório visual

Rota permanente `/dev`, dentro de `ProtectedRoute` + `AppLayout` (mesma proteção do resto do
app — é uma ferramenta interna, não uma vitrine pública; não teria sentido expor dado/UI do
sistema sem login). **Não aparece no `Sidebar`** (`NAV_ITEMS`) — acessada só digitando a URL,
para não confundir a navegação real do app com uma página de desenvolvimento. Conteúdo:
cada componente novo desta etapa (seção 9.1) demonstrado com dado fixo (fixtures locais no
próprio arquivo, no formato exato dos schemas da seção 3 — nunca uma chamada real à API,
para a página funcionar sempre, independente do estado real do banco), cobrindo os estados
pedidos: loading (`Skeleton`/`LoadingCard`), erro (`ErrorMessage` com botão de retry
decorativo), vazio (`EmptyState`), sucesso (dado fixo preenchido), todas as `tone`s de
`Badge`/`FinancialBadge`, `AnimatedNumber` com um botão para disparar a contagem de novo
(útil para inspecionar a animação sem esperar uma sessão nova). Página organizada em seções
com `SectionTitle`, uma por componente. **Convenção daqui pra frente**: todo componente novo
de qualquer etapa futura ganha uma seção aqui no mesmo commit que o introduz — o pedido
original já registra isso ("sempre que um componente novo nascer... deverá aparecer nessa
página").

## 13. Estados — cobertura por seção

Reafirmando o vocabulário já definido (`analise-arquitetural-frontend.md` seção 9,
design-system.md seção 20.3), aplicado especificamente às 10 seções de domínio (a 11ª,
Indicadores, segue o mesmo padrão):

- **loading** → `LoadingCard` (skeleton no formato do card real, nunca um `Spinner`
  central genérico competindo com o skeleton).
- **erro** → `ErrorMessage` dentro do `Card` (não a página inteira) + botão "Tentar
  novamente" chamando `refetch()` — um card com erro nunca derruba os outros 10.
- **vazio** → seção 10 (não renderiza) para as 8 seções de lista; N/A para
  Resumo/Visão Mensal/Indicadores.
- **sucesso** → conteúdo real, com a entrada animada da seção 11 só na primeira carga.
- **atualização** (usuário troca o período) → seção 11, pulso em vez de recontagem.
- **retry** → mesmo botão do estado de erro; `refetch()` do React Query, sem lógica manual.

## 14. Responsividade

Sem decisão nova — aplicação direta de `design-system.md` seção 24 (breakpoints
`sm`/`md`/`lg`/`xl` já definidos) e seção 8 (bento grid colapsa para coluna única abaixo de
`md`, mesma ordem de prioridade da seção 8 deste documento).

## 15. Performance

- `React.memo` só nos componentes de `components/domain/dashboard/` que recebem props
  estáveis e podem re-renderizar sem necessidade quando o período muda em outro card
  irmão (ex. `CartoesCard` não depende de `ano`/`mes`, não deveria re-renderizar quando
  `PeriodoSeletor` muda) — aplicado depois de confirmar que há re-render desnecessário de
  verdade (React DevTools Profiler), não especulativamente em todos os 13 componentes.
- Nenhuma seção busca dado de outra — sem waterfall de queries (seção 7.2), que já é a
  maior alavanca de performance percebida aqui.
- `AnimatedNumber` anima só `transform`/opacity-equivalentes (o próprio valor numérico via
  `useSpring`/`useTransform` do `motion`, não uma propriedade de layout) — motion-principles.md
  seção 9.

## 16. Critério de pronto

Backend inalterado (conferido, não é objetivo desta etapa mudar nada nele). Dashboard real
consumindo os 11 endpoints, com todas as seções da seção 8 renderizando corretamente com
dado real da conta de teste. Rota `/dev` funcionando e cobrindo os componentes da seção
9.1. `npm run build` e `tsc -b` limpos. Testado manualmente no navegador (não só
build/typecheck) antes de considerar a etapa concluída — pedido explícito. `README.md`
atualizado e `docs/revisao-tecnica-dashboard.md` escrito ao final, mesmo padrão de toda
etapa anterior do projeto.

## 16.1 Diretriz adicional aprovada — crescer sem refatoração

Registrada aqui como princípio explícito, não só uma consequência implícita da seção 5/6/9
(que já apontavam nessa direção, mas agora isso é regra, não coincidência de design):

- **Cada seção do Bento Grid é um componente independente e reutilizável** —
  `ResumoFinanceiroSection`, `ContasCard`, `CartoesCard`, `FaturasCard`, `MetasCard`,
  `AgendaFinanceiraCard`, `IndicadoresStrip`, `VisaoMensalCard` (seção 9.2) nunca dependem
  uns dos outros nem compartilham estado local entre si (só o período, seção 7.3, passado
  por prop de cima). Adicionar uma seção nova no futuro (ex. quando Alertas/Insights
  ganharem endpoint) significa criar um componente novo + um hook novo — nenhum componente
  existente é tocado.
- **`DashboardPage.tsx` só orquestra.** Monta o layout (grid, breakpoints, ordem das
  seções, o gate de onboarding da seção 7.1) e compõe os widgets — nunca chama
  `httpClient`/`centralFinanceiraService` diretamente, nunca guarda estado de
  loading/erro/dado de nenhuma seção. Se um dia esse arquivo crescer a ponto de parecer
  complexo, o sintoma correto a corrigir é extrair mais um componente de seção, não
  adicionar lógica ali.
- **Toda busca de dado mora em `hooks/useCentralFinanceiraQueries.ts`.** Nomeação alinhada
  ao pedido: `useResumoFinanceiroQuery`, `useAgendaFinanceiraQuery`,
  `useIndicadoresGeraisQuery`, etc. (sufixo `Query` mantido para não colidir com o nome do
  hook React `use...` genérico e para ficar consistente com o restante do projeto, que já
  nomeia assim — `useContasQuery` é o exemplo dado em `analise-arquitetural-frontend.md`
  seção 9). Cada componente de seção (`components/domain/dashboard/`) chama exatamente um
  desses hooks e é, por construção, puro de apresentação: recebe o resultado
  (`data`/`isLoading`/`error`/`refetch`) e decide só o que renderizar (seção 13) — nenhuma
  seção faz fetch por conta própria fora desse hook.

## 17. Próximos passos

Aguardando sua validação deste documento antes de qualquer código, mesma convenção de
sempre. Ordem de implementação sugerida uma vez aprovado:

1. `utils/format.ts` + `utils/date.ts` (seção 7.4) — infraestrutura sem dependência de UI.
2. `types/centralFinanceira.ts` + `services/centralFinanceiraService.ts` + `queryKeys.ts`
   (seção `dashboard`) + `hooks/useCentralFinanceiraQueries.ts` (seção 6).
3. `components/ui/` novos (seção 9.1): `Card` primeiro (todo o resto depende dele), depois
   `Skeleton`/`EmptyState`/`LoadingCard`/`SectionTitle`/`MetricCard`/`FinancialBadge`/
   `TrendIndicator`/`AnimatedNumber`/`StatCard`, nessa ordem de dependência crescente.
4. `components/domain/dashboard/` (seção 9.2), um por vez, cada um já plugado no hook real.
5. `pages/dashboard/DashboardPage.tsx` — monta o Bento Grid (seção 8) com o gate de
   onboarding (seção 7.1).
6. `pages/dev/DevPage.tsx` + rota `/dev` (seção 12).
7. Validação manual no navegador + `tsc -b` + `npm run build` + README +
   `docs/revisao-tecnica-dashboard.md` (seção 16).
