# Análise arquitetural — Refinamento de UX, Onboarding, Dashboard e Cartões

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**, mesma convenção de
sempre. Cobre, em ordem, as 13 frentes do pedido. Backend permanece inalterado, exceto onde
a seção 6 sinaliza explicitamente uma decisão de modelagem — e mesmo essa fica **fora do
escopo de implementação desta etapa** até aprovação separada (ver seção 6.4). Nenhuma regra
de negócio existente é alterada; nenhuma lógica é duplicada; tudo abaixo reaproveita
componentes/hooks/endpoints já existentes, exceto onde o contrário é dito explicitamente.

## 0. O que já existe hoje (lido diretamente do código, não assumido)

- Dashboard: `pages/dashboard/DashboardPage.tsx` monta um Bento Grid orquestrando 13
  componentes de `components/domain/dashboard/`, cada um consumindo 1 dos 11 endpoints de
  `/central-financeira/*` via `hooks/useCentralFinanceiraQueries.ts` — arquitetura descrita em
  `docs/analise-arquitetural-dashboard.md`, seção 16.1 ("crescer sem refatoração"). Nenhum card
  hoje é clicável — `Card.tsx` já aceita `onClick`/qualquer prop nativa (`{...props}` repassado
  ao `motion.div`), então tornar um card navegável é aditivo, nunca uma reescrita.
- Rotas reais existentes (`routes/AppRoutes.tsx`): `/`, `/contas`, `/cartoes`, `/cartoes/:id`,
  `/categorias`, `/tags`, `/transacoes`. **Não existem** `/metas`, `/financiamentos`,
  `/emprestimos`, nem uma rota própria de Fatura (Fatura só existe aninhada em
  `/cartoes/:id`, via Drawer).
- Categoria: `Categoria.usuario_id` nullable já é, desde o início, o desenho de "categoria de
  sistema" (`usuario_id IS NULL` = padrão, compartilhada por todos; `CategoriaService` já
  trata visibilidade/edição desse caso corretamente) — só nunca foi populado. Zero mudança de
  modelagem necessária para a seção 5.
- Conta: `saldo_atual` é sempre calculado (nunca uma coluna), a partir de `saldo_inicial`
  (coluna real, existe desde o início) + soma de transações/transferências. **O formulário de
  criação de Conta já pede "Saldo inicial" hoje** (`ContaFormDialog.tsx`, campo
  `CurrencyField name="saldo_inicial"`) — ou seja, a parte de "saldo inicial" da seção 6 **já
  está implementada**, não é um gap.
- Cartão: não guarda saldo, só `limite` (coluna) — `limite_disponivel` é sempre calculado a
  partir da fatura aberta corrente. Fatura: `criar()` sempre nasce `status=ABERTA`,
  `valor_total=NULL`; só `fechar()` congela um `valor_total`. Pagamento
  (`registrar_pagamento`) só é aceito em fatura **não-ABERTA**, e cria uma `Transacao` real
  (`fatura_paga_id`), permitindo pagamento parcial/múltiplo nativamente.
- As duas "limitações" da seção 8 (não dar para lançar transação em ciclo fechado, não dar
  para excluir certas faturas) são, na leitura direta de `FaturaService`, **regras de negócio
  deliberadas e já documentadas no código-fonte**, não bugs de implementação — detalhado na
  seção 7.3 abaixo.

## 1. Dashboard como hub de navegação

Cada elemento vira uma superfície clicável (`onClick`/`useNavigate`, sem `<button>` extra
visível — o próprio card/linha é o alvo de clique, cursor `pointer`, hover já existente do
`Card` reforçado). Mapeamento, célula a célula:

