# Análise arquitetural — CRUD de Meta (Frontend, Etapa F12)

Décima primeira entidade a ganhar CRUD real no frontend (Conta, Categoria, Tag, Cartão,
Fatura, Transação, Parcelamento, Transferência, Financiamento, Empréstimo já concluídas).
Diferente de todas as anteriores, o backend de Meta já nasceu **completo e fechado**:
`docs/analise-arquitetural-meta.md` e `docs/revisao-tecnica-meta.md` documentam uma
implementação já testada (709 testes, migração validada, zero drift) — este documento não
questiona nenhuma regra de negócio já decidida lá, só projeta a experiência de frontend sobre
o que já existe. A única decisão pendente de verdade não é sobre Meta em si, é sobre um campo
que falta em Transação (seção 3.6).

## 0. Por que Meta é diferente de tudo que já foi construído

Toda entidade anterior com "progresso" (Financiamento, Empréstimo, Parcelamento, utilização de
Cartão) mede *quanto falta pagar de uma dívida*. Meta é a primeira entidade que mede o
**inverso**: quanto já foi guardado rumo a um objetivo. Isso muda o tom emocional pretendido
pelo usuário ("inspiradora", "incentivar a economizar") e também a mecânica de dados: uma
Meta não tem cronograma gerado na criação (nenhuma parcela, nenhuma data fixa por aporte) —
ela cresce por transações soltas que o próprio usuário decide lançar, no ritmo que quiser, e
pode até encolher (uma retirada é uma `DESPESA` com `meta_id`). O frontend não pode tratar
Meta como "mais um Financiamento" — a metáfora certa é mais próxima de "um cofrinho que se
enche a partir de qualquer lançamento normal do dia a dia", não de um contrato com plano de
pagamento.

## 1. O que já existe no backend (não é código novo, só o que o frontend consome)

- `Meta`: `id`, `descricao` (único por usuário, com semântica de reativação — seção 2),
  `valor_alvo` (`Decimal`, sempre > 0), `data_alvo` (opcional), `conta_id` (opcional, só
  organizacional — **nunca participa do cálculo de progresso**), `ativo`.
- `MetaRead` acrescenta `valor_acumulado`/`percentual` — **sempre calculados no backend**
  (`MetaService._com_progresso`, soma de `Transacao.valor` com `meta_id` apontando para a
  Meta, só transações `PAGO`, RECEITA soma/DESPESA subtrai). O frontend nunca refaz essa
  conta — só lê, formata e anima o valor já pronto (mesmíssimo princípio de
  `Cartao.limite_disponivel`/`Financiamento.saldo_devedor`, e a instrução explícita do
  pedido original: "o cálculo de progresso já existe no backend e não deve ser reproduzido").
  `percentual` não tem teto — pode passar de 100% se a meta for superada.
- Rotas (`app/api/routes/meta.py`): `POST /metas`, `GET /metas` (`apenas_ativas`, `skip`,
  `limit`), `GET /metas/{id}`, `PATCH /metas/{id}` (todos os campos opcionais, inclui
  `ativo`), `DELETE /metas/{id}` (soft delete — marca `ativo=False`, nunca apaga a linha;
  **não existe exclusão definitiva/hard-delete para Meta**, diferente de Conta/Categoria/
  Tag/Cartão/Fatura/Financiamento, que ganharam essa capacidade em etapas anteriores — ver
  seção 2.3).
- `Transacao.meta_id`: FK opcional, **já validada** por `TransacaoService._validar_meta_ativa`
  (existe + pertence ao usuário + está ativa) e já filtrável em `GET /transacoes?meta_id=`.
  Ortogonal a `financiamento_id`/`parcelamento_id`/`emprestimo_id` — uma transação pode ter
  `meta_id` e um desses outros vínculos ao mesmo tempo. **Não existe** em
  `ParcelamentoCreate` — uma compra parcelada não pode ser marcada como aporte de meta.
