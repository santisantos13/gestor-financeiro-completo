# Análise arquitetural — Gráficos

## 1. Escopo

Pedido do usuário: "vamos partir pro crud de gráficos" (a feature já existia na tabela de
funcionalidades do painel de acompanhamento como "Gráficos", pendente, 5%). Não é um CRUD de
verdade — gráfico não é uma entidade que se cria/edita/apaga, é uma VISUALIZAÇÃO somente-leitura
sobre dado que já existe, seguindo exatamente o mesmo espírito da Central Financeira
(`docs/analise-arquitetural-central-financeira.md`): "camada de agregação, nunca duplica regra de
negócio de outro Service".

Perguntado ao usuário onde os gráficos deveriam morar e quais entram nesta etapa
(`AskUserQuestion`), a resposta foi: **as duas coisas** (um resumo leve no Dashboard + uma página
`/graficos` completa) e **todos os 4 propostos, mais "o que mais eu achar válido"**:

1. Evolução do saldo (linha, últimos N meses)
2. Entradas × Saídas por mês (barras, últimos N meses)
3. Gastos por categoria (donut, mês selecionado)
4. Gastos por cartão (barras horizontais, mês selecionado)
5. **Extra escolhido**: Distribuição do saldo atual por conta (donut) — não pedido explicitamente
   por nome, mas *zero custo de backend* (reaproveita 100% `saldo-consolidado`, já teria os dados
   na tela) e fecha visualmente o quadro "de onde vem e para onde vai o patrimônio" sem inventar
   nenhuma agregação nova. Critério de escolha do 5º item: só entrou o que já existe pronto —
   qualquer coisa que exigisse endpoint novo ficou de fora desta rodada (ver seção 6, backlog).

## 2. Onde reaproveita dado existente vs. o que é novo

Regra do arquivo `central_financeira_service.py` (cabeçalho, regras 1-3): nunca acessar um
Repository direto, nunca duplicar cálculo de outro Service, toda soma feita ali é sobre resultado
já agregado (nunca somar linha por linha de `Transacao` em Python). Os 5 gráficos, sob essa régua:

| Gráfico | Fonte | Novo? |
|---|---|---|
| Distribuição do saldo por conta | `GET /central-financeira/saldo-consolidado` (`contas[]`) | Nada novo — só render |
| Entradas × Saídas por mês | `TransacaoService.somar_por_periodo` já existe, mas só para 1 mês por chamada | Novo: versão agrupada por mês (evita N chamadas) |
| Evolução do saldo | Não existe hoje nenhuma "foto histórica" de saldo (só o `saldo_atual` corrente) | Novo: derivado de `saldo_inicial` (constante) + a MESMA fórmula líquida que `ContaRepository.somar_transacoes_pagas` já usa por conta, só que agregada por mês para todas as contas juntas |
| Gastos por categoria | Não existe agregação por categoria hoje | Novo: `GROUP BY categoria_id` |
| Gastos por cartão | Não existe agregação por cartão (existe `limite_utilizado`, mas é sobre o ciclo aberto atual, não sobre um período arbitrário) | Novo: `GROUP BY cartao_id`, deliberadamente distinto de "limite usado" |

### 2.1 Evolução do saldo — por que não itera conta por conta

`ContaRepository.somar_transacoes_pagas(conta_id)` soma `RECEITA - DESPESA` de `Transacao` PAGA,
não-importada, **daquela conta**. `Transferencia` move dinheiro entre DUAS contas do mesmo
usuário (nunca para fora) — então o efeito líquido de qualquer transferência sobre o **total**
somado de todas as contas é sempre zero (o que sai de uma entra na outra, inclusive quando o
destino é o cofrinho oculto de uma Meta). Consequência: para a série histórica do saldo TOTAL
(não por conta), a Transferencia pode ser ignorada por completo — só precisamos de:

```
saldo_total(mês M) = Σ(conta.saldo_inicial) + Σ(Transacao.valor com sinal, PAGO, não-importada,
                                                 conta_id preenchido [nunca cartão], data ≤ fim de M)
```