| Elemento | Destino | Observação |
|---|---|---|
| StatCard "Saldo total" | `/contas` | Não existe uma tela de "saldo consolidado" própria; `/contas` é o destino mais próximo (mesma fonte de dado, `SaldoPorContaCard`/`ContasCard` usam o mesmo endpoint). |
| StatCard "Patrimônio líquido" | `/contas` | Idem — patrimônio líquido é derivado das mesmas contas; não há tela dedicada, e criar uma só para isso violaria "reutilize a arquitetura existente" sem necessidade real. |
| StatCard "Entradas do mês" / "Saídas do mês" / "Fluxo de caixa" | `/transacoes` | Com um filtro de período pré-aplicado via query string, já que `TransacoesPage` lista por período (a confirmar filtro exato ao implementar, sem mudança de contrato do backend). |
| `SaldoPorContaCard` (lista por conta) | `/contas` | Cada linha individual pode navegar para a mesma rota (sem detalhe por conta hoje). |
| `CartoesCard` (lista de cartões) | Cada linha → `/cartoes/:id` (já existe); título do card → `/cartoes` | Granularidade máxima possível hoje. |
| `FaturasCard` (não existe hoje como componente próprio — faturas aparecem dentro de Cartões) | — | Não há uma seção "Faturas" isolada no Dashboard atual (conferido em `DashboardPage.tsx`) — o pedido original citava "Faturas" como se já existisse; na prática, hoje quem navega para fatura é sempre via `/cartoes/:id`. Nenhuma ação necessária além do mapeamento de `CartoesCard` acima. |
| `MetasCard` | **Sem destino — não existe `/metas`** | Card permanece visualmente igual mas **não clicável** (sem `cursor-pointer`/hover de navegação, para não prometer uma navegação que não existe). Documentado como dependência de uma futura Etapa de CRUD de Meta. |
| `FinanciamentosCard` | **Sem destino — não existe `/financiamentos`** | Mesmo tratamento — não clicável, deferido. |
| `EmprestimosCard` | **Sem destino — não existe `/emprestimos`** | Mesmo tratamento — não clicável, deferido. |
| `AgendaFinanceiraCard` (por evento) | Depende de `origem_tipo`: `CONTA`→`/contas`, `CARTAO`→`/cartoes/:id` (usando `origem_id` como `cartao_id`), `TRANSACAO`→`/transacoes` | `FATURA`/`PARCELAMENTO`/`FINANCIAMENTO`/`EMPRESTIMO`/`CONTA_RECORRENTE`/`META` **não navegam** — ou não há rota (Parcelamento/Financiamento/Empréstimo/ContaRecorrente/Meta), ou o payload do evento (`origem_id`) não é suficiente para montar a URL sozinho (evento de `FATURA` traz o `id` da fatura, não o `cartao_id` necessário para `/cartoes/:id` — buscar isso exigiria uma chamada extra só para montar um link, custo não justificado agora). Itens sem destino continuam exibidos normalmente, só sem affordance de clique. |

Nenhum botão novo visível é adicionado — a affordance é o próprio card (cursor, hover já
existente do `Card.tsx`, leve reforço de contraste da borda no hover para sinalizar
"clicável" sem texto extra).

## 2. Reimaginação visual do Dashboard

Pesquisa breve (não normativa, só para calibrar decisões) sobre os apps citados confirma um
padrão convergente, não 8 estilos diferentes: liderar com o número que mais importa (saldo),
manter contagem visual baixa por tela (progressive disclosure — Linear esconde analytics
atrás de uma aba "Insights"; Stripe usa 4 cards com número+tendência, nunca 15), cor com
peso semântico consistente (verde/vermelho só para ganho/perda reais, nunca decorativo), e
hierarquia por tamanho de fonte/peso em vez de mais bordas/caixas. Decisões concretas para
este projeto (reaproveitando 100% do Design System/tokens já existentes, nenhuma cor/fonte
nova):

- Removida a divisão rígida "seção 8.2 (Resumo) + seção 8.3 (Indicadores) + seção 8.5
  (Detalhamento)" como três blocos de peso visual igual. Novo agrupamento por prioridade:
  **hero** (Saldo total + Patrimônio líquido, maior destaque, os dois já são 3/12 colunas
  hoje) → **contexto do mês** (Entradas/Saídas/Fluxo, ver seção 3 abaixo) → **indicadores de
  apoio** (a faixa compacta atual, mantida, mas visualmente mais discreta — reduzir contraste
  de fundo, não remover informação) → **detalhamento por domínio** (Contas/Cartões/Metas/etc,
  mantido) → **Agenda** (mantido por último).