- `CentralFinanceiraService` já integra Meta em três lugares: `progresso_metas()` (endpoint
  `GET /central-financeira/metas`, consumido hoje só pelo `MetasCard` do Dashboard),
  `indicadores_gerais()` (`metas_ativas`, `percentual_medio_metas`) e
  `calendario_financeiro()` (evento de categoria `META` no dia de `data_alvo`, quando
  preenchida e dentro do mês consultado).

## 2. ANÁLISE — mapeamento completo do CRUD

### 2.1 Criação

`MetaFormDialog` (mesmo padrão `FormDialog` + `Form` + `*Field` de toda entidade): campos
`descricao` (`TextField`), `valor_alvo` (`CurrencyField`), `data_alvo` (`DateField`,
opcional — "Sem prazo definido" quando vazio) e `conta_id` (`AccountSelect`, opcional,
rotulado como algo como "Conta dedicada (cofrinho)" com descrição deixando claro que é só
organizacional e não afeta o progresso — evita o usuário achar que precisa ter uma conta
específica para a meta "funcionar"). `POST /metas`.

**Reativação por nome (backend já implementado, frontend só precisa não atrapalhar).** Se o
usuário digitar uma `descricao` que colide com uma Meta desativada seguida, o backend
reativa e sobrescreve os campos silenciosamente, devolvendo 201 normal — o formulário não
precisa de nenhuma lógica especial, só funciona. Se colidir com uma Meta **ativa**, o backend
devolve 409 (`ConflictError`) — tratado como qualquer outro conflito do projeto:
`form.setError("descricao", ...)` a partir de `getFieldErrors`, mesmo padrão de
Tag/Cartão/Conta.

### 2.2 Edição

Mesmo `MetaFormDialog`, todos os campos editáveis via `PATCH /metas/{id}` (`MetaUpdate` é
100% opcional, `exclude_unset`). Renomear para uma descrição já usada por uma Meta inativa
**não** reativa/mescla — 409, mesmo tratamento da criação. `ativo` também é editável via
`PATCH` (permite reativar sem passar pelo fluxo de criação — mesma forma de
`TagUpdate`/`CartaoUpdate`), mas a UI expõe isso como um botão "Reativar" dedicado (seção
2.3), não como um campo solto dentro do formulário.

### 2.3 Exclusão / desativação

**Só soft delete existe no backend.** `DELETE /metas/{id}` marca `ativo=False` sem apagar a
linha — histórico de aportes (transações com `meta_id`) nunca é afetado. Mesmo padrão visual
de Cartão: um `ConfirmAction` de "Desativar" (não "Excluir" — a linguagem importa: nada é
apagado), e quando a Meta já está inativa, a ação vira "Reativar" (`PATCH {ativo: true}`),
sem confirmação extra (reativar é sempre seguro, nunca destrutivo).

Diferente de Conta/Categoria/Tag/Cartão/Fatura/Financiamento (que ganharam exclusão
definitiva em etapas dedicadas — `docs/analise-arquitetural-fatura-frontend.md` seção 6 e a
Tarefa de "Exclusão hard delete"), **Meta não tem essa capacidade no backend hoje**. Não é um
bug nem uma omissão desta análise — é escopo que nunca foi pedido para Meta. Fica registrado
como item explícito de aprovação (seção 8): implementar só soft delete agora, ou pedir a
extensão de hard-delete como um adendo antes de codar. Recomendação: só soft delete por
enquanto — uma Meta tem, por natureza, uma relação de longo prazo com o histórico financeiro
do usuário (ela é literalmente uma "sobre o que foram meus aportes"), diferente de um Cartão
cadastrado errado por engano.

### 2.4 Filtros e pesquisa