Isso vira UMA query agregada (`GROUP BY ano, mês`, com `CASE WHEN tipo=RECEITA THEN valor ELSE
-valor END`) que devolve o líquido de cada mês com atividade — bem mais barato que iterar
conta-por-conta (que seria `nº de contas × nº de meses` queries). A soma acumulada (prefixo) sobre
essas poucas dezenas de linhas já agregadas é feita em Python — isso NÃO viola a regra 3 do
cabeçalho (que proíbe somar `Transacao` crua em Python): aqui é um prefix-sum sobre um resultado
que já é um `SUM` do banco, o mesmo princípio de `resumo_financeiro` somando `entradas_mes -
saidas_mes` (dois `SUM` já prontos).

**Limitação aceita, documentada, não implementada**: a fórmula assume que toda conta ativa hoje
"sempre existiu" com o `saldo_inicial` atual. Não existe no modelo um campo "data de abertura da
conta" distinto de `criado_em` (timestamp de auditoria) — se o usuário criar uma conta nova hoje
com saldo inicial de R$ 1.000, um mês de 6 meses atrás no gráfico vai incluir esse R$ 1.000 no
total (mesmo a conta não existindo naquela época). Corrigir isso exigiria um campo de negócio novo
(ex. `Conta.data_abertura`) — fora do pedido do usuário, não implementado agora. Fica registrado
como gap conhecido, mesmo padrão de outras limitações já aceitas neste projeto (ex. recorrências
futuras não geradas em `HojeCard`).

### 2.2 Gastos por categoria / por cartão — escopo do período

Usam exatamente o mesmo filtro que `_somar_periodo` (chamado por `resumo_financeiro`/
`visao_mensal` hoje): `status=PAGO`, sem excluir compra de cartão (`apenas_conta` não se aplica) —
os números precisam bater com o que "Visão mensal" já mostra. "Gastos por cartão" filtra
adicionalmente `cartao_id IS NOT NULL` (por definição). Categoria sem `categoria_id` (transação
sem categorização) vira um item "Sem categoria" — nunca omitido silenciosamente.

## 3. Endpoints novos (2, não 4 — mesmo espírito de `/calendario` agrupar fechamento+vencimento)

```
GET /central-financeira/graficos/tendencias?meses=12
GET /central-financeira/graficos/periodo?ano=&mes=
```

`tendencias` cobre os 2 gráficos de série temporal (evolução do saldo + entradas×saídas) num só
payload — os dois compartilham a mesma janela "últimos N meses", então uma chamada só evita dois
round-trips redundantes. `periodo` cobre os 2 gráficos escopados a UM mês (categoria + cartão),
no mesmo padrão `ano`/`mes` já usado por `/resumo`, `/visao-mensal`, `/calendario`.

```python
# Novo em TransacaoRepository (SUM agrupado, cross-DB via sqlalchemy.extract —
# nunca strftime, que é SQLite-only e quebraria em Postgres/produção):
def somar_liquido_por_mes(usuario_id, *, data_fim) -> Sequence[Row]          # ano, mes, liquido
def somar_por_mes(usuario_id, *, tipo, status, data_inicio, data_fim) -> Sequence[Row]  # ano, mes, total
def somar_agrupado_por_categoria(usuario_id, *, tipo, status, data_inicio, data_fim) -> Sequence[Row]  # categoria_id, total
def somar_agrupado_por_cartao(usuario_id, *, status, data_inicio, data_fim) -> Sequence[Row]  # cartao_id, total

# Espelhados 1:1 em TransacaoService (mesmo padrão de somar_por_periodo)
```

`CentralFinanceiraService` ganha `categoria_service` como dependência nova (só usado aqui, para
resolver nome/cor/ícone da categoria) — mesmo padrão aditivo de `conta_recorrente_service`
(parâmetro opcional no fim do construtor, default `None`, não reordena posicionais de teste
existentes).

## 4. Biblioteca de gráfico — decisão adiada desde a Etapa F5, resolvida agora

