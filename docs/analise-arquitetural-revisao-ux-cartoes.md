# Revisão de UX — Módulo de Cartões (produto final)

## 0. Contexto e objetivo

Pedido do usuário, verbatim (resumo): o módulo de Cartões funciona corretamente, mas ainda
"parece um CRUD". O objetivo desta etapa é exclusivamente de UX/UI/motion — **nenhuma regra de
negócio, nenhum endpoint, nenhum contrato de API muda**. O cartão deixa de ser tratado como um
registro e passa a ser tratado como um dos objetos mais importantes do sistema — o padrão de
referência para como as próximas 9 entidades (Transação em diante) deveriam "parecer produto".

Critério de decisão usado em cada escolha abaixo: *"essa solução faz o usuário querer abrir
essa tela todos os dias?"*. Inspiração (Linear/Framer/Raycast/Apple/Stripe), nunca cópia de
Nubank/Inter/Mercado Pago — identidade própria, já estabelecida em `CartaoVisual`
(gradientes de marca, tilt 3D) e nos tokens do Design System.

Este documento é o gate de aprovação de sempre (mesmo protocolo de toda etapa anterior:
análise → aprovação → implementação). Depois de aprovado, a implementação segue sem pausas
intermediárias.

## 1. Escopo e não-escopo

**Dentro do escopo (só apresentação, reaproveitando dados/endpoints já existentes):**
`GET /cartoes`, `GET /cartoes/{id}`, `GET /faturas?cartao_id=`, `PATCH/DELETE` de sempre
(desativar/reativar/excluir) — nenhum campo novo, nenhuma rota nova, nenhuma lógica de
cálculo nova no backend.

**Fora do escopo (documentado na seção 14, não implementado agora):** qualquer coisa que
dependa de `Transacao` (histórico de compras do cartão, análise de gastos por categoria,
tendência de utilização ao longo do tempo).

## 2. Decisão 1 — Listagem: `DataTable` → grid de cards clicáveis

`docs/analise-arquitetural-cartao-frontend.md`, seção 9, já registrava esta tensão
explicitamente: *"não vira uma página de grid de cards do zero (isso sim seria uma mudança de
padrão de página digna de discussão à parte — não é o que esta análise propõe)"*. Esta é
exatamente essa discussão, agora pedida pelo usuário.

`/cartoes` deixa de usar `DataTable`/`ColumnDef`/`cartaoTableColumns.tsx` e passa a renderizar
um **grid responsivo de `CartaoResumoCard`** (novo componente, seção 4). Justificativa: uma
tabela comunica "registros a gerenciar"; um grid de cards ricos comunica "painel de contas
financeiras" — exatamente a virada de percepção pedida. Volume de dados de um cartão por
usuário é tipicamente baixo (unidades, não centenas) — paginação/ordenação de `DataTable` não
fazem falta real.

O que a página mantém (reconstruído fora do `DataTable`, componentes já existentes):
- Busca por nome/instituição/últimos 4 dígitos (`SearchInput` já existe como primitivo).
- Filtro por bandeira (`Select` simples).
- Switch "mostrar inativos".
- `EmptyState` quando não há cartões (ou nenhum resultado de busca/filtro).
- `Skeleton` de carregamento (grid de placeholders no formato do card, não linhas de tabela).

O que a página perde (aceitável, nada usa hoje): ordenação por coluna, paginação client-side
(lista curta não precisa).

`cartaoTableColumns.tsx`/`cartaoTableFilters` são removidos (nada mais os consome).
`CartaoVisual layout="compact"` fica sem uso após a remoção — removido junto (nenhum outro
consumidor, `CartoesCard.tsx` do Dashboard tem implementação própria e não importa
`CartaoVisual`).

## 3. Decisão 2 — Anatomia do `CartaoResumoCard` (mini dashboard)

Ordem de leitura (storytelling, do pedido do usuário) dentro do próprio card da listagem:

1. **Qual cartão** — `InstitutionBadge` + `BandeiraBadge` + nome + `•••• dígitos` (mesmo
   cabeçalho que `CartaoVisual layout="full"` já desenha).
2. **Quanto ainda posso gastar** — "Disponível" em destaque (maior peso visual do card,
   `text-h2`/`font-semibold`, `AnimatedNumber` com count-up `SPRING.gentle` — mesmo padrão de
   `StatCard`), com "de {limite} total" em texto secundário logo abaixo.
3. **Como está a utilização** — `ProgressBar` + percentual calculado (`AnimatedNumber
   format="percent"`) + indicador semáforo (seção 5 — correção de cor).
4. **Próxima fatura** — busca a fatura mais relevante entre as já carregadas por
   `useFaturas(cartaoId)` (nenhuma query nova: a própria listagem de faturas do cartão, que a
   página de detalhes já usa, também alimenta o card — ver nota de performance na seção 12
   sobre pré-carregamento): a `ABERTA` mais recente, ou a próxima com `data_vencimento` futura.
   Mostra "vence em N dia(s)" + `FinancialBadge` de status + valor (se já fechada).
