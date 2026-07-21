# Revisão técnica — Dashboard (Etapa F3)

Revisão final da etapa, mesmo padrão de toda revisão técnica anterior do projeto (backend
e F1/F2 do frontend). Escopo: Dashboard real consumindo os 11 endpoints de
`/central-financeira/*`, rota `/dev`, seguindo `docs/analise-arquitetural-dashboard.md`
(aprovado antes da implementação, com uma diretriz adicional aprovada nesta conversa —
seção 16.1 do documento: cada seção do Bento Grid é um componente independente, busca de
dado só nos hooks, `DashboardPage` só orquestra).

## 1. O que foi entregue

**Camada de dados** (`docs/analise-arquitetural-dashboard.md`, seção 6):
`types/centralFinanceira.ts` (espelha os 11 schemas de saída do backend 1:1, conferido por
leitura direta de `app/schemas/central_financeira.py` e das entidades reaproveitadas —
não da especificação de produto original), `services/centralFinanceiraService.ts` (11
funções finas), seção `dashboard` de `api/queryKeys.ts`, `hooks/useCentralFinanceiraQueries.ts`
(11 `useQuery`, um por endpoint, zero `useMutation` — a Central é 100% leitura).

**Infraestrutura nova**: `utils/format.ts` (`formatMoney`, `formatPercent`, `toNumber`) e
`utils/date.ts` (`formatDate`, `nomeMes`, `proximaOcorrenciaDoDia`, `diasAte`) — nenhuma
etapa anterior precisava formatar dinheiro real.

**Dez componentes genéricos** em `components/ui/`: `Card`, `Skeleton` (com shimmer via
`.skeleton-shimmer` novo em `index.css`, respeitando `prefers-reduced-motion`),
`EmptyState`, `LoadingCard`, `SectionTitle`, `MetricCard`, `FinancialBadge` (mapeia
`StatusFatura`/`StatusContratoCredito`/`StatusTransacao` → tone/label do `Badge` já
existente, tabela única em vez de três `switch` espalhados), `TrendIndicator`,
`AnimatedNumber` (count-up spring `gentle` via `useSpring`/`useTransform` do `motion`,
formata a cada frame, pula a animação sob `prefers-reduced-motion` via `useReducedMotion`
— o único componente do projeto que precisa checar isso manualmente, porque roda fora do
sistema declarativo que `MotionConfig` cobre), `StatCard`.

**Treze componentes de seção** em `components/domain/dashboard/`: `PeriodoSeletor`,
`DashboardOnboarding`, `ResumoFinanceiroSection`, `SaldoPorContaCard`, `ContasCard`,
`CartoesCard`, `FaturasCard`, `FinanciamentosCard`, `EmprestimosCard`, `MetasCard`,
`AgendaFinanceiraCard`, `VisaoMensalCard`, `IndicadoresStrip` — cada um chama exatamente um
hook, decide loading/erro/vazio/sucesso, e é usado por `DashboardPage.tsx` sem que a página
saiba nada sobre `httpClient`/serviços.

**`DashboardPage.tsx`**: reescrita completa, orquestra o Bento Grid (header com saudação +
`PeriodoSeletor`, `ResumoFinanceiroSection`, `IndicadoresStrip`, `SaldoPorContaCard` +
`VisaoMensalCard` lado a lado, grade de `ContasCard`/`CartoesCard`/`FaturasCard`/
`FinanciamentosCard`/`EmprestimosCard`/`MetasCard`, `AgendaFinanceiraCard` em largura
total), com gate de onboarding: `indicadores.contas_ativas === 0` mostra
`DashboardOnboarding` em vez do grid. Estado de período (`ano`/`mes`) vive só aqui,
compartilhado por prop com as duas seções que precisam dele.

**Rota `/dev`** (`pages/dev/DevPage.tsx`): protegida (mesma `ProtectedRoute` do resto do
app), fora do `Sidebar`. Demonstra os dez componentes de `components/ui/` com dado fixo —
todas as variações de `StatCard`/`AnimatedNumber`/`TrendIndicator`, `FinancialBadge` para
os 10 valores de enum cobertos (`StatusFatura` × 5, `StatusContratoCredito` × 3,
`StatusTransacao` × 2), `Badge` com os 5 tones brutos, `MetricCard`, `SectionTitle` com e
sem ação, `Skeleton`, `LoadingCard`, `EmptyState` com e sem ação, um estado de erro
decorativo com botão de retry.

## 2. Decisões que divergiram do previsto — e por quê

Todas já sinalizadas em `docs/analise-arquitetural-dashboard.md` antes da implementação
começar, não descobertas depois:

- **Alertas/Insights/Parcelamentos não existem no Dashboard.** A especificação de produto
  original (`docs/central-financeira-especificacao.md`) os previa; o backend real
  (`app/api/routes/central_financeira.py`, docstring "11 endpoints agregadores") nunca os
  implementou. Conferido por leitura direta do router antes de escrever qualquer
  componente — evitou construir uma seção para um endpoint que não existe.
- **Sem gráfico de biblioteca.** `docs/design-system.md` (seção 16) já adiava essa escolha
  para esta etapa; em vez de escolher uma lib no meio da implementação, "Visão Mensal" usa
  uma comparação Entradas vs. Saídas com duas barras de `div` estilizado — zero dependência
  nova. Gráficos de verdade (evolução de financiamento, fluxo de caixa histórico) ficam
  para quando a lib for escolhida com calma.