O backend só filtra por `apenas_ativas` (booleano). Volume de Metas por usuário é baixo por
natureza (poucas metas de vida ativas ao mesmo tempo — muito diferente do volume de
Transação), então o mesmo raciocínio já usado em Cartão/Financiamento/Empréstimo se aplica:
**grid de cards, não `DataTable`**, com um `Switch` "Mostrar desativadas" (mesmo texto/
posição de "Mostrar quitados" em `FinanciamentosPage`) controlando `apenas_ativas` na query.
Busca textual por `descricao`, client-side (a lista inteira já está em memória, filtrar no
servidor seria over-engineering para uma lista de poucos itens) — só aparece quando há
metas suficientes para justificar (ex. a partir de ~6 cards, mesmo limiar de bom senso usado
em outras listas pequenas do projeto).

### 2.5 Ordenação

O backend ordena por `descricao` (alfabético) e não aceita nenhum outro parâmetro de
ordenação. Como a lista completa já chega ao cliente (baixo volume), a ordenação "que importa
de verdade" é uma decisão de apresentação, não uma query nova: um controle client-side simples
(3 opções: "Mais urgentes primeiro" — combina `tonePorPrazo`/proximidade de `data_alvo`,
metas sem prazo por último; "Maior progresso primeiro" — `percentual` desc; "Nome" — o próprio
default do backend) resolvido com um `Select` pequeno acima do grid, sem nenhum novo parâmetro
de API.

### 2.6 Estados

Todos derivados **client-side a partir de valores já calculados pelo backend** (nunca
recalculando `valor_acumulado`/`percentual` em si — só classificando o que já veio pronto,
exatamente como `tonePorUtilizacao`/`tonePorPrazo` já fazem para Cartão hoje):

- **Ativa / desativada** — campo `ativo`, direto.
- **Concluída** — `percentual >= 100` (independente de `data_alvo`). É o estado mais
  "celebrável" da tela (seção 5).
- **Em andamento** — `0 < percentual < 100`.
- **Sem nenhum aporte ainda** — `valor_acumulado == 0` (uma meta recém-criada).
- **Atrasada** — `data_alvo` no passado E `percentual < 100`. Usa a mesma régua de
  `tonePorPrazo` (que já documenta explicitamente "mesma régua serve... para prazo de Meta no
  futuro" desde que foi escrita).
- **Sem prazo definido** — `data_alvo == null`, um estado neutro (não é nem bom nem ruim,
  só "sem urgência calculável").

Nenhum destes é um campo novo do backend — são só funções puras de apresentação, mesmo
espírito de `utils/status.ts`.

### 2.7 Integração com Dashboard

`MetasCard` já existe e já lê `useMetasQuery()` (`/central-financeira/metas`), já mostra
`ProgressBar` + prazo com `tonePorPrazo`. Seu próprio comentário já registra a lacuna:
*"Sem destino de navegação — `/metas` ainda não existe como rota — card permanece não
clicável, documentado como deferido até essa entidade ganhar CRUD próprio."* Essa etapa é
exatamente esse momento. Mudança necessária: cada item da lista (ou o card inteiro, mesmo
padrão de `FinanciamentosCard`/`CartoesCard` de navegar para a página da entidade) passa a
navegar para `/metas` (ou, melhor ainda, para `/metas` com o card daquela meta em destaque —
decisão de implementação, não estrutural). Nenhuma mudança na query nem no schema.

### 2.8 Integração com Central Financeira

Três endpoints já existem e já são consumidos (seção 1) — nenhum novo endpoint necessário.
O que muda com o CRUD: toda mutação de Meta (criar/editar/desativar/reativar) precisa
invalidar `dashboard.metas` e `dashboard.indicadores` (mesmo raciocínio de `cartoes`/
`financiamentos`/`emprestimos` já implementados: a Central Financeira agrega o mesmo dado, e
sem invalidação o Dashboard ficaria com números defasados até um F5 manual — o mesmo bug já
corrigido para Fatura na etapa de Refinamento de Pagamento). Quando `data_alvo` é
criada/alterada/removida, `dashboard.calendario` do mês afetado (e do mês anterior, se a data
mudou de mês) também precisa invalidar — mesmo padrão de Transferência.

### 2.9 Integração com Transações — o ponto mais importante desta análise

Achado central: **o backend já fecha essa lacuna (`_validar_meta_ativa`, filtro
`meta_id` em `GET /transacoes`), mas o frontend não tem absolutamente nenhum campo de Meta
em lugar nenhum** — `types/transacao.ts` até declara `meta_id` no `TransacaoCreate`/
`TransacaoUpdate` (herdado do backend), mas `schemas/transacao.ts`
(`transacaoFormSchema`/`TransacaoFormValues`/`transacaoFormValuesParaCriacao`/
`...ParaAtualizacao`) simplesmente não menciona o campo, e `TransacaoFormDialog.tsx` não
renderiza nenhum seletor para ele.

Isso não é um detalhe cosmético: **sem essa peça, nenhuma Meta jamais teria
`valor_acumulado` maior que zero**, porque a única forma de um aporte existir é uma
`Transacao` normal marcada com `meta_id` — não existe (nem deveria existir, por design do
backend) nenhum outro caminho de "depositar" numa Meta. Uma tela de Metas premium sem essa
peça seria uma vitrine vazia. Por isso este documento trata a peça abaixo como **parte
obrigatória do escopo desta etapa**, não como um "nice to have" à parte:

- Novo componente `MetaSelect` (`components/domain/meta/MetaSelect.tsx`), espelhando
  `CardSelect.tsx` quase literalmente: `SearchSelect` sobre `useMetas(apenasAtivas=true)`,
  cada opção mostrando o ícone `Target` + `descricao` + o percentual atual como pista visual
  (ex. "Viagem para o Japão — 42%"), para o usuário reconhecer a meta certa sem precisar abrir
  cada uma.
- Adicionado a `TransacaoFormDialog` como campo **opcional**, sempre visível (RECEITA e
  DESPESA, CONTA e CARTÃO — `meta_id` é ortogonal a tudo isso no backend), rotulado "Meta
  (opcional)" com uma descrição curta explicando o efeito ("Receita = aporte à meta; despesa
  = retirada da meta"). **Não aparece no modo Parcelado** (mesmo raciocínio já aplicado a
  `TagMultiSelect`: `ParcelamentoCreate` não tem `meta_id`, então mostrar o campo seria
  prometer algo que o backend silenciosamente ignoraria — omitir é mais honesto).
