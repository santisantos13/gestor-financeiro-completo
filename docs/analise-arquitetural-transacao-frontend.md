# Análise arquitetural — Transação (frontend)

## 0. Escopo e contexto

Próximo CRUD do frontend (14 entidades no total; 5 concluídas: Conta,
Categoria, Tag, Cartão, Fatura). Transação é qualitativamente diferente de
tudo que veio antes: é a única entidade que já nasce com volume real
(lançamentos acumulam todo dia), é o ponto de encontro de praticamente
todas as outras entidades do sistema (Conta, Cartão, Categoria, Tag e,
futuramente, Parcelamento/Financiamento/Empréstimo/ContaRecorrente/Meta) e,
segundo o pedido explícito desta etapa, deve ser "um dos pontos altos do
projeto" — a tela mais usada do aplicativo, não apenas uma tabela.

Este documento cobre só o frontend. O backend (`app/models/transacao.py`,
`app/schemas/transacao.py`, `app/services/transacao_service.py`,
`app/repositories/transacao_repository.py`, `app/api/routes/transacao.py`)
foi lido por completo e não é alterado nesta etapa — nenhuma regra de
negócio nem endpoint novo. Este documento também assume como já
formalizados: `docs/design-system.md` (cores, tipografia, componentes),
`docs/motion-principles.md` (timing/easing) e
`docs/analise-arquitetural-frontend.md` (arquitetura geral: `httpClient`,
`queryKeys`, camada `services`/`hooks`, `DataTable`/`useDataTable`,
`Form`/`*Field`, schemas Zod).

## 1. O que o backend garante (resumo operacional para a UI)

- `conta_id` XOR `cartao_id`: toda transação pertence exatamente a uma
  origem. Imutável após a criação — não aparece em `TransacaoUpdate` nem na
  rota PATCH (`app/api/routes/transacao.py`, docstring do módulo).
- No máximo um de `parcelamento_id`/`financiamento_id`/`emprestimo_id`.
  `numero_parcela` só faz sentido (e só é aceito) se um desses três estiver
  presente.
- `status` tem significado dependente do contexto: em transação de Conta é
  autoritativo e livremente editável (PENDENTE/PAGO); em transação de
  Cartão é sempre forçado para PAGO na criação — a autoridade real sobre
  pagamento passa a ser a Fatura, não este campo.
- `fatura_id`/`fatura_paga_id` são sempre derivados internamente pelo
  backend (`TransacaoService` via `FaturaService.resolver_fatura_aberta`) —
  nunca aparecem em `TransacaoCreate`/`TransacaoUpdate`, e a UI não deve
  tentar prever ou exibir controle algum sobre eles no formulário.
- `parcelamento_id`/`financiamento_id`/`emprestimo_id`/
  `origem_recorrente_id`/`meta_id`: o `TransacaoService` **já valida
  integralmente** a posse/existência desses vínculos (achado desta
  releitura: um comentário do schema ainda descreve isso como "decisão
  YAGNI adiada", mas o `_validar_parcelamento`/`_validar_financiamento`/
  `_validar_emprestimo`/`_validar_conta_recorrente`/`_validar_meta_ativa`
  do Service já fazem a validação completa — o comentário está
  desatualizado, não o código). Isso não muda a decisão de escopo do
  frontend (seção 6): nenhuma dessas entidades tem CRUD/tela própria ainda,
  então não há de onde a UI ofereceria um ID válido para esses campos.
- Sem soft delete: `Transacao` é lançamento de livro-razão de verdade — o
  único endpoint de remoção é `DELETE /transacoes/{id}`, sempre definitivo.
  Não existe `ativo`/"desativar" para esta entidade (diferente de
  Conta/Categoria/Tag/Cartão).