**Recharts** (React + SVG, componível, tema via `props` em vez de CSS global — encaixa bem com os
tokens de `--color-chart-*`/`--color-positive`/etc. já definidos). Motivo da escolha: é a lib mais
madura para React puro (sem wrapper de canvas pesado), curva de aprendizado baixa, e os tipos de
gráfico pedidos (linha, barra, donut) são todos de primeira classe na API dela. Instalada como
dependência nova do frontend (não havia nenhuma lib de gráfico no projeto até agora).

## 5. Design (design-system.md, seção 19 — já documentada, só aplicada agora)

- Paleta: `--color-positive`/`--color-negative` para entradas×saídas (polaridade financeira real);
  `--color-chart-1..6` para categoria/cartão/conta (sem polaridade, só distinção categórica);
  evolução do saldo usa `--color-accent` (série única, mesmo critério já documentado na seção 6.3:
  "série principal de gráfico").
- Sem grid de fundo pesado — só linhas-guia horizontais sutis (`--color-border-subtle`).
- Eixos em `--text-caption`/`--color-text-tertiary`.
- Tooltip: `--color-surface-4` + `--shadow-md` + `--radius-md`, valor em Geist Mono (`.tabular`).
- Entrada animada (draw-in) uma vez só na montagem, nunca ao trocar de aba com dado em cache.
- Toda cor tem legenda com texto (nunca só cor) — seção 23 (acessibilidade).

## 6. Onde aparece

- **Dashboard**: novo card `EvolucaoSaldoCard` (mini-linha dos últimos 6 meses, mesmo grid
  personalizável do Bento Grid — entra em `dashboardLayout.ts`/`COMPONENTE_POR_CARD`, mostrar/
  ocultar/reordenar de graça).
- **Nova página `/graficos`**: os 5 gráficos completos, com dois seletores independentes —
  "últimos N meses" (6/12/24, para os 2 de tendência) e `PeriodoSeletor` de um mês só (para
  categoria/cartão, reaproveitando o componente já existente). Novo item de navegação no
  `Sidebar`/`MobileNav` (`navItems.ts`), ícone `BarChart3`.

## 7. Backlog explicitamente fora desta etapa

- Exportação de gráfico como imagem/PDF.
- Comparação ano-a-ano (ex. Janeiro/2026 vs Janeiro/2025).
- Gráfico de progresso de metas ao longo do tempo (métricas de meta já existem, mas não uma série
  histórica — exigiria decisão de "snapshot" que não foi pedida).
- Filtro de categoria/cartão específico dentro do próprio gráfico (drill-down) — os 2 endpoints
  novos devolvem a distribuição completa do período, sem filtro adicional client-side além do que
  o próprio Recharts já oferece (hover/legenda).

## 8. "Gastos por conta" — 6º gráfico, pedido em cima da etapa já em produção (2026-07-25)

Pedido do usuário: "pode ter uma espécie de gastos por conta, em formato de círculo também, porém
relacionados a conta usada" — irmão direto de "Gastos por cartão" (seção 3), mas agrupando por
`Conta` em vez de `Cartão`, e em donut (como "Gastos por categoria") em vez de barras.

