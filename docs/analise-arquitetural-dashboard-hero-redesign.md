# Redesign do Dashboard — hero cards, gauge e listas combinadas

## Pedido do usuário

Uma referência visual (print de outro app) mostrando: cabeçalho com seletor de mês +
saudação, uma linha de 3 cards de destaque ("Saldo Total" com uma linha de tendência,
"Visão Mensal" com entradas/saídas e um mini gráfico, "Metas Ativas" com um anel de
progresso circular), e abaixo duas colunas — "Contas e Cartões" (lista compacta
mesclando os dois) e "Transações Recentes" (tabela com abas Transações/Agenda) — além
de um destaque "Financiamento Principal". Pedido explícito: **manter a identidade
visual já existente** — o print é só inspiração de composição/densidade, não um layout
para clonar pixel a pixel.

## Levantamento (o que já existia)

- Nenhuma biblioteca de gráfico está instalada (`recharts`/`chart.js`/`d3` — nenhuma).
  `docs/analise-arquitetural-dashboard.md`, seção 0.3, já registrava essa decisão como
  **deliberadamente adiada** — "quando fizer sentido escolher a lib com calma". Esta
  etapa é esse momento, mas a escolha feita foi **não adicionar dependência nenhuma**:
  os elementos gráficos pedidos (linha de tendência, anel de progresso) são simples o
  bastante para SVG cru, seguindo o mesmo espírito de `ProgressBar.tsx` (construído do
  zero, sem lib, com os tokens do Design System).
- Não existe nenhum endpoint de série histórica (saldo dia a dia, fluxo de caixa diário
  etc.) — `resumo`/`visao-mensal` são sempre uma FOTO do período (um `ano`+`mes`), nunca
  uma linha do tempo. **Nenhum endpoint novo foi criado** para isto (ver decisão
  abaixo) — a "linha de tendência" do Saldo Total é derivada de dois números REAIS já
  disponíveis (início e fim do período), nunca uma série diária fabricada.
- Não existia componente de progresso circular (`ProgressBar` é só linear) nem `Tabs`.
  Os dois foram criados do zero, seguindo os mesmos tokens (`tone` idêntico ao de
  `ProgressBar`, animação `SPRING.gentle` de `lib/motion.ts`).
- `MetasCard.tsx` já calculava "meta mais perto de concluir" (`percentual < 100`,
  ordenada desc, primeira) — a mesma lógica foi reaproveitada para escolher qual meta
  aparece no gauge do hero, sem duplicar a fórmula.
- `lib/dashboardLayout.ts::carregarLayoutDashboard` já tolera ids desconhecidos/ausentes
  (filtra o que não existe mais, acrescenta o que é novo no fim) — trocar
  `contas`+`cartoes` por um único `contas_cartoes` não precisou de nenhuma migração
  manual de `localStorage`.

## Decisões

### 1. Sem gráfico "de verdade" fabricado — tendência derivada, não inventada

"Saldo Total" ganha uma mini-linha de tendência (2 pontos: saldo no início do período →
saldo agora) e um `trend` percentual (já suportado por `StatCard`/`TrendIndicator`,
existente mas nunca usado até agora por falta de dado). Os dois são calculados 100% a
partir de campos que `ResumoFinanceiroRead` já devolve:

```
saldo_inicio_periodo = saldo_total - fluxo_caixa_mes
trend_percentual = fluxo_caixa_mes / saldo_inicio_periodo * 100   (se saldo_inicio_periodo != 0)
```

Nenhuma linha diária é desenhada — a mini-linha é literalmente um segmento entre dois
pontos reais, rotulada "desde o início do período" para nunca insinuar granularidade
que não existe. Se um endpoint de série histórica fizer sentido no futuro (ex. saldo
dia a dia para um gráfico de verdade), fica registrado aqui como próximo passo natural,
fora do escopo desta etapa.

### 2. "Visão Mensal" continua sem duplicar `resumo` (mesma diretriz de antes)

O antigo `VisaoMensalCard` já tinha sido fundido em `ResumoFinanceiroSection` por
duplicar `entradas_mes`/`saidas_mes`/`fluxo_caixa_mes` com outro endpoint
(`visao-mensal`) que devolve os mesmos três números. Essa fusão continua — "Visão
Mensal" no hero novo é o MESMO StatCard de fluxo de caixa de antes, só restilizado (as
duas barras proporcionais viram uma versão maior/mais polida, ainda sem nenhuma lib).

### 3. "Metas Ativas" no hero é uma meta só (a mais perto de concluir), não a média