- `transacaoFormSchema` ganha `meta_id: z.string()` (mesmo padrão de `categoria_id` — string
  vazia = nenhuma); `transacaoFormValuesParaCriacao`/`...ParaAtualizacao` passam
  `meta_id: valores.meta_id === "" ? null : Number(valores.meta_id)`.
- Mutations de Transação que tocam `meta_id` (criar, editar) precisam invalidar
  `dashboard.metas`/`dashboard.indicadores` além do que já invalidam hoje — mesmo padrão da
  seção 2.8, só que disparado do lado de Transação em vez de Meta.

### 2.10 Atualização automática via React Query

Novo bloco em `api/queryKeys.ts`:

```ts
metas: {
  all: ["metas"] as const,
  list: (apenasAtivas: boolean) => ["metas", "list", apenasAtivas] as const,
  detail: (id: number) => ["metas", "detail", id] as const,
},
```

`hooks/useMetaQueries.ts` (novo): `useMetas`, `useMeta`, `useCriarMeta`, `useAtualizarMeta`,
`useDesativarMeta`/`useReativarMeta` — mesmo formato de `useCartaoQueries.ts`. Toda mutation
invalida `metas.all` + `dashboard.metas` + `dashboard.indicadores` (+ `dashboard.calendario`
quando `data_alvo` está envolvido, seção 2.8). `useMetasQuery` (Central Financeira, já
existente) e o novo `useMetas` (CRUD) continuam sendo coisas **diferentes** — mesmo par já
estabelecido para `contas`/`dashboard.contas` e `cartoes`/`dashboard.cartoes`: um lê do
endpoint agregador (usado só pelo `MetasCard`), o outro do CRUD real (usado pela página
`/metas`, que precisa listar inclusive as desativadas quando o filtro pedir).