**Não confundir com "Distribuição do saldo atual por conta"** (o 5º gráfico, seção 6): aquele é o
*saldo hoje* de cada conta (`SaldoConsolidadoRead`, foto do momento); este é o *quanto foi gasto
diretamente daquela conta durante o mês selecionado* (mesma janela `ano`/`mes` de "Gastos por
categoria"/"por cartão"). São dois recortes diferentes do mesmo substantivo "conta" — o nome dos
dois cards na página deixa isso explícito.

**Backend** — mesmo padrão de `somar_agrupado_por_cartao`/`GastoPorCartao`, sem nenhum endpoint
novo: `TransacaoRepository.somar_agrupado_por_conta` agrupa por `conta_id`, hardcoding
`conta_id IS NOT NULL` e `tipo == DESPESA` — essa dupla condição já exclui toda compra de cartão
por construção (compra de cartão grava `cartao_id`, nunca `conta_id`, ver constraint
`ck_transacao_conta_xor_cartao`), o mesmo resultado da decisão de 2026-07-25 sobre `apenas_conta`
(seção 6 de `docs/analise-arquitetural-escopo-parcelamento.md`), só que aqui de graça, sem precisar
de nenhum parâmetro extra. `CentralFinanceiraService.graficos_periodo()` ganhou o terceiro bloco
(`gastos_por_conta`), resolvendo nome via `conta_service.listar(apenas_ativas=False,
apenas_visiveis=False)` — mesmo par usado para resolver nome de conta no calendário (uma despesa
pode ter sido lançada numa conta hoje inativa/oculta, e o gráfico nunca deve omitir o valor por
isso). `GraficosPeriodoRead` ganhou `gastos_por_conta: list[GastoPorConta]` — resposta do endpoint
`/central-financeira/graficos/periodo` já existente, nenhum novo fetch no frontend.

**Frontend** — novo componente `GastosPorContaChart.tsx`, mesma estrutura de
`GastosPorCategoriaChart.tsx` (donut + legenda com % ao lado), paleta categórica por índice (como
`GastoPorCartao`, sem cor própria). Único toque visual novo, a pedido explícito do usuário como
inspiração no app do Mercado Pago: o total do período fica escrito no miolo vazio do donut (um
`<div>` posicionado em absoluto sobre o `ResponsiveContainer`), além de continuar na lista ao lado
— nenhuma outra tela do app tem esse elemento ainda; se o padrão for aprovado no uso real, é
candidato a subir para um componente compartilhado (`DonutChartComTotal` ou similar) e substituir a
duplicação atual entre "Gastos por categoria"/"Saldo por conta"/"Gastos por conta".

## 9. Melhorias de Gráficos (2026-07-26) — 6 pedidos do usuário em cima da página já em produção

Usuário pediu sugestões de melhoria para `/graficos` e, em seguida, pediu para implementar todas.
100% frontend — nenhum endpoint novo, nenhum cálculo de agregação novo no backend. As 6 peças:

**1. Total do mês + variação vs mês anterior.** `GraficosPage` passou a buscar um SEGUNDO
`graficos_periodo` (mês anterior, via novo `utils/date.ts:mesAnterior`) além do já existente (mês
selecionado) — mesmo endpoint, dois `useGraficosPeriodoQuery` com `ano`/`mes` diferentes, cacheados
separadamente pelo React Query. O total do mês é a soma de `gastos_por_categoria` (cobre 100% das
despesas do período — cartão e conta somados, ver seção 2 sobre a garantia de
`somar_agrupado_por_conta`/`somar_agrupado_por_cartao` nunca se sobreporem). Novo componente
`ResumoGastosMes.tsx` exibe o total + a variação percentual. Este último NÃO reaproveita
`ui/TrendIndicator` (usado em `StatCard` para saldo/receita, onde "mais" é sempre bom, verde) —
gasto SUBINDO é a notícia ruim, então a cor é invertida (vermelho para aumento, verde para queda) em
um indicador local (`IndicadorVariacaoGasto`), preservando o "Sistema semântico de status" do
projeto (tone correto por significado, nunca por sinal aritmético cru).

**2. Seletor de mês unificado.** Os 3 cards de gasto (categoria/cartão/conta) tinham cada um seu
próprio `MesAnoSeletor`, sempre sincronizados entre si (mesmo estado `periodo`) — virou um único
seletor compartilhado num novo card de cabeçalho "Gastos do mês", junto do resumo/variação da peça
1, do toggle da peça 6 e do atalho da peça 3.

**3. Atalho para Relatórios.** Botão "Baixar relatório" no card de cabeçalho leva para
`/relatorios?ano=&mes=` com o mês já selecionado aqui — evita escolher o mesmo mês de novo naquela
página. `RelatoriosPage` passou a ler `ano`/`mes` da URL como seed inicial (`useSearchParams`, com
fallback para o mês atual quando ausentes — acesso direto pelo menu continua funcionando igual).

**4. Drill-down por categoria/conta/cartão.** A seção 7 (backlog) desta etapa original listava
"Filtro de categoria/cartão específico dentro do próprio gráfico (drill-down)" como
explicitamente fora de escopo — revisitado agora a pedido do usuário. `GastosPorCategoriaChart`/
`GastosPorContaChart` ganharam `onSelecionarCategoria`/`onSelecionarConta` opcionais: cada linha da
legenda (já existia, virou um `<button>`) leva para `/transacoes?categoria_id=&ano=&mes=` ou
`?conta_id=&ano=&mes=` — filtro EXATO no caso de conta (mesma condição `conta_id IS NOT NULL` que
`gastos_por_conta` já usa), aproximado no caso de categoria (categoria também é atribuída a compras
de cartão, que `/transacoes` nunca lista — ver próximo parágrafo). `TransacoesPage` passou a ler
`categoria_id`/`conta_id`/`ano`/`mes` da URL como seed inicial, e ganhou um novo `Select` "Conta:
todas" (não existia nenhum filtro de conta na tela até então).

"Gastos por cartão" é diferente: `GastosPorCartaoChart` leva para `/cartoes/:id` (a página de
detalhe do cartão), NUNCA para `/transacoes` — compras de cartão nunca aparecem naquela tabela por
desenho (`apenas_conta: true`, pedido explícito do usuário em 2026-07-20, ver
`docs/analise-arquitetural-escopo-parcelamento.md`), então um filtro por `cartao_id` ali sempre
voltaria vazio. Esse gráfico também ganhou uma lista clicável abaixo das barras (não existia
nenhum elemento HTML de verdade ali antes, só o SVG do Recharts) — um `<Cell onClick>` sozinho não é
navegável por teclado nem exposto a leitor de tela; a lista é a superfície acessível real do
drill-down, o clique direto na barra continua funcionando como atalho extra.

**5. Cauda longa agrupada em "Outros".** Novo `lib/agruparCaudaLonga.ts` (helper genérico, testado
isoladamente em `agruparCaudaLonga.test.ts`): agrupa o excedente de uma lista já ordenada (garantia
de `graficos_periodo`, seção acima) num único item sintético "Outros (N)" acima de 6 itens — usado
pelos 3 gráficos de período (`GastosPorCategoriaChart`/`GastosPorCartaoChart`/`GastosPorContaChart`).
O item "Outros" nunca é clicável (`categoria_id`/`conta_id`/`cartao_id: null` só nesse caso).

**6. Comparação com o mês anterior.** Novo componente `GastosComparativoChart.tsx` — barras
horizontais agrupadas (mês atual x mês anterior), genérico por `nome`/`total` (mescla as duas listas
por nome, já que os 3 domínios de id são diferentes entre si). Reaproveitado pelas 3 seções de gasto
quando o toggle "Comparar com mês anterior" (`Switch` no card de cabeçalho) está ativo — substitui o
donut/barra específico daquela seção nesse modo; comparação lado a lado não tem um análogo natural
em donut, então um único componente de barras serve igualmente para as 3 seções. Faz seu próprio
agrupamento de cauda longa (linhas com 2 totais cada, atual e anterior, não cabem no acessor único
de `agruparCaudaLonga`).

**Backlog da seção 7 revisado**: com a peça 4, "drill-down" sai da lista de fora-de-escopo. Com a
peça 6, "comparação ano-a-ano" continua fora de escopo (o que foi pedido e implementado é
mês-a-mês, não ano-a-ano) — mantido no backlog. "Exportação de gráfico como imagem/PDF" também
continua fora de escopo (a peça 3 é um atalho de navegação para a exportação TEXTUAL já existente
de Relatórios, não uma exportação de imagem do gráfico em si).

**Testes**: `agruparCaudaLonga.test.ts` (2), `date.test.ts` ganhou 2 novos (`mesAnterior`),
`GraficosPage.test.tsx` (novo, 6 testes — total+variação, drill-down de categoria/conta/cartão,
atalho de relatório, toggle de comparação). Suíte completa (45 testes), `tsc -b` e `vite build`
revalidados sem regressão.