- `IndicadoresStrip` (seção 8.3 do doc anterior) passa a usar tom mais neutro (menos "cards
  dentro de cards" competindo visualmente com o Resumo) — ajuste de estilo, não de dado.
- Nenhuma nova biblioteca de gráfico é introduzida (decisão já adiada em
  `analise-arquitetural-dashboard.md`, seção 0.3, reafirmada aqui — está fora do escopo de
  "polimento").

## 3. "Entradas e Saídas" — redução/reorganização

Hoje isso é `VisaoMensalCard` (8/12 colunas, duas barras horizontais `div` + fluxo de caixa em
texto) **mais** os StatCards redundantes "Entradas do mês"/"Saídas do mês"/"Fluxo de caixa" já
presentes em `ResumoFinanceiroSection` (confirmado: os mesmos 3 números aparecem 2x na tela,
já sinalizado como intencional em `analise-arquitetural-dashboard.md`, seção 3.1 — "visualmente
diferentes, mesmo dado por trás" — mas a duplicação visual é exatamente a queixa da seção 3
deste pedido). Decisão: **fundir os dois** em vez de manter ambos.

- `VisaoMensalCard` deixa de ser um card de 8 colunas com barras grandes e passa a ser uma
  *mini-visualização compacta embutida dentro do próprio StatCard "Fluxo de caixa"* do Resumo
  Financeiro (um sparkline/mini-barra de proporção entradas×saídas, poucos pixels de altura,
  no rodapé do card já existente) — elimina a seção duplicada inteira do grid principal,
  sem perder a comparação visual, só reduzindo-a de "card próprio" para "detalhe dentro de um
  card que já existe". Reaproveita 100% do dado (`useVisaoMensalQuery`), muda só onde ele é
  renderizado.
- Efeito colateral positivo: o grid de `SaldoPorContaCard` (4 col) + `VisaoMensalCard` (8 col)
  desaparece, e `SaldoPorContaCard` ganha a linha inteira (ou passa a compor a mesma linha do
  Resumo) — grid final mais enxuto, um bloco a menos para o olho escanear.

## 4. Cards "mais inteligentes"

Infraestrutura já existe e é só sub-aproveitada — reutilizar, não recriar:

- `FinancialBadge` (mapeia `StatusFatura`/`StatusContratoCredito`/`StatusTransacao` → tone)
  já existe mas só é usado em `FinanciamentosCard` hoje. Passa a ser usado em `CartoesCard`
  (cartão perto do vencimento) e `MetasCard` (meta com prazo vencido/perto de vencer, usando
  `tonePorPrazo` de `utils/status.ts`, já existente e já usado em `CartaoVisual`).
  Nenhum `switch` novo de enum→cor é criado — mesma régua central de sempre.
- `TrendIndicator` (seta + variação %) já existe no código (`components/ui/TrendIndicator.tsx`)
  mas está sem uso real — nenhum dos 11 endpoints expõe "variação vs. mês anterior"
  (confirmado em `analise-arquitetural-dashboard.md`, seção 9.1). Usá-lo de verdade exigiria
  o backend calcular uma variação — **fora de escopo aqui** (mudaria contrato de API sem
  necessidade comprovada; fica sinalizado, não implementado).
- Indicadores de "próxima ação" usando só dado já calculado: `CartoesCard` já mostra "vence em
  X dias" com tone por prazo — estender o mesmo padrão (ícone de alerta + tone) para
  `FaturasCard`/fatura mais próxima do vencimento dentro de `CartaoDetalhePage`, e para
  `MetasCard` (`tonePorPrazo` sobre `data_alvo`, quando presente).
- Nenhum ícone/badge é decorativo sem significado (evita ruído): cada indicador novo mapeia
  1:1 a um dado real já calculado pelo backend (prazo, percentual, status) — nunca um número
  inventado no cliente.

## 5. Categorias padrão

Confirmado na seção 0: zero mudança de modelagem. Implementação puramente de dado — um script
de seed (migração Alembic de dados, não de schema) inserindo categorias com `usuario_id=NULL`.
Estrutura proposta (pai/filho, usando `categoria_pai_id` já existente):

- Alimentação → Mercado, Delivery, Restaurante, Padaria
- Transporte → Combustível, Uber/Apps, Estacionamento, Pedágio, Manutenção
- Moradia → Água, Energia, Internet, Condomínio, Gás
- Saúde → Consultas, Farmácia, Plano de saúde
- Educação → Cursos, Material, Mensalidade
- Lazer → Streaming, Viagens, Hobbies
- Compras → Vestuário, Eletrônicos, Casa
- Pets
- Assinaturas
- Investimentos
- Presentes
- Trabalho
- Renda (categoria de entradas — hoje `Categoria.tipo` já suporta `RECEITA`/`DESPESA`/`AMBOS`;
  categorias padrão de entrada como Salário/Freelance/Rendimentos entram aqui)

Todas com `tipo`/`cor`/`icone` preenchidos (mesmos componentes `IconPicker`/`ColorPicker` já
existentes definem a paleta — nenhuma cor nova inventada fora do sistema semântico). Usuário
continua podendo editar/desativar/criar as suas — `_buscar_editavel` já bloqueia edição só
das categorias de sistema (`usuario_id IS NULL`), comportamento correto e inalterado.
**Decisão a confirmar com você antes de codar**: a migração de seed roda automaticamente
(alembic upgrade) para bancos existentes E novos, ou só para bancos novos? Como o banco atual
já está em uso (dado real do projeto), a migração precisa ser idempotente (verificar se já
existe antes de inserir) — vou tratar isso como um requisito da implementação, não uma
decisão de produto.

## 6. Estado inicial (onboarding financeiro) — análise antes de implementar

Pedido explícito: analisar a melhor solução respeitando a arquitetura atual, documentar antes
se exigir modelagem nova. Indo item a item:

### 6.1 Saldo inicial (Conta) — já resolvido, nenhuma ação necessária

`ContaFormDialog` já pede "Saldo inicial" na criação. Nada a fazer.

### 6.2 Cartão já existente + limite já utilizado — resolvido pela arquitetura já existente

Criar o Cartão normalmente (limite, dia de fechamento/vencimento) já é suficiente — "limite já
utilizado" nunca foi uma coluna, é sempre `limite - limite_disponivel`, e `limite_disponivel`
é sempre derivado da fatura aberta corrente. Ou seja, assim que existir QUALQUER transação de
compra na fatura aberta do cartão, o "limite já utilizado" já aparece certo automaticamente.
O gap real está em *como* o usuário registra esse "já usei R$ 800 do limite" sem lançar
compra por compra (próximo item).

### 6.3 Fatura em aberto com saldo já gasto — gap real, solução proposta sem mudar modelagem

Hoje, para o "limite já utilizado" (6.2) refletir a realidade, seria necessário lançar cada
compra histórica individualmente — exatamente o retrabalho que o pedido quer evitar. Solução
proposta, reaproveitando 100% do model `Transacao` já existente: um passo de onboarding
("Ajuste de saldo inicial da fatura") que cria **uma única `Transacao` de compra**, valor =
o total que o usuário já sabe que está gasto hoje, descrição fixa tipo "Saldo inicial
(ajuste)", vinculada à fatura aberta corrente do cartão (via o mesmo
`resolver_fatura_aberta` que qualquer transação de cartão já usa). Nenhum endpoint novo,
nenhuma coluna nova — é literalmente uma `Transacao` normal, só originada de um fluxo de UI
dedicado em vez do formulário genérico de Transação. **Isto é reaproveitamento de arquitetura,
não uma exceção especial no backend.**