## 3. UX — a área de Metas como experiência, não como formulário

### 3.1 O que cada card precisa comunicar, de relance

Progresso, valor atual, valor objetivo, percentual, tempo restante, situação e "velocidade
para atingir" (pedido explícito do usuário) — nessa ordem de prioridade visual:

1. **Progresso** é a informação dominante — ocupa a maior área do card, não compete com
   texto pequeno ao lado.
2. **Valor atual / valor objetivo** — sempre os dois juntos, nunca só o percentual sozinho
   (ex. "R$ 4.200 de R$ 15.000"), porque um número relativo sem a régua absoluta ao lado
   comunica menos do que os dois juntos.
3. **Percentual** — reforça o progresso visual com um número exato, formatado com
   `AnimatedNumber format="percent"` (count-up na primeira carga real, nunca ao revisitar
   com dado em cache — motion-principles.md, seção 6.1).
4. **Tempo restante** — só quando `data_alvo` existe; formatado como "faltam N dias"/"vence em
   N meses" em vez da data crua, mais fácil de processar de relance (a data completa continua
   disponível ao abrir o card).
5. **Situação** — um `Badge` compacto (seção 2.6: Concluída/Em andamento/Atrasada/Sem prazo),
   tone semântico, nunca cor sem texto.
6. **Velocidade para atingir** — a peça nova que nenhuma outra entidade deste projeto expõe.
   Calculada 100% client-side a partir de dado já existente (não é uma nova métrica de
   backend, é aritmética de apresentação sobre `valor_acumulado`/`data_alvo`/`created_at`):
   ritmo médio de aporte desde a criação da meta (`valor_acumulado / dias_desde_criacao`) e,
   quando há `data_alvo`, o ritmo que ainda seria necessário para chegar lá a tempo
   (`valor_restante / dias_restantes`). Exibido como uma frase curta, não como um número
   isolado — ex. "Nesse ritmo, você bate a meta em ~3 meses" (ritmo atual projetado) ou "Faltam
   R$ 850/mês para chegar no prazo" (quando o ritmo atual for insuficiente). Sem prazo
   definido, só a primeira frase aparece. Esse cálculo é claramente diferente de
   `valor_acumulado`/`percentual` (esses continuam vindo prontos do backend) — é uma projeção
   de UX sobre um valor já dado, o equivalente a `preverStatusPosPagamento` de Fatura (preview
   client-side não-autoritativo, nunca persistido, só para orientar o usuário).

### 3.2 Tom "inspirador" sem quebrar a filosofia "confiança silenciosa"

O pedido do usuário por uma experiência "premium" e "inspiradora" precisa conviver com o
princípio fundamental do design-system (seção 1: "confiança silenciosa", nunca
"comemoração" — motion-principles.md, seção 5.7, reforça a mesma regra para o caso de
sucesso). A forma de resolver essa tensão sem introduzir confete/gamificação (fora de tom
para um app financeiro sério) é: **inspiração vem da clareza e da linguagem, não de efeito
visual chamativo**. Concretamente:
- Frases orientadas a ação/progresso reais ("faltam R$ 850/mês", "você já guardou 42%"), não
  elogios genéricos vazios.
- Quando uma Meta é concluída (`percentual` cruza 100% pela primeira vez, visto em tempo
  real pelo usuário — mesma condição de "anima só a transição presenciada" de
  motion-principles.md seção 6.3), o `Badge` de situação faz crossfade para "Concluída" com
  o mesmo tratamento de qualquer outra transição de status do projeto — **sem** confete,
  sem modal de celebração, sem som. O "momento" é comunicado por ser a única transição de
  Badge que troca para `tone="positive"` combinada com o preenchimento do `ProgressBar`
  atingindo o teto — suficiente para ser sentido como uma conquista sem quebrar o tom do
  resto do produto.