- **`resumo` × `visao-mensal` não são fetch duplicado.** Os dois endpoints devolvem
  entradas/saídas/fluxo de caixa do mesmo período por desenho do backend (dois agregadores
  distintos) — `resumo` alimenta os `StatCard`s do topo, `visao-mensal` alimenta a
  comparação visual; cada um com seu próprio hook/query, sem chamada manual compartilhada.
- **`proximaOcorrenciaDoDia`/`diasAte` no frontend.** `Cartao.dia_fechamento`/
  `dia_vencimento` são inteiros (dia do mês), não datas — converter isso em "fecha em X
  dias" é aritmética de calendário pura, não regra financeira; o dado autoritativo
  (`dia_fechamento`) já vem do backend sem alteração.
- **Renumeração de etapa** (F3 = Dashboard, não Formulários) — decisão explícita do
  usuário nesta conversa, registrada em `docs/analise-arquitetural-dashboard.md` seção 0.1
  e no README; `docs/analise-arquitetural-frontend.md` seção 16 não foi editada (só
  sinalizada como desatualizada), por não ser um conflito arquitetural real — é só ordem de
  execução.

## 3. Diretriz "crescer sem refatoração" — como foi cumprida

Pedido explícito do usuário antes da implementação começar (`docs/analise-arquitetural-dashboard.md`,
seção 16.1):

- Nenhum componente de `components/domain/dashboard/` importa outro componente de seção,
  nem lê estado de outro — o único dado compartilhado é `ano`/`mes`, passado por prop de
  `DashboardPage` para as duas seções que precisam dele (`ResumoFinanceiroSection`,
  `VisaoMensalCard`).
- `DashboardPage.tsx` não importa `httpClient`, `centralFinanceiraService` nem nenhum hook
  de mutation/query além de `useIndicadoresGeraisQuery` (usado só para o gate de
  onboarding, mesma `queryKey` de `IndicadoresStrip` — o React Query deduplica, sem
  requisição extra). Todo o resto do dado vem de dentro de cada seção.
- Cada hook de `useCentralFinanceiraQueries.ts` é uma função isolada — adicionar uma seção
  nova no futuro (ex. quando Alertas ganhar endpoint) é: um hook novo + um componente novo
  em `components/domain/dashboard/` + uma linha em `DashboardPage.tsx`. Nenhum arquivo
  existente precisa ser reestruturado.

## 4. Validação realizada

- **`tsc -b`** (build incremental do projeto inteiro, com project references) — limpo, sem
  erros, após cada lote de arquivos novos (verificado incrementalmente, não só no final).
- **`vite build`** — limpo (`2396 módulos transformados`, bundle de produção gerado; único
  aviso é o tamanho do chunk principal, 502KB minificado — esperado dado `motion` + React
  Query + toda a árvore do app num único bundle ainda sem code-splitting, não um erro).
- **Sessão real contra o backend**: banco temporário isolado, migrations aplicadas do
  zero, `POST /auth/registrar` + `/auth/login` reais, os 11 endpoints de
  `/central-financeira/*` chamados com o token real. Confirmado: `contas_ativas: 0` antes
  de qualquer conta existir (gatilho correto do `DashboardOnboarding`); após
  `POST /contas`, `contas_ativas: 1` e `resumo`/`saldo-consolidado`/`contas`/`indicadores`
  todos refletindo o novo saldo. Toda resposta JSON comparada campo a campo contra
  `types/centralFinanceira.ts` — nenhuma divergência de nome/formato encontrada.
- **Validação visual no navegador**: pendente de confirmação do usuário — recomendado
  `npm run dev:full` na raiz do projeto e abrir `http://localhost:5173`, navegar pelo
  Dashboard e por `/dev`. Esta revisão cobre tudo que é verificável sem olhos humanos
  (tipos, build, contrato real de API); o critério de pronto do documento de arquitetura
  (seção 16) também exige essa confirmação visual antes de encerrar a etapa por completo.

## 5. Riscos conhecidos / dívida técnica sinalizada, não corrigida agora

- **Bundle de produção sem code-splitting** (502KB minificado) — aviso do próprio Vite, não
  um bug. Candidato natural para `React.lazy`/`import()` quando o app crescer mais (F4+),
  não urgente para um app de usuário único hoje.
- **`TrendIndicator` sem uso real** — nenhum dos 11 endpoints expõe variação percentual
  hoje; o componente existe pronto (seção 9.1 do doc de arquitetura já sinalizava isso
  explicitamente, não é uma surpresa).
- **`types/centralFinanceira.ts` duplica campos que pertencerão a `types/<entidade>.ts`**
  quando o CRUD de cada entidade chegar (F6+) — sinalizado no próprio doc de arquitetura
  (seção 6.1) como revisão futura, não uma dívida silenciosa.

## 6. Conclusão

Etapa F3 implementada seguindo `docs/analise-arquitetural-dashboard.md` sem nenhuma
alteração de contrato/endpoint/regra de negócio do backend. Todas as divergências entre a
especificação de produto original e o que o backend realmente expõe foram sinalizadas antes
da implementação (documento de arquitetura, seção 0/4), não descobertas como bug depois.
Build e typecheck limpos, contrato de API validado byte a byte contra uma sessão real.
Falta apenas a confirmação visual do usuário no navegador para considerar a etapa
inteiramente encerrada, conforme o próprio critério de pronto pedido.