### 6.4 Fatura já FECHADA (ciclo anterior, ainda com saldo devedor) antes do usuário começar a usar o app

Esse caso **não** tem uma solução puramente de dado como o 6.3: `FaturaService.criar()` só
sabe criar faturas `ABERTA` (regra deliberada, seção 0). Para representar "eu já tinha uma
fatura fechada de R$ 1.200 em aberto quando comecei a usar o sistema", seria necessário um
novo caminho de criação que aceite `status=FECHADA` + `valor_total` vindos do cliente — **isso
é uma mudança de regra de negócio** (hoje `valor_total`/`status` nunca vêm do payload, sempre
calculados), então cai exatamente na cláusula "se exigir alteração de modelagem, documente
antes" do pedido. **Não implemento isso nesta etapa.** Recomendação: tratar como avançado/raro
o suficiente para não valer o risco arquitetural agora — o caso comum (fatura do mês corrente
em andamento) já é coberto pelo 6.3. Se você quiser essa capacidade mesmo assim, ela precisa
virar uma etapa própria, com sua própria análise de impacto no backend (endpoint novo tipo
`POST /faturas/importar-existente`, ou um parâmetro opcional em `FaturaCreate` guardado atrás
de uma flag "fatura histórica" com suas próprias validações) — deixo sinalizado, não decidido
por mim sozinho.