- Nenhuma automação/notificação é implementada (fora de escopo, confirmado em
  `docs/analise-arquitetural-meta.md`) — a "inspiração" vive inteiramente na tela, não em
  um push/e-mail.

### 3.3 Formulário

`MetaFormDialog` segue a receita padrão de todo formulário do projeto (design-system.md,
seção 17): coluna única, `FormDialog` sempre (nunca inline), validação `onBlur`,
`SubmitButton`/`CancelButton` fixos no rodapé. Nenhuma peça nova de formulário é necessária —
`TextField`, `CurrencyField`, `DateField` e `AccountSelect` já existem e já cobrem os 4 campos
de `MetaCreate`/`MetaUpdate`.

## 4. VISUAL — por que Cards (não tabela, não apenas uma barra)

Avaliando as opções levantadas pelo pedido:

- **Tabela (`DataTable`)** — descartada. Mesma decisão já tomada para Cartão/Financiamento/
  Empréstimo: volume baixo por usuário, e uma Meta tem densidade de informação (progresso +
  prazo + situação + velocidade) demais para uma linha de tabela sem comprimir tudo em texto
  minúsculo. Uma tabela também entra em conflito direto com o pedido de "não apenas um CRUD,
  quero que seja inspiradora" — tabelas comunicam "registro administrativo", não "objetivo
  pessoal".
- **Progress Ring (circular)** — considerada e descartada como elemento **principal**. Um
  anel de progresso comunica bem uma métrica isolada (é ótimo em um relógio/app de saúde),
  mas aqui a Meta precisa mostrar SIMULTANEAMENTE valor atual, valor alvo, prazo e
  velocidade — encaixar tudo isso dentro/ao redor de um círculo pequeno either soterra
  informação em texto minúsculo ao redor do anel, ou força um card gigante só para caber. A
  barra linear (`ProgressBar` já existente) comunica a mesma proporção com muito mais espaço
  sobrando ao lado para o resto dos números — e já é o componente que o design-system
  explicitamente reserva para isso (seção 14: "usada... em barra de progresso de Meta").
  **Decisão：sem anel como elemento principal.**
- **Timeline** — poderosa para "histórico de aportes ao longo do tempo" (um gráfico de área
  cumulativo mostrando o crescimento do `valor_acumulado` mês a mês), mas isso exigiria uma
  série histórica que **não existe no backend** (`docs/analise-arquitetural-meta.md` confirma
  explicitamente: "sem tabela de snapshot temporal — o progresso é sempre o valor 'ao vivo'").
  Reconstruir essa série a partir de transações individuais no cliente seria possível
  (agrupar `Transacao` por `meta_id` e por mês), mas é claramente fora do escopo desta etapa
  (o pedido fala em "progresso, prazo, velocidade" — não em "histórico visual"). Registrado
  como ideia futura genuína (seção 8), não implementada agora.
- **Cards com barra de progresso + badges + motion** — a escolha. Um `Card` por Meta,
  reaproveitando a composição já validada em `CartaoResumoCard`/`FinanciamentosPage`: card
  inteiro clicável (`role="link"`, mesmo padrão de acessibilidade), `ProgressBar` como
  elemento visual dominante, `AnimatedNumber` para os valores monetários e percentual,
  `Badge`/`FinancialBadge`-like para a situação, ação bar com Editar/Desativar-Reativar no
  rodapé (mesmo componente `CartaoActionBar`, adaptado — ou um novo `MetaActionBar` que segue
  a mesma receita).

### 4.1 Composição do `MetaResumoCard` (novo componente)

De cima para baixo (ordem de leitura, storytelling):

1. Ícone `Target` + `descricao` (título) + `Badge` de situação no canto (crossfade quando
   muda em tempo real).
2. `AnimatedNumber` grande (`text-h2`, mesmo peso visual do "Disponível" de
   `CartaoResumoCard`) para `valor_acumulado`, com "de `valor_alvo`" ao lado em peso menor.