- Listagem (`GET /transacoes`) aceita filtros server-side reais:
  `conta_id`, `cartao_id`, `categoria_id`, `parcelamento_id`,
  `financiamento_id`, `emprestimo_id`, `origem_recorrente_id`, `meta_id`,
  `tipo`, `status`, `data_inicio`, `data_fim`, `skip`, `limit` (default
  100). Ordenação é sempre `data desc, id desc` (mais recente primeiro),
  fixa no repository — não há parâmetro de ordenação.

## 2. Decisão 1 — Filtragem híbrida (servidor filtra período, `DataTable` pagina/busca/ordena por cima)

Toda entidade anterior usa `useDataTable` 100% client-side: busca a lista
inteira (limite alto, volume pequeno de "dado mestre") e faz busca, filtro,
ordenação e paginação inteiramente no navegador
(`docs/analise-arquitetural-frontend.md`, seção 13). Transação quebra essa
premissa: lançamentos acumulam de verdade, e o backend já teria mais de 100
registros num usuário ativo depois de poucos meses — o `limit` default do
endpoint deixaria de ser "generoso" e passaria a truncar dado real.

Decisão: `TransacoesPage` sempre envia um filtro de período ao backend
(reaproveitando `PeriodoSeletor`, já usado no Dashboard — `ano`+`mes` viram
`data_inicio`/`data_fim` do primeiro/último dia do mês) e, opcionalmente,
`tipo`/`status`/`categoria_id`/`conta_id`/`cartao_id` como parâmetros reais
de `GET /transacoes` (nova query key `queryKeys.transacoes.list(filtros)`,
refetch a cada mudança de filtro real). O resultado já filtrado no servidor
(tipicamente dezenas de linhas por mês, nunca centenas) alimenta o
`DataTable` normalmente — que continua responsável só por busca textual
adicional, ordenação de coluna e paginação de exibição, exatamente como já
faz hoje. Nenhuma mudança em `useDataTable`/`DataTable`: a única mudança é
que, pela primeira vez, o array que entra em `data` já vem pré-filtrado do
backend em vez de ser "tudo que existe".

Um seletor de período sempre visível (não escondido atrás de um filtro
opcional) também resolve o pedido de produto: a pergunta mais comum ao
abrir a tela é "o que aconteceu neste mês", não "me mostre tudo".

## 3. Decisão 2 — Origem (Conta × Cartão) como seletor segmentado, imutável na edição

`TransacaoFormDialog` precisa resolver `conta_id` XOR `cartao_id` sem
expor os dois `Select`s simultaneamente (confuso, e o backend rejeita se
os dois vierem preenchidos). Solução: um controle segmentado — dois
botões, "Conta" / "Cartão de crédito" — decide qual dos dois selects
aparece embaixo (`AccountSelect` ou o novo `CardSelect`, seção 4). Estado
guardado no próprio formulário (não no schema Zod como union — mais simples
manter os dois campos e limpar o que não está ativo no submit).

