# Sprint de Refinamento Premium — Análise Arquitetural

Este documento consolida as decisões de arquitetura da "Sprint de Refinamento
Premium" (pedido de 18 frentes, 2026-07): correções de bugs, ajustes de
UX/UI, consistência visual e preparação de arquitetura para crescimento
futuro. Constraints explícitas do pedido, válidas para toda a sprint: não
criar novas regras de negócio, respeitar a arquitetura existente, não
duplicar regras de negócio, não implementar lógica paralela ao backend, e
documentar antes de implementar qualquer mudança que dependa de alteração
no backend.

Dado o tamanho da sprint, a execução acontece em etapas dentro da mesma
sprint — este documento é atualizado a cada etapa concluída. As seções
abaixo cobrem o que já foi decidido e implementado; o restante (dashboard
executivo, personalização, Command Palette, Central de Atividades, etc.)
tem sua análise e decisão registradas aqui **antes** da implementação,
conforme pedido.

## 1. Cartão — "Estado Inicial do Cartão" (saldo já utilizado)

### Situação encontrada

Investigação (ver histórico de tarefas #161/#165) mostrou que o mecanismo
de "informar saldo já utilizado" existente (`AjusteSaldoInicialDialog` +
`Fatura.ajuste_manual`, `PATCH /faturas/{id}/ajuste-manual`) funcionava
corretamente em termos de cálculo, mas tinha um efeito colateral confuso:
quando o cartão ainda não tinha nenhuma Fatura ABERTA (o caso normal de um
cartão recém-criado), o próprio diálogo criava uma `Fatura` do mês corrente
só para ter onde gravar o `ajuste_manual`. Do ponto de vista do usuário,
ele só queria dizer "já tenho R$X gasto neste cartão" e o sistema criava
silenciosamente uma fatura — exatamente a reclamação relatada.

### Decisão

Criado o conceito de **"Estado Inicial do Cartão"**: um novo campo
`Cartao.saldo_inicial_utilizado` (Numeric(12,2), default 0), independente
de qualquer Fatura ou Transacao. Consome `limite_disponivel` permanentemente
até o usuário editar/zerar - não tem ciclo, não fecha, não é pago.

- **Backend**: migração `a1b2c3d4e5f6` adiciona a coluna; `CartaoCreate`/
  `CartaoUpdate`/`CartaoRead` expõem o campo; `CartaoService._com_limite_disponivel`
  subtrai `cartao.saldo_inicial_utilizado` do limite, além dos gastos não
  pagos já calculados.
- **Frontend**: `CartaoFormDialog` ganha um campo opcional "Saldo já
  utilizado" **só no modo de criação** (`CurrencyField`, escondido em
  edição — evitar dois lugares editando o mesmo valor). Depois de criado,
  o valor é editado via o botão "Informar saldo já utilizado" já existente
  em `CartaoDetalhePage`.
- **`AjusteSaldoInicialDialog`** foi redesenhado para ter dois modos,
  dependendo se existe uma Fatura ABERTA:
  - **Sem fatura aberta** (caso comum pós-criação): edita
    `Cartao.saldo_inicial_utilizado` direto via `PATCH /cartoes/{id}` —
    nenhuma Fatura é criada.
  - **Com fatura aberta**: comportamento de sempre, edita
    `Fatura.ajuste_manual` daquele ciclo específico (uso legítimo e
    diferente: ajustar o saldo do ciclo corrente, não mais usado como
    mecanismo de onboarding).

Essa decisão não duplica regra de negóco: `ajuste_manual` continua
existindo e com o mesmo significado de sempre (declarar saldo de um ciclo
ABERTO especificamente); `saldo_inicial_utilizado` é um conceito novo e
distinto (nível Cartão, não nível Fatura), cada um resolvendo um problema
diferente.

### Testes

Cobertura via testes de integração existentes de Cartão/Fatura (todos
passando); o cálculo de `limite_disponivel` com `saldo_inicial_utilizado`
é exercitado pelos testes unitários de `CartaoService`.

### Revisão independente (pós-implementação)