5. **Preciso agir agora** — chip de alerta discreto só quando aplicável (fatura `ATRASADA`, ou
   utilização ≥ 90%) — nunca um badge extra se está tudo normal (ruído visual desnecessário).
6. **Ações** — `CartaoActionBar` (seção 6), sempre visível na base do card.

Dados adicionais expostos sem poluir (texto pequeno, canto do card): quantidade de faturas
(`faturas.length`, já carregado), dias até fechamento (já existe em `CartaoVisual`).

Sem campo "tipo"/"apelido" — `Cartao` não tem essas colunas (`app/models/cartao.py`): `nome` já
cumpre esse papel. Nenhum campo novo é inventado nesta etapa.

## 4. Decisão 3 — Cartão inteiro clicável

O card inteiro navega para `/cartoes/:id` ao clicar em qualquer área livre. Padrão de
acessibilidade escolhido: **não** envolver o card inteiro em `<a>`/`<Link>` (um `<button>` da
Action Bar dentro de um `<a>` é HTML inválido — elemento interativo aninhado, quebra leitores
de tela). Em vez disso:

- Container é um `<div role="link" tabIndex={0}>` com `onClick`/`onKeyDown` (Enter/Espaço)
  chamando `navigate(...)`, `aria-label` descritivo ("Ver detalhes do cartão {nome}").
- Botões da Action Bar (dentro do card) chamam `event.stopPropagation()` no `onClick` — mesmo
  padrão que qualquer botão dentro de um `RowAction`/card clicável já precisaria em qualquer
  lugar do projeto.
- `focus-visible:ring` no container inteiro (mesmo token `--color-accent-ring` de todo
  elemento focável do Design System).