Na criação, os dois botões ficam habilitados. Na edição, a origem já
escolhida aparece fixa (sem os botões, só o valor lido, com um texto
explicativo — "A origem de uma transação não pode ser alterada depois de
criada; exclua e crie uma nova se precisar mudar") porque o backend não
aceita `conta_id`/`cartao_id` em `TransacaoUpdate`. Mesmo princípio já
aplicado a `Fatura.cartao_id` (imutável, resolvido apenas na criação).

## 4. Decisão 3 — `CardSelect` (novo componente)

Não existe hoje (confirmado por grep: só `AccountSelect`/`CategorySelect`
existem). Espelha `AccountSelect.tsx` quase literalmente: usa `useCartoes`,
mapeia para `{value: String(id), label: nome}`, mesmo `SearchSelect` por
baixo. Único acréscimo de valor: usar `InstitutionBadge`/`BandeiraBadge`
como `render` de cada opção (mesmo padrão de slot visual que
`CategorySelect` já usa para ícone+cor) — reconhecer o cartão pela
bandeira/instituição é mais rápido que ler o nome puro, e o componente já
existe em outro lugar do projeto (nenhum "ícone novo" inventado aqui).

## 5. Decisão 4 — `CategorySelect` ganha filtro por `tipo`

`CategorySelect.tsx` já tem um comentário próprio prevendo este uso
("usado... futuramente, para `categoria_id` em Transação"), mas hoje não
filtra por tipo. Nova prop opcional `tipoTransacao?: TipoTransacao` — quando
passada, a lista de opções é restrita a categorias com
`categoria.tipo === tipoTransacao || categoria.tipo === "AMBOS"`
(`TipoCategoria` é `"RECEITA" | "DESPESA" | "AMBOS"`, valores idênticos aos
de `TipoTransacao` — comparação direta de string, sem tabela de
tradução). Puramente uma filtragem de UX (evita o usuário escolher uma
categoria de Despesa numa transação de Receita); a validação de
compatibilidade real continua no backend. `TransacaoFormDialog` observa o
campo `tipo` do próprio formulário (`useWatch`) e repassa como
`tipoTransacao` — trocar de Receita para Despesa depois de já ter
escolhido uma categoria incompatível limpa a seleção (mesmo padrão de
"dependência entre campos" que o projeto ainda não tinha, primeiro caso
real).

## 6. Decisão 5 — `TagMultiSelect` (novo componente sobre `MultiSelectField`)

Não existe hoje. `tag_ids: number[]` no payload, `MultiSelectField` já
existe como primitivo genérico (`value: string[]` de RHF) — falta só a
camada "inteligente" de domínio que busca a lista de tags via `useTags` e
monta `SelectOption[]`, exatamente como `AccountSelect`/`CardSelect` fazem
para seus respectivos hooks. Diferente de `MultiSelectField` puro, mostra
cada opção selecionada como `TagBadge` (cor real da tag) em vez do `Badge`
genérico `tone="accent"` que `MultiSelectField` usa por padrão — pequeno
ajuste visual, não uma reescrita: basta passar um `renderTag`/usar a lista
de tags já carregada para resolver a cor no lugar de exibir só o rótulo.

## 7. Decisão 6 — Visibilidade condicional de `status`

Campo `status` só é exibido como controle editável quando a origem
escolhida é Conta (`SwitchField`/toggle Pendente↔Pago, ou um `SelectField`
simples com as duas opções). Quando a origem é Cartão, o campo não aparece
no formulário — mostrar um toggle que o backend vai ignorar (sempre força
PAGO) seria, na melhor das hipóteses, redundante, e na pior, enganoso.
Na listagem, a coluna "Status" usa `FinancialBadge` (já existente,
`TONE_POR_STATUS` já cobre `PENDENTE`/`PAGO`), sempre visível
independentemente da origem — é informação, mesmo quando não editável.

## 8. Decisão 7 — Campos adiados (preparados para o futuro, não implementados)

Seguindo o mesmo princípio já usado no placeholder "Histórico" de
`CartaoDetalhePage` (documentar e não construir lógica provisória):
`parcelamento_id`, `financiamento_id`, `emprestimo_id`, `numero_parcela`,
`origem_recorrente_id` e `meta_id` **não aparecem** em
`TransacaoFormDialog` nesta etapa. Nenhuma dessas cinco entidades tem
CRUD/tela de navegação própria ainda — expor um campo de ID cru
("digite o ID do parcelamento") seria pior do que não expor nada, e
qualquer picker de verdade (`ParcelamentoSelect` etc.) só faz sentido
depois que a entidade correspondente existir. `types/transacao.ts` inclui
os campos (espelhando `TransacaoRead`/`TransacaoCreate`/`TransacaoUpdate`
1:1, mesmo princípio de todo `types/*.ts` do projeto), mas o formulário
nunca os envia — ficam `undefined`, o que o backend já trata como "nenhum
vínculo". Quando essas entidades ganharem CRUD próprio, a extensão é
aditiva (um `*Select` novo + um campo condicional a mais no formulário),
nunca uma reestruturação.

## 9. Novos arquivos de dados

- `types/transacao.ts` — espelha `TransacaoCreate`/`TransacaoUpdate`/
  `TransacaoRead` (seção 1). `tags: TagRead[]` em `TransacaoRead` (mesmo
  padrão de objeto aninhado que `FaturaRead` não tem, mas que o backend
  aqui de fato retorna).
- `schemas/transacao.ts` — Zod só para formato/obrigatoriedade
  (`valor` > 0, `descricao` 1–200, `data` obrigatória, exatamente um de
  `conta_id`/`cartao_id` via `.refine`). Conversão forms→payload trata a
  origem (limpa o campo não-ativo) e omite os campos adiados da seção 8.
- `services/transacaoService.ts` — `listar(filtros)` repassa todos os
  parâmetros de query já suportados pelo backend (seção 1) direto para
  `httpClient.get`; `criar`/`atualizar`/`excluir` no mesmo molde de
  `cartaoService.ts`. Sem `desativar` (não existe — seção 1).
- `api/queryKeys.ts` — nova seção `transacoes`: `list(filtros)` (objeto de
  filtros inteiro na chave, igual ao padrão `dashboard.resumo(ano, mes)`
  já usado) e `detail(id)`.
- `hooks/useTransacaoQueries.ts` — `useTransacoes(filtros)`,
  `useTransacao(id)`, `useCriarTransacao`, `useAtualizarTransacao`,
  `useExcluirTransacao`. Invalidação é a mais ampla do projeto até agora:
  além de `queryKeys.transacoes.all`, toda mutation invalida
  `dashboard.resumo`, `dashboard.saldoConsolidado`, `dashboard.contas`,
  `dashboard.cartoes`, `dashboard.faturas`, `dashboard.visaoMensal`,
  `dashboard.agenda`, `dashboard.indicadores` e, quando a transação tem
  `conta_id`/`cartao_id` conhecido, `contas.detail(conta_id)`/
  `cartoes.detail(cartao_id)` — uma transação nova ou excluída muda saldo
  de conta OU limite de cartão OU fatura, então quase todo o Dashboard
  depende dela (nenhuma outra entidade do projeto tem esse alcance).

## 10. Componentes novos de UI/domínio

| Componente | Domínio/UI | Descrição |
|---|---|---|
| `CardSelect` | domínio/cartao | Seção 4 |
| `TagMultiSelect` | domínio/tag | Seção 6 |
| `TransacaoFormDialog` | domínio/transacao | Seções 3, 5, 7, 8 |
| `transacaoTableColumns` | domínio/transacao | Colunas: data, descrição, categoria (`CategoryBadge`), origem (conta/cartão), tipo (ícone seta ↑/↓ + cor positive/negative — nunca só texto), valor (`tabular`, cor por tipo), status (`FinancialBadge`), tags (`TagBadge`, truncado) |
| `TransacaoResumoPeriodo` | domínio/transacao | Faixa de `MetricCard`s acima da tabela: Receitas do período, Despesas do período, Saldo do período — mesma agregação que `somar_por_periodo` já expõe, reaproveitando `centralFinanceiraService`/`useCentralFinanceiraQueries` existentes (não uma soma nova no cliente) sempre que os números batem com o que o Dashboard já mostra |

`CategorySelect` ganha a prop `tipoTransacao` (seção 5); nenhuma outra
alteração em componente existente.

## 11. `TransacoesPage`

Diferente de `/cartoes` (grid de cards — decisão deliberadamente pontual
para um "mini dashboard" por cartão, não um padrão geral, ver
`design-system.md` seção 18), `/transacoes` usa `DataTable`: volume alto,
uma linha por lançamento é o modelo mental correto (livro-razão), e
`DataTable` já resolve responsividade (linha vira card em `md-`), seleção
em massa e ações por linha sem nenhum componente novo. Composição da
página: `PeriodoSeletor` + `TransacaoResumoPeriodo` (seção 10) + barra de
filtros adicionais (`tipo`/`status`/categoria via `FilterBar`, mesma
mecânica de `contaTableFilters`) + `DataTable` com `transacaoTableColumns`
+ `TransacaoFormDialog` + `ConfirmAction` de exclusão (sem "desativar" —
seção 1). Ação rápida "Nova transação" sempre visível (botão primário no
topo, mesmo padrão de toda página de CRUD existente) — é a ação mais
frequente da tela mais usada do app, then merece estar sempre a um clique.

## 12. Fora de escopo desta etapa

- Qualquer UI para Parcelamento/Financiamento/Empréstimo/ContaRecorrente/
  Meta (seção 8) — inclusive os campos de vínculo no formulário de
  Transação.
- Edição em massa (`bulkActions` do `DataTable` já suporta a mecânica, mas
  nenhuma ação em massa real foi pedida para Transação nesta etapa).
- Importação/OFX, anexos, ou qualquer criação automática de transação
  (recorrência, parcelamento) — todas dependem de CRUDs futuros.
- Gráficos/visualizações novas além dos `MetricCard`s do resumo do
  período — o Dashboard já tem seus próprios gráficos; duplicar aqui não
  foi pedido.

## 13. Auditoria final planejada (mesmo checklist das etapas anteriores)

UX, UI, Motion, Responsividade, Performance (busca com `useDeferredValue`
já herdada de `useDataTable`; nenhum recalculo pesado por tecla),
Hierarquia, Acessibilidade e Consistência — validado ao final via `tsc -b`
+ `vite build`, mais smoke test manual dos três fluxos centrais (criar
transação de Conta, criar transação de Cartão, editar/excluir).

## 14. Regra nova (2026-07-20): compras de cartão não aparecem em `/transacoes`

Pedido explícito do usuário: "as compras feitas com o cartão de crédito,
NÃO DEVEM aparecer em transações, em transações devem aparecer apenas
compras feitas utilizando as contas cadastradas e os pagamentos de
faturas". Como `Transacao.conta_id`/`cartao_id` são mutuamente exclusivos
(CHECK constraint, `app/models/transacao.py`) e um pagamento de fatura
grava `conta_id` (a conta de pagamento do cartão, nunca `cartao_id` — ver
`FaturaService.registrar_pagamento`), a regra inteira se resume a um
filtro: esconder linhas com `cartao_id IS NOT NULL`.

Implementado como filtro **aditivo e opt-in** (`apenas_conta: bool =
False`) em toda a cadeia — `TransacaoRepository.listar_do_usuario` →
`TransacaoService.listar` → `GET /transacoes?apenas_conta=true` —
nunca como mudança do comportamento padrão. `TransacoesPage.tsx` é o
único consumidor que envia `apenas_conta: true` (hardcoded, não é um
toggle visível — a regra é absoluta, não uma preferência). Todo outro
chamador de `TransacaoService.listar` (`CentralFinanceiraService`,
`CartaoService`, `ContaService`, `Financiamento`/`EmprestimoService`)
continua sem passar esse parâmetro, então compras de cartão continuam
entrando normalmente em limite de cartão, faturas, Central
Financeira/Dashboard e Calendário — a regra é só de **exibição** na tela
de Transações, nunca dos dados por trás dela.

Fora de escopo desta mudança (não pedido, não implementado): remover a
opção "Cartão" do seletor de origem ao criar uma transação a partir de
`/transacoes` — hoje ainda é possível criar uma compra de cartão por lá,
que desaparece da lista imediatamente após criada (comportamento
consistente com a regra, só potencialmente surpreendente). O caminho
recomendado para compras de cartão continua sendo `/cartoes/:id` → "Nova
compra".