Antes de prosseguir para as próximas frentes, esta etapa passou por uma
revisão crítica independente (agente dedicado, sem contexto da implementação).
Achado real: `CartaoFormDialog` enviava `saldo_inicial_utilizado: "0"` em
**todo** PATCH de edição (nome, limite, dia de fechamento etc.), porque o
payload sempre incluía a chave mesmo com o campo escondido no formulário de
edição — isso resetava silenciosamente o "Estado Inicial do Cartão" já
declarado toda vez que o usuário editava qualquer outro dado do cartão.
Corrigido removendo `saldo_inicial_utilizado` do payload antes do PATCH de
edição (`CartaoFormDialog.onSubmit`) — o campo só é enviado na criação;
depois de criado, só muda via `AjusteSaldoInicialDialog`. Revalidado com
`tsc -b`, `vite build` e a suíte de testes de Cartão/Fatura, todos verdes.

Ressalva registrada (não bloqueante): `FaturaService.ids_faturas_pagas`
roda uma query por fatura do cartão (via `_com_valores_calculados`), o que
introduz um N+1 real em `CartaoService.listar()`. Aceitável para o volume
atual de dados de um usuário único; registrado como dívida técnica para
revisar se a listagem de Cartões ficar perceptivelmente lenta.

## 2. Bug: limite disponível não volta ao pagar fatura

### Causa raiz

`CartaoRepository.somar_gastos_nao_pagos` comparava `Fatura.status` (coluna
persistida) com `StatusFatura.PAGA` para decidir se uma fatura já estava
quitada. Só que, por design documentado em `StatusFatura` (ver
`app/models/enums.py`), a coluna `status` **nunca** grava `PAGA` de
verdade — só `ABERTA`/`FECHADA` são valores reais persistidos; `PAGA`,
`PARCIALMENTE_PAGA` e `ATRASADA` são sempre **derivados** em runtime por
`FaturaService._derivar_status` a partir de `valor_pago`/`valor_total`, e
`FaturaService.registrar_pagamento` nunca escreve na coluna `status`.

Consequência: a condição `Fatura.status != StatusFatura.PAGA` era **sempre
verdadeira** para qualquer fatura real, então `somar_gastos_nao_pagos` nunca
excluía as transações de uma fatura já paga — `limite_disponivel` nunca se
recuperava depois de um pagamento real via `POST /faturas/{id}/pagamentos`.

Um teste de integração existente (`test_limite_disponivel_ignora_despesas_de_fatura_ja_paga`)
passava porque forçava `Fatura.status = PAGA` diretamente no banco via
`db_session`, um estado que o fluxo real da aplicação nunca produz — o
teste mascarava o bug.

### Correção (sem duplicar regra de negócio)

`FaturaService.ids_faturas_pagas(cartao_id)` é a nova e única fonte de
verdade sobre "quais faturas deste cartão estão pagas" — reusa
`_com_valores_calculados`/`_derivar_status` (o mesmo cálculo já usado em
toda leitura de Fatura), nunca duplica a fórmula. `CartaoService` passou a
depender de `FaturaService` (constructor injection, `deps.py` reordenado)
e repassa esse conjunto de ids para `CartaoRepository.somar_gastos_nao_pagos`,
que agora só executa a query com o conjunto já resolvido — a regra "o que
conta como pago" mora inteiramente em `FaturaService`, a Repository de
Cartão só faz a soma.

O teste de integração mascarado foi reescrito para passar pelo fluxo real
(criar fatura → lançar despesa → fechar → `POST /pagamentos` com valor
total → conferir que o limite voltou), e passa a detectar o bug real caso
reapareça. Adicionados 5 testes unitários novos em `test_fatura_service.py`
cobrindo `ids_faturas_pagas` (fatura aberta, fechada sem pagamento, paga
totalmente, paga parcialmente, isolamento entre cartões).

### Validação

- 543 testes unitários passando (5 novos).
- Suíte de integração completa passando (rodada em chunks por causa do
  timeout do ambiente de execução: `test_cartao_flow.py`, `test_fatura_flow.py`
  e as demais 18 suítes, todas verdes).
- `tsc -b` limpo, `vite build` bem-sucedido.
- Migração `a1b2c3d4e5f6` testada em banco SQLite limpo (upgrade head
  aplica sem erro, coluna criada com `default '0'`).

## 3-18. Demais frentes da sprint (dashboard, calendário, categorias,
command palette, central de atividades, personalização, auditoria final)