Hover (motion-principles.md + `Card.tsx`, mesmo padrão já usado no resto do app — "leve
elevação" pedida é literalmente o que `Card` já faz): `y: -2`, borda para
`--color-border-strong`, `--shadow-sm` → `--shadow-md`, `cursor-pointer`. Brilho: reaproveita o
glow radial que segue o mouse já existente em `CartaoVisual layout="full"` (não inventa um
efeito novo) — "extremamente discreto" já é a opacidade atual (`0.22`), mantida.

## 5. Decisão 4 — `CartaoActionBar`

Novo componente compartilhado (`components/domain/cartao/CartaoActionBar.tsx`), usado nos dois
lugares (card da listagem e página de detalhes) para consistência visual e zero duplicação:

| Ação | Ícone (`lucide-react`) | Onde aparece | Comportamento |
|---|---|---|---|
| Editar | `Pencil` | sempre | abre `CartaoFormDialog` em modo edição |
| Faturas | `Receipt` | só no card da listagem | navega para `/cartoes/:id#faturas` (a página de detalhes rola até a seção Faturas ao montar com esse hash — sem endpoint novo, só `scrollIntoView`) |
| Desativar / Reativar | `Ban` / `RotateCcw` | sempre | mesmo fluxo já existente (`ConfirmAction` para desativar; reativar é direto) |
| Excluir | `Trash2` | sempre | mesmo fluxo já existente (`ConfirmAction` reforçado da Etapa F10) |

Visual: botões maiores que os atuais (`size="sm"` → padrão, ícone + texto sempre visível em
desktop/tablet; em mobile, ícone + texto continuam visíveis mas a barra vira scroll horizontal
se não couber — nunca esconde texto atrás de um menu "..." escondido, ação frequente merece
estar sempre à vista). Todos os botões `stopPropagation` quando dentro do card clicável (seção
4). Na página de detalhes, a Action Bar sem "Faturas" (a seção já está na própria página).

## 6. Decisão 5 — Correção de cor semântica (achado da auditoria)

`design-system.md`, seção 6.3, é uma regra dura: `--color-accent` é *"reservado para
interação, nunca para dado financeiro"*; seção 6.4 reforça que positive/negative/warning são
as **únicas** cores com significado financeiro. O código atual de `CartaoVisual` viola essa
regra desde a Etapa F9: `tone = percentual >= 100 ? "negative" : percentual >= 80 ? "warning" :
"accent"` — usa a cor de interação para representar "utilização saudável", que é dado
financeiro, não uma ação.

Correção: `ProgressBar` ganha um quarto `tone` (`"positive"`, token `--color-positive` já
existente, mesmo verde de saldo positivo/fatura paga) e o cálculo de tone em
`CartaoVisual`/`CartaoResumoCard` passa a ser `negative` (≥100%) / `warning` (≥80%) /
`positive` (abaixo disso) — o semáforo 🟢🟡🔴 pedido pelo usuário, resolvido com as cores
semânticas que o próprio Design System já define para "positivo/atenção/negativo", sem
introduzir emoji literal na interface (mantém a consistência do resto do app, que já expressa
esses três estados via `Badge`/`ProgressBar` coloridos, nunca caracteres emoji). Efeito visual:
a barra de utilização saudável muda de roxo (marca) para verde — mudança pequena e
inteiramente coberta pela própria regra escrita do Design System, não uma preferência nova.

## 7. Decisão 6 — Página de detalhes: reorganização em seções (storytelling)

`CartaoDetalhePage` é reorganizada na ordem exata pedida (cada seção responde a uma pergunta
antes que o usuário precise procurar):

1. **Cabeçalho** — breadcrumb "Voltar para Cartões" + nome do cartão como título da página
   (hoje só existe o botão voltar, sem título próprio da página).
2. **Resumo** (hero, topo, maior destaque) — `CartaoVisual layout="full"` ao lado (desktop) ou
   acima (mobile) de um bloco com "Disponível" em `StatCard`-like hero, percentual e
   `ProgressBar` grande com tone correto (seção 6).
3. **Utilização** — breakdown: limite total, utilizado, disponível (3 `MetricCard`, já
   existem) + a mesma barra da seção 2 não se repete, só os números de apoio.
4. **Próxima fatura** — card de destaque isolado (não misturado com a lista completa):
   `FinancialBadge`, "vence em N dias", valor, botão de ação contextual (Fechar/Registrar
   pagamento) direto ali — atalho que evita abrir o `FaturaDrawer` para a ação mais comum.
5. **Ações rápidas** — `CartaoActionBar` (seção 6, sem "Faturas").
6. **Faturas** (`id="faturas"`, ver seção 6 sobre o link do card) — lista completa inline, já
   implementada na F10, mantida.
7. **Informações do cartão** — instituição, bandeira, dia de fechamento/vencimento, conta de
   pagamento vinculada (dados hoje "escondidos" só no formulário de edição, nunca exibidos em
   modo leitura — passam a ter uma seção própria, sem card genérico "detalhes técnicos").
8. **Histórico** — placeholder documentado (seção 13), não implementado agora.

## 8. Decisão 7 — Simplificação do `CartaoFormDialog`

Com o card inteiro clicável (seção 4) e a página de detalhes cobrindo toda visualização
(seção 7), a ação "Ver" (modal somente-leitura) fica redundante — abrir um modal só para ler o
que a página de detalhes já mostra melhor é fricção sem propósito, na contramão de
"informação sempre visível". `CartaoFormDialog` perde o modo `somenteLeitura`/toggle "Editar":
passa a ser usado só para **criar** e **editar** (título e rodapé sempre no modo de edição). A
ação "Ver" desaparece do grid (o clique no card já é "ver"); "Ver detalhes" também desaparece
como ação redundante — o clique no card *é* a navegação.

## 9. Componentes novos, alterados e removidos

**Novos:**
- `components/domain/cartao/CartaoResumoCard.tsx` — card clicável do grid (seção 3/4).
- `components/domain/cartao/CartaoActionBar.tsx` — action bar compartilhada (seção 5).
- `components/domain/fatura/ProximaFaturaCard.tsx` — card de destaque da seção 4 da página de
  detalhes (reaproveita `useFaturas` já carregado, nenhuma query nova).

**Alterados:**
- `pages/cartoes/CartoesPage.tsx` — grid em vez de `DataTable`, busca/filtro/switch
  reconstruídos localmente.
- `pages/cartoes/CartaoDetalhePage.tsx` — reorganizado em seções (seção 7), suporte a
  `#faturas` no hash (scroll on mount).
- `components/domain/cartao/CartaoFormDialog.tsx` — remove modo somente-leitura (seção 8).
- `components/domain/cartao/CartaoVisual.tsx` — tone correction (seção 6); avaliar se
  `layout="compact"` deixa de existir (ver abaixo).
- `components/ui/ProgressBar.tsx` — novo tone `"positive"`.

**Removidos:**
- `components/domain/cartao/cartaoTableColumns.tsx` (DataTable descontinuada para Cartão).
- `CartaoVisual layout="compact"` — sem consumidor após a remoção da tabela (confirmado via
  busca: só `cartaoTableColumns.tsx` o usava).

## 10. Microinterações e motion (tudo já dentro do vocabulário de `motion-principles.md`)

| Elemento | Gatilho | Spec |
|---|---|---|
| `CartaoResumoCard` | hover | `y: -2`, `--shadow-sm`→`--shadow-md`, `DURATION.fast`/`EASE.out` (mesmo `Card.tsx`) |
| `CartaoResumoCard` | entrada do grid | fade + `y: 8→0`, `DURATION.moderate`/`EASE.out`, stagger curto entre cards (orçamento total ≤ `DURATION.slow`, seção 5.2 de motion-principles) |
| Percentual/valores | contagem | `AnimatedNumber`, `SPRING.gentle` (já existe, reaproveitado) |
| `ProgressBar` | mudança de valor | `SPRING.gentle` (já existe) |
| Troca de tone (verde→amarelo→vermelho) | cruzar limiar de 80%/100% | crossfade de cor, `DURATION.base`, nunca instantâneo (mesmo tratamento de badge de status em motion-principles.md, seção 6) |
| Action bar | hover/focus de botão | `SPRING.snappy` (já é o padrão de `Button`) |
| Skeleton do grid | carregamento | mesmo `.skeleton-shimmer` já existente |
| Página de detalhes | entrada | fade + slide, `DURATION.moderate`, sem stagger pesado (é uma página, não uma lista) |

## 11. Responsividade

- **Desktop (`lg+`):** grid 2-3 colunas (`grid-cols-2 xl:grid-cols-3`), cards com todas as
  informações lado a lado (hero + progress bar + próxima fatura em linha).
- **Tablet (`md`):** grid 2 colunas, mesma densidade de informação, texto secundário reduzido.
- **Mobile (`<md`):** 1 coluna, card empilhado verticalmente (hero → progress → próxima
  fatura → action bar), Action Bar com scroll horizontal se necessário — nunca corta texto de
  botão. Página de detalhes: colunas empilham (já é o comportamento atual do grid
  `lg:grid-cols-[...]`), Action Bar também linear.

## 12. Performance

Pontos a auditar/corrigir durante a implementação:
- `useFaturas(cartaoId)` hoje só é chamado dentro de `CartaoDetalhePage`. Com o card da
  listagem também precisando da "próxima fatura" (seção 3, item 4), cada `CartaoResumoCard` do
  grid dispara sua própria query `GET /faturas?cartao_id=` — aceitável (poucos cartões, React
  Query já dedupe/cacheia por `queryKey`, e a mesma query é reaproveitada instantaneamente
  quando o usuário entra na página de detalhes daquele cartão — cache quente, não repete a
  requisição).
- `lib/cardThemes.ts` já tem cache em memória da preferência de tema (Etapa F9) — mantido.
- Nenhum `useState` novo por `mousemove` (tilt do card continua via `useMotionValue`, mesmo
  princípio já usado).
- Grid com poucos itens não precisa de virtualização.

## 13. Preparado para o futuro (Transação) — documentado, não implementado agora

- **Histórico** (seção 7, item 8): quando `Transacao` existir, mostrar as últimas N compras
  lançadas neste cartão (via `fatura_id`/`cartao_id`) diretamente na página de detalhes — hoje
  fica como seção vazia com texto "Disponível quando o histórico de transações existir",
  nunca uma lógica provisória buscando dados que aind a não existem.
- **Tendência de utilização**: um pequeno gráfico de evolução do limite utilizado mês a mês só
  faz sentido com histórico real de faturas fechadas ao longo do tempo — natural quando houver
  mais de 1-2 meses de uso real do app, não implementado agora.
- **"Preciso agir agora" (seção 3, item 5)**: hoje só reage a fatura `ATRASADA`/utilização
  alta. Quando `Transacao` existir, pode also reagir a "gasto incomum este mês" — não
  implementado agora, é só um lugar natural para crescer.

## 14. Auditoria final — checklist antes de finalizar

- [ ] `tsc -b` limpo.
- [ ] `vite build` limpo.
- [ ] Nenhuma regra de negócio ou payload de API alterado (diff de `services/*.ts` deve ser
      vazio ou só cosmético).
- [ ] Hierarquia visual: disponível/percentual são os elementos de maior peso no card e na
      página de detalhes.
- [ ] Card clicável funciona por mouse e teclado (Tab + Enter/Espaço), sem disparar navegação
      ao clicar em um botão da Action Bar.
- [ ] `axe`/verificação manual de contraste nos novos estados de cor (`positive` já é token
      auditado, seção 6.5 do design-system).
- [ ] Responsividade testada nos 3 breakpoints.
- [ ] `prefers-reduced-motion` desliga tilt/glow (já existente) e stagger de entrada do grid.
- [ ] Nenhum import morto (`cartaoTableColumns.tsx` removido, `CartaoVisual layout="compact"`
      removido se de fato sem uso).

## 15. Fora de escopo desta etapa

- Qualquer dado dependente de `Transacao` (seção 13).
- Gráficos de tendência.
- Mudança em `Conta`/`Categoria`/`Tag` (permanecem `DataTable`, apropriado para o volume e
  natureza mais simples dessas entidades — só Cartão ganha o tratamento de "mini dashboard"
  nesta etapa, por ser o objeto mais rico em dado financeiro direto do usuário no momento).
