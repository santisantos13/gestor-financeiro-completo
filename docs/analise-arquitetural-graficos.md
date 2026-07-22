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