### 6.5 Parcelamentos, Financiamentos e Empréstimos já existentes

Nenhuma das três entidades tem CRUD/tela no frontend ainda (só existem no backend). "Estado
inicial" delas é, por definição, dependente de uma etapa futura ainda não iniciada — fora de
escopo aqui, mesma lógica da seção 1 (Metas/Financiamentos/Empréstimos sem rota). Quando essas
telas nascerem, o formulário de criação de cada uma já deve nascer pensando em "posso estar
cadastrando algo que já está no meio do caminho" (ex.: financiamento com `parcelas_pagas` > 0
desde o dia 1) — reservo essa diretriz para quando aquela etapa chegar, não invento a tela
agora.

## 7. Cartões e Faturas — experiência de criação

### 7.1 Criação de Fatura hoje

Só pede `mes_referencia` (data_fechamento/vencimento sempre derivadas do Cartão) — confirmado
como suficiente para o uso normal (fatura nasce ABERTA, valores sempre calculados a partir das
transações reais). Não há necessidade de expandir esse formulário: o modelo já é "criar o
ciclo, deixar o valor emergir das transações reais" — mudar isso para pedir valores manuais
contradiria a arquitetura de "documento financeiro histórico calculado, nunca digitado"
(mesmo princípio de `valor_total` congelado só no fechamento).

### 7.2 Registrar fatura pré-existente no onboarding

Coberto na seção 6.3/6.4 acima — resposta funcional para o ciclo aberto (6.3), gap real e
sinalizado (não implementado) para ciclo já fechado (6.4).

### 7.3 As duas "limitações" — classificação

- **"Não dá para lançar transação em ciclo já fechado"**: **regra de negócio deliberada**,
  não bug. `FaturaService.resolver_fatura_aberta` rejeita explicitamente
  (`BusinessRuleError`) quando o ciclo resolvido para a data da transação já não está mais
  `ABERTA` — o comentário no código é explícito: "não mascarar um provável erro de data".
  Fatura fechada tem `valor_total` congelado por design (documento financeiro histórico);
  aceitar novas transações ali quebraria essa garantia. **Não altero isso** (constraint
  explícita do pedido: não mudar regra de negócio sem necessidade — e não há necessidade
  demonstrada, é o comportamento correto para um sistema financeiro).
- **"Não dá para excluir certas faturas"**: também **regra de negócio deliberada**.
  `FaturaService.excluir()` só permite excluir fatura ainda `ABERTA` e sem nenhuma transação
  vinculada — qualquer fatura fechada ou com histórico real é permanente, mesmo racional já
  aplicado a `Conta.excluir()`/hard delete em toda a Etapa F10 (documento
  `docs/analise-arquitetural-exclusao.md`). Não é uma limitação técnica, é proteção de
  histórico financeiro. **Não altero isso.**

Ambas ficam documentadas no resumo final como "investigado, é regra de negócio, mantido de
propósito" — exatamente o que a seção 8 do pedido pediu para o caso de não ser bug.

## 8. (conteúdo já coberto acima, nas seções 6/7 — sem repetição)

## 9. Primeira experiência de uso

- `DashboardOnboarding` já foi corrigido numa etapa anterior (o botão "Criar conta" que
  apontava para lugar nenhum já foi trocado por navegação real para `/contas` — conferido no
  próprio código, comentário já registra esse achado). Nada a fazer aqui de novo.
  Continua sendo o gate quando `contas_ativas === 0`.
- Oportunidade real e nova: depois de criar a primeira Conta, o próximo passo natural
  (criar um Cartão, ou já ir direto para Transação) não tem nenhuma sugestão guiada — o
  usuário volta ao Dashboard e vê zeros nos outros cards sem saber o que fazer a seguir.
  Proposta: dentro do próprio `DashboardOnboarding`/gate inicial, ou como um estado
  intermediário (`contas_ativas > 0` mas `cartoes_ativos === 0` e nenhuma transação), mostrar
  uma sugestão textual leve ("Cadastre seu primeiro cartão" com link para `/cartoes`) —
  reaproveita o mesmo padrão de `EmptyState`, sem novo componente.