3. `ProgressBar` (`tone` reagindo via `tonePorUtilizacao(percentual)` — `positive` até 80%,
   `warning` 80-100%, e quando ultrapassa 100% um tratamento visual distinto, ex. tone
   `positive` mantido mas o texto do percentual em destaque, já que superar uma Meta é sempre
   bom, diferente de estourar o limite de um Cartão).
4. Linha de "tempo restante" + "velocidade para atingir" (seção 3.1, itens 4 e 6) — texto
   secundário, tom sóbrio.
5. `MetaActionBar` (Editar / Desativar ou Reativar) — mesmo rodapé de toda entidade.

### 4.2 Motion aplicado (motion-principles.md, sem inventar nenhum token novo)

- Grid de cards: `stagger` de entrada só na primeira carga real dos dados (seção 5.8/9 do
  motion-principles), respeitando o orçamento de 8-10 itens — acima disso, fade único.
- `ProgressBar`: já usa spring `gentle` nativamente (seção 4.3) — nenhuma mudança necessária.
- `AnimatedNumber` (valor acumulado, percentual): já implementa count-up-uma-vez +
  interpolação direta em mudanças (seção 6.1/6.2), reaproveitado sem alteração.
- Badge de situação: crossfade `--duration-moderate` só quando a mudança acontece em tempo
  real na sessão do usuário (seção 6.3) — nunca anima o estado inicial de uma tela recém-
  aberta.
- Card inteiro: `whileHover` já embutido no componente `Card` (elevação 2px) — nenhuma
  customização nova.

## 5. RESPONSIVIDADE

Grid de cards responsivo, mesma grade já usada por `FinanciamentosPage`/`CartoesPage`:
`grid-cols-1` (mobile) → `md:grid-cols-2` (tablet) → `xl:grid-cols-3` (desktop), sem nenhuma
mudança de conteúdo entre breakpoints — diferente de tabela (que precisaria reformatar para
lista de cards abaixo de `md`, design-system.md seção 24), o card já É o formato de exibição
em qualquer largura, então não há transformação nenhuma a fazer. O texto de "velocidade para
atingir" (a linha mais longa do card) quebra em duas linhas normalmente em telas estreitas —
sem truncamento, porque é justamente a informação mais "inspiradora" do card, não deveria
sumir cortada. `MetaFormDialog` é um `FormDialog` comum, que já lida com mobile (tela cheia
abaixo de `md`, mesmo padrão de todo formulário do projeto).

## 6. Página `/metas`

Estrutura igual a `FinanciamentosPage.tsx`: header com título + botão "Nova meta"; controle
"Mostrar desativadas" (`Switch`); seletor de ordenação (seção 2.5); grid de
`MetaResumoCard`; `EmptyState` (ícone `Target`, "Nenhuma meta ainda", CTA "Criar meta") quando
vazio; `MetaFormDialog` para criar/editar. Registrada em `routes/AppRoutes.tsx`
(`React.lazy`, mesmo padrão de code-splitting por rota) e em `NAV_ITEMS`
(`components/layout/navItems.ts`) com ícone `Target` (ainda não usado por nenhum outro item
do menu).

## 7. Resumo das decisões arquiteturais

1. **Nenhuma regra de negócio do backend é questionada** — `valor_acumulado`/`percentual`
   continuam sendo lidos prontos, nunca recalculados; `conta_id` continua sendo puramente
   organizacional.
2. **Grid de `MetaResumoCard`, não `DataTable`** — mesmo raciocínio de volume baixo já usado
   para Cartão/Financiamento/Empréstimo; card clicável com Editar/Desativar/Reativar.
3. **`ProgressBar` linear como peça visual central, não Progress Ring** — mais espaço para
   comunicar as 7 informações pedidas simultaneamente; Ring rejeitado por comprimir demais.
4. **Timeline/histórico de progresso explicitamente fora de escopo** — não existe dado de
   série temporal no backend; ideia registrada para uma etapa futura dedicada, não implícita
   nesta.
