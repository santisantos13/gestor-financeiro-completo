# Extrato de Conta (histórico expansível) — Análise Arquitetural

## Pedido do usuário

"Cada conta deve ser responsável pelo seu próprio histórico financeiro, assim como os
cartões são responsáveis pelo histórico das compras neles" — ao clicar/expandir uma
Conta em `/contas`, exibir inline (sem navegar para outra página) um painel estilo
extrato bancário: saldo atual, saldo inicial, entradas/saídas/saldo líquido "do
período", última movimentação, quantidade de movimentações, um mini resumo do mês
corrente (entradas/saídas/saldo do mês, maior entrada, maior saída) e o histórico
cronológico, com filtros rápidos (Todos/Entradas/Saídas/Transferências/Pagamentos/
Período). Compras de cartão de crédito NÃO entram aqui — pertencem ao histórico do
Cartão até a fatura ser paga.

## O que já existia (reaproveitado, nada duplicado)

- `Conta.saldo_atual` já é 100% calculado por `ContaService._com_saldo` via duas somas
  SQL (`ContaRepository.somar_transacoes_pagas`/`somar_transferencias`) —
  `ContaService.extrato()` reaproveita esse mesmo método, nunca recalcula saldo.
- `TransacaoService.listar(usuario_id, conta_id=..., status=..., data_inicio=...,
  data_fim=...)` já existe e já é usado por `ContaService._apagar_vinculos` — cobre
  receitas, despesas diretas, pagamento de fatura (`fatura_paga_id` preenchido) e
  pagamento de financiamento/empréstimo (`financiamento_id`/`emprestimo_id`
  preenchido), porque TODOS esses casos são `Transacao` com `conta_id` preenchido
  (nunca `cartao_id`) — ver `models/transacao.py`. Uma compra no cartão sempre tem
  `cartao_id` preenchido e `conta_id` nulo, então já fica fora só pelo filtro
  `conta_id=X` — nenhuma exclusão especial precisou ser escrita para "não mostrar
  compra de cartão aqui".
- `TransferenciaService.listar(usuario_id, conta_id=..., apenas_ativas=True)` já existe
  e já filtra origem OU destino da conta.
- `CentralFinanceiraService.calendario_financeiro`/`atividades_recentes` já
  estabelecem o padrão "combinar Transacao + Transferencia numa lista Python única,
  ordenada por data, sem inventar SQL novo, porque a lista já é pequena e limitada por
  natureza (uma conta, um período)" — o mesmo padrão é usado aqui.

## Por que a agregação do período é feita em Python, não com `SUM` novo

`docs/decisao-performance-saldo.md` estabelece "toda métrica agregada deve ser SQL
`SUM`" para casos como `saldo_atual`/`somar_por_periodo`, onde o Service NUNCA precisa
das linhas — só do número. Aqui é diferente: as mesmas linhas de `Transacao`/
`Transferencia` do período já são buscadas de qualquer forma para exibir a lista de
histórico. Somar essa mesma lista em Python (entradas/saídas/saldo líquido/quantidade/
última movimentação/maior entrada/maior saída) custa zero I/O adicional — a alternativa
seria rodar 2-4 queries de `SUM` A MAIS além da query de listagem, só para recalcular
números que já estão disponíveis na lista que acabou de ser lida. Mesmo raciocínio já
aplicado em `CentralFinanceiraService.calendario_financeiro`/`atividades_recentes`
("a combinação/ordenação é só Python sobre listas já pequenas e limitadas — nunca uma
query nova"). O volume por conta/mês é inerentemente pequeno (dezenas de
movimentações), não a tabela inteira.

## Categorização das movimentações (`CategoriaMovimentacaoConta`)

Novo enum em `models/enums.py`, mesma família de `CategoriaEventoCalendario`
(schema-only, sem coluna de banco, sem migration):

- `RECEITA` / `DESPESA` — `Transacao` sem `fatura_paga_id`/`financiamento_id`/
  `emprestimo_id`, discriminada por `Transacao.tipo`.
- `PAGAMENTO_FATURA` — `Transacao.fatura_paga_id` preenchido.
- `PAGAMENTO_FINANCIAMENTO` — `Transacao.financiamento_id` preenchido.
- `PAGAMENTO_EMPRESTIMO` — `Transacao.emprestimo_id` preenchido.
- `TRANSFERENCIA_ENVIADA` / `TRANSFERENCIA_RECEBIDA` — `Transferencia`, discriminada
  por `conta_origem_id == conta_id` vs `conta_destino_id == conta_id`.

Cada item também carrega `positivo: bool` (RECEITA/TRANSFERENCIA_RECEBIDA = `True`,
todo o resto = `False`) — mesmo campo já usado no frontend por `MetaResumoCard`
(`ItemHistoricoMeta.positivo`), reaproveitado aqui em vez de reinventar a distinção
entrada/saída no cliente.

`Transacao.importada=True` (parcelas de Financiamento/Empréstimo lançadas pelo
onboarding, representando dívida anterior ao uso do app) é excluída do extrato — mesmo
critério já usado em `somar_transacoes_pagas` para não entrar no saldo. O próprio
pedido do usuário reforça isso: "esse histórico deve conter apenas movimentações que
realmente alteraram o saldo da conta", e uma transação `importada` nunca alterou.

## "Período" vs "resumo do mês" — dois eixos independentes

O app já tem uma convenção estabelecida para "período": sempre um único `ano`+`mes`
(nunca um range livre de datas) — `PeriodoSeletor`/`MesAnoSeletor`, usados por
Dashboard/Calendário/Transações. O extrato de Conta segue a mesma convenção:

- **Resumo do período** (`ano`/`mes` — parâmetros opcionais da rota, default = mês
  atual): saldo inicial, entradas/saídas/saldo líquido *daquele mês*, última
  movimentação e quantidade de movimentações *dentro dele*. Navegável com o mesmo
  `PeriodoSeletor` já usado em outras telas — nenhum componente novo.
- **`saldo_atual`**: sempre o saldo real agora, independente do período navegado.
- **Resumo do mês atual** (`resumo_mes_atual`): sempre o mês corrente do calendário
  (`date.today()`), CONSTANTE independente do período que o usuário está navegando no
  bloco acima — "o pulso de agora", não histórico. Se o período selecionado já é o mês
  atual, a mesma lista de movimentações é reaproveitada (nenhuma query extra); só
  quando o usuário navega para outro mês é que uma segunda busca (bem menor,
  Transacao+Transferencia de um único mês) é feita.

Os filtros rápidos "Todos/Entradas/Saídas/Transferências/Pagamentos" filtram a lista de
movimentações já carregada 100% no cliente (mesmo padrão de `filtroRapido` em
`MetasPage`) — não são parâmetros da rota, só o `ano`/`mes` (o filtro "Período" da UI)
o são.

## Endpoint

```
GET /contas/{id}/extrato?ano=&mes=
```

`ano`/`mes` opcionais, default = mês atual. Reaproveita
`ContaService._buscar_da_propriedade_do_usuario` (mesmo 404 uniforme de sempre) e
`_com_saldo`. Resposta (`ContaExtratoRead`):

```
resumo: { saldo_atual, saldo_inicial, entradas_periodo, saidas_periodo,
          saldo_liquido_periodo, ultima_movimentacao, quantidade_movimentacoes }
resumo_mes_atual: { entradas_mes, saidas_mes, saldo_mes, maior_entrada, maior_saida }
movimentacoes: [ { data, descricao, valor, positivo, categoria, origem_tipo, origem_id } ]
```

`origem_tipo`/`origem_id` reaproveitam `TipoEntidadeReferenciavel` (mesmo discriminador
já usado por `EventoCalendario`/`EventoAgenda`/`AtividadeRecente`) — não navegam para
lugar nenhum nesta etapa (fora do pedido original), só ficam disponíveis para o
frontend usar no futuro sem precisar de outra migração de schema.

## Frontend: card expansível (não `DataTable`)

`DataTable` não suporta painel de detalhe inline — confirmado por inspeção de
`components/ui/DataTable.tsx`. O mesmo trade-off já foi feito (e aceito pelo usuário)
para Meta: `MetasPage` já abandonou `DataTable` em favor de um grid de
`MetaResumoCard`, cada card expansível inline via `AnimatePresence` + animação de
`height` (`0 → "auto"`), usando os tokens de `lib/motion.ts`
(`DURATION.moderate`/`EASE.out` para abrir, `DURATION.fast`/`EASE.in` para fechar) —
exatamente os Motion Principles do projeto (`docs/motion-principles.md`, §9: accordion
usa animação de altura). `ContaResumoCard` segue o mesmo molde, com dado do extrato
buscado sob demanda (`enabled: expandido`, mesmo padrão de
`useAportesLegadosDaMeta`/`useTransferenciasDoCofrinho`) — a lista não é buscada até o
card ser expandido, mantendo a página inicial leve.

`ContasPage` troca `DataTable` por um grid (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3`,
mesmo breakpoint de `MetasPage`), com filtros rápidos por tipo + busca + ordenação
100% client-side sobre a lista completa (`useContas(false)`), preservando
`ContaFormDialog` e os três `ConfirmAction` de exclusão/desativação já existentes sem
nenhuma mudança de comportamento.

## Refinamento de densidade (pedido explícito do usuário, mesmo dia)

O grid de cards grandes acima ("mini dashboard" nos moldes de `CartaoResumoCard`)
funcionou para a expansão inline, mas ficou pesado como visão PRINCIPAL — "deixam a
tela pesada e exigem muita rolagem". Trocado por uma lista densa e escaneável, estilo
aplicativo bancário, sem perder nenhuma funcionalidade (expansão inline, filtros
rápidos, período, ações):

- `ContaResumoCard` deixou de renderizar seu próprio `Card` (borda + sombra +
  `whileHover` de elevação, pensados para cards isolados num grid) e passou a
  renderizar uma LINHA (`<div role="button">`) sem chrome próprio — a "sensação de
  lista" agora vem do container único em `ContasPage`, que usa `divide-y` entre as
  linhas em vez de N cards empilhados com borda/sombra repetida em cada um.
- Layout da linha, da esquerda para a direita: `InstitutionBadge` (logo) → nome em
  destaque + "tipo · instituição" como legenda secundária (uma linha só, em vez de
  duas linhas separadas) → saldo numa coluna de LARGURA FIXA (`sm:w-32`, alinhado à
  direita) → status como microindicador discreto (`StatusDot` + texto — trocado do
  `AtivoBadge` colorido cheio usado antes, pedido explícito: "status discreto") →
  ações agrupadas → chevron. A largura fixa da coluna de saldo é o que garante os
  valores alinhados verticalmente entre contas, independente do tamanho do nome.
- Responsivo: `sm:flex-row` no desktop (tudo numa linha só); abaixo do breakpoint
  `sm`, o container principal vira `flex-col`, then o bloco
  logo+nome+saldo forma a primeira "linha" visual e ações+chevron a segunda —
  preserva a sensação de lista no mobile em vez de virar um card empilhado de novo.
- Preservado sem nenhuma mudança de comportamento: expansão inline (mesma
  `AnimatePresence`/animação de altura), `PeriodoSeletor`, filtros rápidos
  (Todos/Entradas/Saídas/Transferências/Pagamentos), resumo do período, mini resumo
  do mês atual, histórico cronológico, e os filtros/busca/ordenação de `ContasPage`.