- Seed de categorias padrão (seção 5) também reduz retrabalho de primeira experiência —
  usuário já vê categorias sensatas na primeira vez que cria uma Transação, em vez de uma
  lista vazia.

## 10. Auditoria de UX (autocrítica)

Achados relevantes, encontrados durante esta investigação (sem esperar apontamento):

- **Duplicação visual Resumo × Visão Mensal** (seção 3) — já endereçada.
- **`TODO` obsoleto em `categoria_service.py::desativar()`**: comentário antigo dizendo que
  checagem de "categoria em uso" deveria ser adicionada quando o CRUD de Transação existisse
  — ele existe agora, e `desativar()` (soft delete) ainda não verifica transações vinculadas
  antes de desativar uma categoria (diferente de `excluir()`, hard delete, que já verifica).
  Não é uma regra de negócio pedida por ninguém agora, mas é uma inconsistência real entre os
  dois caminhos de "remover" categoria — proponho corrigir (mesma checagem, reaproveitada) e
  remover o comentário obsoleto, classificado como correção de bug/inconsistência, não feature
  nova.
- **Cards de Metas/Financiamentos/Empréstimos sem destino de navegação** (seção 1) — não é
  bug, é ausência real de tela; documentado, não meia-solução (não crio uma rota vazia só
  para ter link).
- **`IndicadoresStrip` competindo visualmente com o Resumo** (seção 2) — ajuste de peso
  visual, sem mudança de dado.

## 11. Consistência (Design System/Motion/Responsividade)

Nenhuma mudança estrutural nova nesta etapa além do já decidido nas seções 2-4 — tudo
reaproveita tokens/`motion-principles.md` já existentes. Nenhum novo breakpoint, cor, fonte ou
curva de animação é criado. Verificação final (seção 13) inclui checagem manual de que os
cards clicáveis novos (seção 1) têm foco visível/teclado (acessibilidade, mesmo padrão já
usado nos demais elementos interativos do projeto).

## 12. Performance

Nenhuma mudança estrutural de busca de dado (continua 1 hook por seção, sem waterfall). Ao
tornar cards clicáveis, cuidado para não regressar a memoização já aplicada (`React.memo`
onde já existe) — `onClick`/`useNavigate` não deve virar uma nova prop instável recriada a
cada render se o card já for memoizado (mesmo cuidado que corrigiu o loop de
`useFloatingPanel`, mas aqui é preventivo, não um bug encontrado). Verificação real via
build/profiler ao final, não otimização especulativa antecipada.

## 13. Entrega

Ao final da implementação: `tsc -b` + `vite build` limpos, teste manual no navegador,
`npm run build` + restart dos processos em segundo plano (`parar.ps1`/`iniciar.ps1`, combinado
já registrado no README), documento de revisão técnica desta etapa, atualização de
`README.md`/`dashboard/project-status.json`. Resumo final vai diferenciar claramente: bugs
corrigidos (TODO obsoleto de `desativar()`), melhorias de UX (cards clicáveis, fusão
Entradas/Saídas, cards mais informativos, seed de categorias, ajuste de saldo inicial de
fatura), decisões arquiteturais tomadas (o que NÃO foi implementado e por quê — fatura
histórica fechada, seção 6.4) e o que fica deferido para quando Metas/Financiamentos/
Empréstimos ganharem CRUD próprio.

## 14. Ordem de implementação proposta (aguardando aprovação)

1. Seed de categorias padrão (seção 5) — isolado, sem dependência de UI.
2. Correção do `TODO` obsoleto em `desativar()` de Categoria (seção 10) — bug fix pontual.
3. Dashboard: fusão Entradas/Saídas no StatCard de Fluxo de Caixa (seção 3), reorganização
   visual de prioridade (seção 2), cards clicáveis (seção 1), indicadores mais inteligentes
   (seção 4).
4. Onboarding: sugestão pós-primeira-conta (seção 9), fluxo de "ajuste de saldo inicial de
   fatura" (seção 6.3).
5. Auditoria de consistência/performance finais (seções 11/12) e entrega (seção 13).

Nenhuma linha de código será escrita até você validar este documento — mesmo protocolo de
sempre. Avise se algum mapeamento da seção 1, a fusão da seção 3, ou a decisão de NÃO
implementar 6.4 merecem ajuste antes de eu seguir.