Espelha a composição do print (uma meta específica com nome + anel), não um agregado.
Reaproveita a mesma seleção de `MetasCard` (`percentual < 100`, desc, primeira). Sem
meta ativa incompleta, o card retorna `null` (regra já estabelecida: "esconder card
vazio" — `docs/analise-arquitetural-dashboard.md`, seção 10) — a linha de hero cai para
2 cards nesse caso, sem placeholder vazio.

`MetasCard` (lista completa no Bento Grid) continua existindo, sem redundância: o hero
é "uma olhada rápida numa meta", o Bento card é "visão agregada de todas".

### 4. "Contas e Cartões" combinado substitui `ContasCard` + `CartoesCard`

Um card novo (`ContasCartoesCard.tsx`) lista as contas de maior saldo e os cartões com
mais limite disponível numa lista só (mesmo padrão visual de linha compacta usado em
`AgendaFinanceiraCard`/`ContaResumoCard` da página `/contas`), cada linha navegando para
seu destino (`/contas` ou `/cartoes/:id`). Reaproveita `useContasQuery`/`useCartoesQuery`
já existentes — nenhum endpoint novo.

**Perda deliberada, sem duplicar**: a versão antiga de `CartoesCard` mostrava utilização
geral + próximos vencimentos de fatura. Vencimento de fatura já é coberto por
`FaturasCard` (que continua no Bento Grid, mostrando só faturas vencidas/a vencer em 10
dias) — não é uma funcionalidade perdida, só deixou de estar duplicada em dois lugares.

### 5. "Transações Recentes" com abas Transações/Agenda substitui `AgendaFinanceiraCard`

Card novo (`TransacoesRecentesCard.tsx`) com um `Tabs` novo alternando entre
`useAtividadesRecentesQuery(6)` (mesma fonte da Central de Atividades, já existente,
aberta hoje só via Drawer no Header) e `useAgendaFinanceiraQuery(30)` (a mesma da antiga
`AgendaFinanceiraCard`, fatiada nas 6 primeiras). "Ver mais" navega para `/transacoes`
(aba Transações) ou `/calendario` (aba Agenda). O card só retorna `null` quando AS DUAS
abas estão vazias — se só uma tem conteúdo, o card continua visível para o usuário poder
trocar de aba.

### 6. "Financiamento Principal" — destaque dentro de `FinanciamentosCard`, não um card novo

Em vez de criar um card dedicado (que duplicaria `FinanciamentosCard`), o financiamento
com a parcela mais próxima do vencimento (`proxima_parcela_data` mais cedo) ganha
destaque no topo do card existente — nome do bem financiado, próxima parcela, "N/M
parcelas" e um `Gauge` com o progresso. Os demais financiamentos (se houver mais de um)
continuam listados abaixo, como já era.

### 7. `ContasCartoesCard`/`TransacoesRecentesCard` saem da personalização

`lib/dashboardLayout.ts` — `DashboardCardId` perde `"contas"`/`"cartoes"` (viram
`ContasCartoesCard`, uma linha FIXA de destaque logo abaixo do hero, junto de
`TransacoesRecentesCard`), sem nenhum id novo no lugar: os dois passam a ter o mesmo
nível de destaque do print de referência (não fazia sentido continuar
escondível/reordenável junto dos cards secundários do Bento Grid). `carregarLayoutDashboard`
já ignora ids desconhecidos sem erro (comportamento pré-existente, não alterado) —
usuários com um layout salvo antigo (`ordem`/`ocultos` contendo `"contas"`/`"cartoes"`)
simplesmente os perdem da lista de personalização, sem quebrar nada.

### 8. Layout final da página

```
header (saudação + PeriodoSeletor + Personalizar)
hero row: Saldo Total | Visão Mensal | Metas Ativas   (substitui ResumoFinanceiroSection antigo)
ProximoPassoCard (inalterado)
IndicadoresStrip (inalterado — não pedido para remover)
HojeCard (inalterado)
2 colunas: Contas e Cartões | Transações Recentes      (novo, reflete o print)
Bento Grid personalizável: Faturas | Financiamentos | Empréstimos | Metas
DashboardCustomizeDrawer (inalterado, só com a lista de ids atualizada)
```

Nenhum componente existente foi removido sem substituição equivalente — a única perda
real de informação foi a "utilização geral do limite" (estava só em `CartoesCard`, que
deixou de existir); se fizer falta, pode voltar como uma métrica dentro do
`ContasCartoesCard` numa etapa futura.