Dado o tamanho e a heterogeneidade destas frentes — cada uma delas é, por
si só, uma etapa de trabalho comparável às demais etapas já concluídas
neste projeto (ex.: "Revisão completa do Dashboard", "Dashboard
personalizável", "Command Palette") — elas serão executadas em etapas
subsequentes desta mesma sprint, na ordem sugerida abaixo, cada uma com
sua própria investigação → decisão → implementação → testes → validação,
seguindo o mesmo processo já usado em toda a Sprint até aqui.

Decisões preliminares já tomadas (para orientar as próximas etapas, sem
implementar nada disso ainda):

- **Dashboard de Cartões (item 3)** e **revisão geral do Dashboard (itens
  6-14)**: nenhuma nova regra de negócio - tudo consome dados já expostos
  por `CentralFinanceiraService`/`CartaoService`/`FaturaService` etc. Exige
  investigar a estrutura atual antes (tarefa já planejada).
- **Categorias padrão deletáveis por usuário (item 4)**: provavelmente
  precisa de um campo por-usuário (ex.: tabela de "categorias ocultas/
  excluídas pelo usuário" ou um novo campo em Categoria) para não apagar a
  categoria globalmente - isso é uma mudança de schema/backend e será
  documentada em detalhe (com o desenho de tabela/migração) antes de
  implementar, conforme exigido.
- **Calendário (item 5)**: ocultar parcelas individuais é só um filtro na
  camada de apresentação (`CalendarioFinanceiroRead`/frontend) - parcelas
  continuam existindo normalmente, só não aparecem como evento individual
  no grid do calendário. Não deve exigir mudança de schema.
- **Dashboard personalizável (item 15)**: a persistência de layout
  (ordem/visibilidade dos cards) começará em `localStorage` (mesmo padrão
  já usado em `lib/cardThemes.ts` para preferências puramente visuais),
  com o formato de dado já desenhado para migrar para o backend depois
  (um endpoint de preferências de usuário), sem implementar essa migração
  agora - documentado em detalhe na etapa correspondente antes da
  implementação.
- **Command Palette (item 16)** e **Central de Atividades (item 17)**:
  arquitetura de busca/índice e de feed cronológico será desenhada para
  aceitar novos tipos de resultado/evento no futuro (Alertas, Contas
  Recorrentes, etc.) sem implementar esses tipos agora - só a extensão
  pontual pedida.
- **Auditoria final de experiência premium (item 18)**: última etapa,
  depois de todo o resto implementado.

Cada uma dessas frentes será marcada como concluída neste documento
conforme for implementada, com sua própria seção de decisão detalhada, no
mesmo padrão das seções 1 e 2 acima.

## 4. Categorias padrão: exclusão por usuário (item 4)

### Situação encontrada

Categoria de sistema (`usuario_id IS NULL`) é **uma única linha global,
compartilhada por todos os usuários** — não existe cópia por usuário.
`CategoriaService._buscar_editavel` já bloqueia com `AcessoNegadoError`
qualquer tentativa de `desativar()`/`excluir()` uma categoria de sistema,
para qualquer usuário — hoje é tudo ou nada. Não existe nenhuma tabela de
associação usuário↔categoria; o único precedente de "ocultar uma entidade"
é `Conta.oculta` (usado pelo cofrinho de Meta), mas é um campo na própria
linha — inaplicável aqui, porque a linha de sistema é compartilhada e um
`oculta=True` afetaria todo mundo, não só quem pediu.

### Decisão

Nova tabela de associação por usuário — `CategoriaOcultaUsuario`
(`categorias_ocultas_usuario`): `id`, `usuario_id` (FK CASCADE),
`categoria_id` (FK CASCADE), `criado_em`, `UniqueConstraint(usuario_id,
categoria_id)`. Não é uma "exclusão" real — a linha de `Categoria`
permanece intocada para todos os outros usuários; só grava/apaga uma
entrada nesta tabela nova. Nenhuma regra de negócio já existente é
duplicada: `desativar()`/`excluir()` continuam bloqueando 100% para
sistema (nada muda ali); esta é uma **quarta operação, nova e distinta**
(`ocultar_para_usuario`/`reexibir_para_usuario`), que nunca toca a linha
da `Categoria`.

- **Repository**: `esta_oculta_para_usuario`, `ocultar_para_usuario`,
  `reexibir_para_usuario` (idempotentes), `existe_transacao_vinculada_do_usuario`
  (mesmo espírito de `existe_transacao_vinculada`, mas filtrado por
  `Transacao.usuario_id` — `Transacao` já tem esse campo direto).
  `listar_visiveis_do_usuario` ganha `incluir_ocultas: bool = False`: por
  padrão exclui via `NOT EXISTS` contra a tabela nova (a categoria
  "desaparece" da listagem normal do usuário que a ocultou, sem
  desaparecer para ninguém mais); com `incluir_ocultas=True`, devolve tudo
  (usado pela visão "Categorias ocultas" no frontend, para reexibir).
- **Service**: `ocultar_para_usuario(categoria_id, usuario_id)` só permite
  em categoria de sistema (`categoria.usuario_id is None`) — categoria
  própria do usuário já tem `desativar()`/`excluir()` normais, não precisa
  deste mecanismo. Bloqueia com `BusinessRuleError` se o usuário já possui
  transação vinculada a esta categoria (mesmo racional de
  `excluir()` bloquear com transação vinculada — mas aqui escopado ao
  próprio usuário, já que é uma ação por-usuário). `reexibir_para_usuario`
  não tem restrição (sempre idempotente).
- **Schema**: `CategoriaRead` ganha `oculta_para_mim: bool` — diferente de
  `e_do_sistema` (deriva de `usuario_id`, já carregado), este campo
  precisa de uma consulta extra por usuário, então segue o padrão de
  `Conta.saldo_atual`: computado pelo Service, anexado como atributo
  transiente no objeto ORM antes da validação do schema (não um
  `@computed_field`, que só leria colunas já carregadas).
- **Rotas novas**: `DELETE /categorias/{id}/ocultar`,
  `POST /categorias/{id}/reexibir`; `GET /categorias` ganha querystring
  `incluir_ocultas`.
- **Frontend**: nova `RowAction` "Ocultar para mim" (visível só quando
  `e_do_sistema && !oculta_para_mim`) e "Reexibir" (visível quando
  `oculta_para_mim`), reaproveitando o padrão de `RowAction`/`ConfirmAction`
  já usado pelas demais ações da página. Um toggle "Mostrar categorias
  ocultas" liga `incluir_ocultas=true` para o usuário encontrar e reexibir
  o que ocultou.

Nenhuma migração de dado é necessária além da criação da tabela (ela
começa vazia para todos os usuários).

### Implementado

Todo o plano acima foi executado:

- Migração `b2c3d4e5f6a7` (tabela `categorias_ocultas_usuario`, testada em
  banco SQLite limpo) + model `CategoriaOcultaUsuario`.
- `CategoriaRepository`: `esta_oculta_para_usuario`/`ocultar_para_usuario`/
  `reexibir_para_usuario` (idempotentes) + `existe_transacao_vinculada_do_usuario`
  + `listar_visiveis_do_usuario(..., incluir_ocultas=False)`.
- `CategoriaService.ocultar_para_usuario`/`reexibir_para_usuario` + `_anexar_oculta_para_mim`
  (atributo transiente, mesmo padrão de `Conta.saldo_atual`).
- Rotas `DELETE /categorias/{id}/ocultar`, `POST /categorias/{id}/reexibir`,
  `GET /categorias?incluir_ocultas=`.
- Frontend: `CategoriasPage` ganha as ações "Ocultar para mim"/"Reexibir"
  (visíveis só para categoria de sistema) e o toggle "Mostrar categorias
  ocultas por você"; `categoriaTableColumns` mostra um badge "Oculta para
  você" quando aplicável.
- Testes: 9 unitários novos (`CategoriaService`) + 9 de integração novos
  (fluxo completo via API, incluindo isolamento entre usuários e bloqueio
  por transação vinculada) - 552 unit + integração completa (392 testes)
  passando.
- Validação: `tsc -b` e `vite build` limpos.

## 5. Calendário: ocultar parcelas individuais, manter eventos agregados (item 5)

### Situação encontrada

`CentralFinanceiraService.calendario_financeiro` monta `EventoCalendario`
a partir de 4 fontes (Transação, Fatura, Transferência, Meta) - uma
parcela de Parcelamento chega pelo bloco genérico de Transação,
classificada só por `origem_tipo = PARCELAMENTO` (não existe categoria
própria de exibição para ela, cai em `DESPESA` como qualquer outra).
`ParcelamentoService` gera uma `Transacao` por parcela, uma por mês - ou
seja, um único Parcelamento contribui no máximo 1 evento por mês
consultado. A "poluição" citada pelo usuário acontece quando 2+
Parcelamentos DIFERENTES têm parcela vencendo no mesmo dia: cada um vira
uma linha individual e indistinguível de uma despesa avulsa no
`EventoDiaDrawer` (que hoje não agrupa nada, `eventos.map(...)` plano).

### Decisão

Confirmado que dá para resolver 100% na camada de apresentação, sem tocar
backend/schema: `EventoCalendario.origem_id` já é o `parcelamento_id`
(estável, nunca colide entre parcelamentos diferentes), suficiente para
agrupar. Implementado em `EventoDiaDrawer.tsx`: quando um dia tem 2+
eventos com `origem_tipo === "PARCELAMENTO"`, eles somem da lista "achatada"
individual e viram um único cartão consolidado (`GrupoParcelas`) mostrando
a contagem e o valor total, recolhido por padrão - um clique expande e
revela cada parcela individualmente (nada é perdido, só não aparece já
expandido). Um único evento de parcelamento no dia continua aparecendo
normal (não há o que consolidar). `CalendarioMensal` (grid mensal) já
agrupava os "dots" por `categoria`, não por evento - nenhuma mudança
necessária ali (uma parcela de Parcelamento já cai como mais um `DESPESA`,
sem proliferar pontos).

Validação: `tsc -b` e `vite build` limpos. Sem mudança de backend, sem
teste de backend novo (comportamento puramente de apresentação).

## 15. Dashboard personalizável (item 15)

### Decisão

Sem backend/dependência nova: reordenar e ocultar/exibir os 6 cards do
Bento Grid (`Contas/Cartões/Faturas/Financiamentos/Empréstimos/Metas`) +
`HojeCard` é uma preferência puramente client-side, persistida em
`localStorage` (mesmo padrão já usado por `lib/cardThemes.ts` e pelos
colapsados de `CategoriasPage`), com o formato de dado já desenhado para
migrar para um endpoint de preferências de usuário no futuro (`{ ordem:
string[], ocultos: string[] }`, chaveado por id estável de card) — essa
migração para o backend NÃO é implementada agora.

Drag-and-drop implementado sem biblioteca nova (native HTML5 Drag and
Drop API - `draggable`/`onDragStart`/`onDragOver`/`onDrop`) para não
adicionar peso de bundle a uma preferência puramente cosmética; a mesma
lista também expõe toggles de mostrar/ocultar e um botão "Restaurar
padrão". `IndicadoresStrip`/`ResumoFinanceiroSection`/`AgendaFinanceiraCard`
ficam FORA da personalização (são estruturais, sempre no topo/rodapé,
mesmo raciocínio de nunca remover a visão geral por completo).

### Implementado

- `frontend/src/lib/dashboardLayout.ts`: registro dos cards
  personalizáveis (id estável + label) e `carregarLayoutDashboard`/
  `salvarLayoutDashboard` (localStorage, tolerante a JSON inválido/ids
  desconhecidos — nunca quebra a tela, sempre cai de volta pro padrão).
- `frontend/src/components/domain/dashboard/DashboardCustomizeDrawer.tsx`:
  Drawer (mesmo componente de overlay tier 2 já usado em Fatura/Financiamento)
  com lista arrastável (handle de grip) + `Switch` por card + "Restaurar
  padrão".
- `DashboardPage.tsx`: renderiza os cards dinamicamente a partir do
  layout salvo (`ORDEM_PADRAO.filter(...)`) em vez de uma lista fixa de
  JSX; botão "Personalizar" no header abre o Drawer.

Validação: `tsc -b` e `vite build` limpos.

## 16. Command Palette (item 16)

### Decisão

Reaproveita 100% `NAV_ITEMS` (`components/layout/navItems.ts`, já
compartilhado por `Sidebar`/`MobileNav`) como índice inicial de resultados
— nenhuma lista nova de rotas duplicada. Desenhado com um discriminador
`tipo` no resultado (`ResultadoComando`, hoje só `"navegacao"`) para
aceitar tipos novos no futuro (ex.: `"acao"` para "Nova transação",
`"entidade"` para pular direto para uma Conta/Cartão específico) sem
refatoração — só a extensão pontual pedida (navegação) é implementada
agora.

- Atalho global `Ctrl+K`/`Cmd+K` (Mac) abre um modal centralizado
  (reaproveita `modalBackdrop`/`modalPanel` de `lib/motion.ts`, mesmo
  padrão visual de `FormDialog`) com campo de busca + lista filtrada.
  Filtro por substring (mesma lógica simples já usada em
  `DataTable`/pickers), destacando o trecho encontrado com
  `utils/highlight.tsx` (reuso, não duplicação).
  Navegação por teclado: `↑`/`↓` move a seleção, `Enter` navega,
  `Esc` fecha.
- Montado uma única vez em `AppLayout` (disponível em toda rota
  autenticada); o listener de `keydown` ignora o atalho quando o foco já
  está num campo de texto/textarea (não interfere na digitação).

### Implementado

- `frontend/src/lib/commandPalette.ts`: `ResultadoComando` + `RESULTADOS_NAVEGACAO`
  (derivado de `NAV_ITEMS`).
- `frontend/src/components/layout/CommandPalette.tsx`: modal + atalho
  global + navegação por teclado.
- `AppLayout.tsx`: monta `<CommandPalette />`.

Validação: `tsc -b` e `vite build` limpos.

## 17. Central de Atividades (item 17)

### Situação encontrada

Não existe hoje nenhuma trilha de auditoria/log de atividades no projeto -
só `criado_em`/`atualizado_em` (via `TimestampMixin`) em cada entidade.
Um feed cronológico "o que aconteceu recentemente" pode ser montado sem
nenhuma tabela nova, combinando leituras que os Services de domínio já
expõem: `TransacaoService.listar`/`TransferenciaService.listar` (ordenados
por `data` desc) e `MetaService.listar` filtrando `concluida_em` não nulo.

### Decisão

Novo método `CentralFinanceiraService.atividades_recentes(usuario_id,
limit)`: busca até `limit` transações + transferências + metas concluídas
recentes (cada uma via o Service de domínio já existente, nenhuma query
nova em Repository), converte cada uma num `AtividadeRecente` (schema novo,
só leitura: `data_hora`, `descricao`, `valor`, `origem_tipo`, `origem_id`)
e ordena o conjunto combinado por `data_hora` desc em Python (regra 3 do
service: combinação sobre listas já pequenas e limitadas, nunca uma
agregação nova sobre a tabela inteira). Discriminador `origem_tipo`
reaproveita `TipoEntidadeReferenciavel` (mesmo enum de
`EventoCalendario`) - zero tipo novo. Arquitetura desenhada para aceitar
fontes novas no futuro (Alertas, Contas Recorrentes) só adicionando mais
uma chamada a um Service já existente e mais um `if`/`for` no método -
nenhuma delas implementada agora (só a extensão pontual pedida: Transação,
Transferência, Meta concluída).

Nova rota `GET /central-financeira/atividades`. Frontend: Drawer aberto a
partir de um botão no `Header` (ícone de relógio/atividade, disponível em
qualquer rota, mesmo padrão de "central de notificações" já comum em
produtos parecidos), reaproveitando `ICONE_POR_ORIGEM`/`ROTA_POR_ORIGEM`
de `origemNavegacao.ts` para ícone/link de cada item, igual ao Calendário
e à Agenda do Dashboard.

### Implementado

- `AtividadeRecente`/`CentralAtividadesRead` (schemas) +
  `CentralFinanceiraService.atividades_recentes` + rota
  `GET /central-financeira/atividades`.
- Testes de integração cobrindo ordenação cronológica e isolamento entre
  usuários.
- Frontend: `useAtividadesRecentesQuery` + `AtividadesRecentesDrawer`,
  aberto por um botão novo no `Header`.

Validação: testes de integração passando, `tsc -b` e `vite build` limpos.

## 18. Auditoria final de experiência premium (item 18)

### Situação encontrada

Auditoria de todas as páginas de produção (`Dashboard`, `Contas`, `Cartões`
lista+detalhe, `Financiamentos`, `Empréstimos`, `Transações`,
`Transferências`, `Metas`, `Categorias`, `Tags`, `Calendário`) contra os 7
critérios de consistência já estabelecidos pelas etapas anteriores (estado
vazio, loading, erro de query, responsividade, padding externo, cabeçalho,
TODOs pendentes). Conclusão: a base já está madura (loading/erro/
responsividade/padding uniformes em praticamente todas as páginas) — só
pontos pequenos de divergência real foram encontrados, listados abaixo.
Nenhum TODO/FIXME esquecido em produção.

### Decisão (achados corrigidos, presentation-only — nenhuma regra de negócio nova)

1. **Dashboard**: subtítulo do cabeçalho sem `mt-1` (só essa página).
   Corrigido para bater com todas as outras.
2. **CTA no estado vazio**: `EmptyState`/`DataTable.emptyAction` já
   suportava um botão de ação, mas só `MetasPage` usava. Adicionado
   `emptyAction`/`action` (botão "Novo/Nova X" que abre o mesmo formulário
   de criação já existente na página) em `ContasPage`, `CategoriasPage`,
   `TagsPage`, `TransferenciasPage`, `TransacoesPage`, `FinanciamentosPage`
   e `EmprestimosPage` — mesmo componente/handler de criação que o botão do
   cabeçalho já chama, nenhuma lógica nova.
3. **Busca duplicada em `MetasPage`**: reimplementava manualmente o que
   `components/ui/SearchBar.tsx` (já usado por `CartoesPage`) resolve, e só
   aparecia com 5+ metas (comportamento que nenhuma outra página tem).
   Trocado por `SearchBar`, sempre visível.
4. **Calendário sem onboarding de conta zerada** e **placeholder de
   histórico em `CartaoDetalhePage`** (depende do CRUD de Transação incluir
   um filtro por cartão na página `/transacoes`, que hoje não existe):
   registrados como lacunas conhecidas, não corrigidos nesta etapa — cada
   um exigiria uma extensão de escopo (nova UI de filtro/onboarding) maior
   que um ajuste de consistência pontual; ficam documentados como próximo
   passo, não como bug.

Validação: `tsc -b` e `vite build` limpos após os ajustes.

## 3/6-14. Dashboard executivo + Dashboard de Cartões agregado — investigação e decisão

### Situação encontrada

`DashboardPage` hoje é uma sequência linear de ~9 seções, das quais 6
(`ContasCard`, `CartoesCard`, `FaturasCard`, `FinanciamentosCard`,
`EmprestimosCard`, `MetasCard`) são **listas item-a-item** (cada conta,
cada cartão, cada fatura, cada contrato, cada meta aparece individualmente)
— exatamente o padrão "coleção de mini-CRUDs" citado pelo usuário.
`CentralFinanceiraService` já expõe 11 endpoints de leitura, mas nenhum
devolve dado agregado de Cartão (limite total/disponível/usado/% geral) ou
de Metas (próxima conclusão, contagem em risco) — só listas cruas +
algumas contagens soltas em `indicadores_gerais`.

### Decisão

Nenhuma regra de negócio nova: os agregados novos (somas, contagens,
ordenações) são só leitura sobre dados que `CartaoService`/`MetaService`
já calculam corretamente (`limite_disponivel`, `percentual`,
`situacao_planejamento` etc.) — `CentralFinanceiraService` nunca recalcula
essas fórmulas, só soma/conta/ordena o que os services de domínio já
devolvem (mesmo princípio já usado em todos os métodos existentes deste
service).

- **Novo método `CentralFinanceiraService.resumo_cartoes_agregado`**:
  limite total, limite disponível total, limite usado total, % usado geral,
  contagem de cartões ativos, contagem de faturas em aberto, próximos 3
  vencimentos (fatura mais próxima por cartão), distribuição de uso por
  cartão (nome + %) para o "Dashboard de Cartões". Nova rota
  `GET /central-financeira/cartoes/resumo`. **Sem gráfico por cartão
  individual** — esse detalhe continua exclusivo de `/cartoes/:id`.
- **Cards do Dashboard viram resumos, não listas**: `ContasCard` mostra só
  saldo total, contagem, as 2-3 maiores contas e botão "Ver todas";
  `CartoesCard` consome o novo agregado (limite/disponível/usado/%,
  contagem, faturas abertas) em vez de listar cada cartão; `FaturasCard`
  filtra só vencidas + a vencer em breve (reaproveitando
  `resumo_faturas` já existente, só mudando o filtro/corte no frontend ou
  um parâmetro novo no service); `MetasCard` mostra contagem, progresso
  médio (já existe em `indicadores_gerais`), próxima conclusão (ordenação
  client-side por `data_alvo`/`percentual` sobre `progresso_metas`, sem
  endpoint novo) e contagem em risco (`situacao_planejamento`, já
  calculado por `MetaService`, só contado). Financiamentos/Empréstimos
  seguem o mesmo padrão de resumo.
- **Card "Hoje"**: reaproveita `calendario_financeiro(ano, mes)` (já
  implementado), filtrando client-side só os eventos de hoje — "Não quero
  lógica duplicada" é respeitado por construção, zero cálculo novo no
  backend. Ressalva já identificada: recorrências futuras ainda não
  geradas e "poupar para meta" como evento recorrente não aparecem no
  calendário hoje (só o prazo final da meta) — fora do escopo desta etapa,
  registrado como gap conhecido, não bloqueia o card (ele mostra o que já
  existe, como pedido).
- **Navegação**: a maioria dos cards já é clicável (`ContasCard`,
  `CartoesCard`, `MetasCard`, `AgendaFinanceiraCard`); faltam
  `FinanciamentosCard`/`EmprestimosCard` (sem `onClick` hoje) - serão
  ligados a `/financiamentos`/`/emprestimos`, mesmo padrão dos demais.
- **Hierarquia visual**: reorganização de layout/agrupamento, sem
  necessidade de nenhum dado novo além do já listado acima.

Implementação desta seção segue nas próximas etapas: backend do agregado
de Cartões (testado) → frontend dos cards resumidos → card "Hoje" →
navegação/hierarquia → validação.

### Implementado

Todo o plano acima foi executado:

- Backend: `resumo_cartoes_agregado` + rota `GET /central-financeira/cartoes/agregado`
  (testes unit/integration cobrindo soma de limites e o caso sem nenhum
  cartão cadastrado).
- `ContasCard` reescrito como resumo (saldo total, contagem, top 3 contas)
  e fundido com `SaldoPorContaCard` (removido — mesma informação, sem
  motivo para dois cards).
- `CartoesCard` reescrito consumindo o agregado novo: grid de métricas
  (limite disponível/usado, cartões ativos, faturas em aberto), barra de
  utilização geral e até 3 próximos vencimentos.
- `MetasCard` reescrito: contagem, progresso médio, "mais perto de
  concluir" e contagem de metas atrasadas — nada mais que soma/ordena
  sobre `percentual`/`situacao_planejamento` já calculados.
- `FaturasCard` reescrito: só mostra faturas atrasadas ou vencendo nos
  próximos 10 dias (o resto não precisa de atenção imediata no Dashboard e
  continua acessível em `/cartoes/:id`); some por completo quando não há
  nenhuma relevante.
- `FinanciamentosCard`/`EmprestimosCard`: cartão inteiro agora navega para
  `/financiamentos`/`/emprestimos` (antes eram os únicos sem destino).
- **Card "Hoje"** (`HojeCard.tsx`, novo): reaproveita
  `useCalendarioFinanceiroQuery(anoAtual, mesAtual)` — já existente, nenhum
  endpoint novo — filtrando client-side só os eventos cuja `data` é hoje.
  Usa o mesmo `ICONE_POR_ORIGEM`/`ROTA_POR_ORIGEM` de `AgendaFinanceiraCard`,
  garantindo que os dois nunca divirjam sobre o que é clicável. Posicionado
  logo após os indicadores gerais, antes do Bento Grid dos demais cards, e
  some sozinho quando não há eventos hoje. Gap conhecido documentado acima
  (recorrências futuras não geradas, meta como prazo único) permanece fora
  de escopo.

Validação: `tsc -b` limpo, `vite build` concluído sem erros, 543 testes de
unidade do backend passando (nenhuma mudança de backend nesta etapa além
do agregado de Cartões, já coberto por testes de integração próprios).