5. **"Velocidade para atingir" é uma projeção 100% client-side sobre dado já existente** —
   nunca substitui nem reproduz `valor_acumulado`/`percentual`, é uma camada de UX adicional
   (mesmo espírito do preview não-autoritativo de pagamento de Fatura).
6. **Tom "inspirador" via linguagem e clareza, não via celebração/gamificação** — sem
   confete, sem modal de conquista; a transição de Badge para "Concluída" é o único momento
   de destaque, tratado com o mesmo rigor de motion de qualquer outra transição de status do
   projeto.
7. **`MetaSelect` em `TransacaoFormDialog` é parte obrigatória desta etapa, não um extra** —
   sem esse campo, nenhuma Meta jamais acumularia progresso de verdade. Some no modo
   Parcelado (mesmo tratamento de `TagMultiSelect`).
8. **Só soft delete (`ativo=false`) — sem exclusão definitiva de Meta nesta etapa**, por não
   ter sido implementada no backend e por essa não ser, a princípio, a decisão recomendada
   dado o caráter de "histórico financeiro pessoal" de uma Meta.
9. **Três queryKeys/hooks novos (`metas.all/list/detail`), mutations invalidando
   `dashboard.metas`/`dashboard.indicadores`/`dashboard.calendario`** — mesmo padrão de toda
   entidade anterior integrada à Central Financeira.
10. **`MetasCard` do Dashboard ganha navegação para `/metas`** — fechando a lacuna já
    documentada no próprio componente desde que foi escrito.

## 8. O que depende da sua aprovação antes de qualquer código ser escrito

- **Confirmar que `MetaSelect` em `TransacaoFormDialog` entra no escopo desta etapa** (item 7
  do resumo) — é tecnicamente uma mudança em Transação, não em Meta, mas sem ela a tela de
  Metas fica sem função real. Alternativa, se preferir separar: implementar o CRUD de Meta
  agora e o campo em Transação como um adendo imediatamente em seguida (duas entregas, mesma
  etapa).
- **Confirmar "só soft delete" para Meta** (item 8) — ou pedir que a exclusão definitiva
  (hard delete, com o mesmo cuidado de verificar transações vinculadas já aplicado a
  Cartão/Conta/Categoria/Tag/Fatura) seja adicionada ao backend como parte desta etapa.
- **Validar a fórmula de "velocidade para atingir"** (seção 3.1, item 6) — a proposta é
  `valor_acumulado / dias_desde_criacao` (ritmo atual) e, quando há prazo,
  `valor_restante / dias_restantes` (ritmo necessário). Se preferir outra forma de calcular
  ou comunicar essa métrica, é o momento de ajustar antes de implementar.
- **Validar a decisão de não implementar Timeline/histórico de progresso** — confirmando que
  fica como ideia futura, fora desta etapa.
- **Validar o critério de ordenação padrão** ("mais urgente primeiro") e se as 3 opções
  propostas (urgência/progresso/nome) bastam, ou se falta algum critério.
- **Validar o texto/tom exato das frases "inspiradoras"** (seção 3.1/3.2) — os exemplos dados
  são ilustrativos; a redação final pode ser ajustada com você antes de virar código.
- **Confirmar o ícone `Target` para o item de menu `/metas`** e o rótulo exato ("Metas").

Nenhum código foi escrito para esta etapa. Após sua validação dos pontos acima, a
implementação segue a ordem: (1) backend, apenas se a exclusão definitiva for aprovada; (2)
camada de dados de Meta (types/schemas/services/hooks/queryKeys); (3) `MetaSelect` +
mudanças em `TransacaoFormDialog`/`schemas/transacao.ts`; (4) `MetaResumoCard` +
`MetaActionBar` + `MetaFormDialog`; (5) página `/metas` + rota + item de menu; (6)
`MetasCard` do Dashboard ganha navegação; (7) validação final (tsc, build, testes,
responsividade, docs/README/dashboard).
