# Análise Arquitetural — Overlays (Design System)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Formaliza, num único
lugar, o padrão para **todo** elemento que aparece "por cima" da interface: `Tooltip`,
`Popover`, `RichPicker` (`docs/analise-arquitetural-rich-pickers.md`), `Dialog`, `Drawer`
(`docs/analise-arquitetural-fatura-frontend.md`), Context Menu e Command Palette. Pedido
explícito do usuário ao aprovar os documentos anteriores: em vez de cada documento
especificar seu próprio overlay isoladamente (o que já estava começando a acontecer — Rich
Pickers definia o fallback mobile do popover, Fatura definia o `Drawer` do zero), existe **uma
fonte canônica só**, e os demais documentos apontam para cá.

`docs/analise-arquitetural-rich-pickers.md` e `docs/analise-arquitetural-fatura-frontend.md`
são atualizados para referenciar este documento em vez de duplicar as regras abaixo.

## 1. Por que um documento por si só

Overlay é a categoria de componente com mais chance de o projeto acumular pequenas
inconsistências (um popover com sombra diferente de outro, um modal que fecha com `Esc` e
outro que não, um z-index que colide) — cada um nasceu num documento de entidade diferente
até agora (`FormDialog`/`DeleteDialog` na F2, `Select`/`Combobox` também na F2, `RichPicker`
e `Drawer` nesta preparação de F10). Este documento não introduz nada visualmente novo — é a
consolidação do que já foi decidido, mais a extensão explícita para os dois tipos que ainda
não tinham especificação nenhuma (Context Menu, Command Palette).

## 2. Dois tiers, uma regra de empilhamento por tier

Todo overlay do projeto pertence a um de dois tiers. A regra de "nunca dois overlays ao mesmo
tempo" (já existente para `FormDialog`, seção 22 de `docs/design-system.md`) **vale só dentro
do mesmo tier** — um overlay leve (tier 1) pode aparecer sobre um overlay pesado (tier 2) já
aberto, porque não compete pela mesma atenção/bloqueio de interação.

### Tier 1 — leve, ancorado, não bloqueia

`Tooltip`, `Popover`, `RichPicker` (que é um `Popover` especializado), Context Menu. Nunca tem
backdrop nem focus trap. Fecha sozinho (`Esc`, clique fora, seleção de item) sem afetar
qualquer outro overlay já aberto por trás. **Pode abrir de dentro de um overlay tier 2** (ex.
um `RichPicker` de campo dentro de um `Drawer`, um `Tooltip` dentro de um `Dialog`) — z-index
sempre acima do tier 2 mais alto já aberto no momento (ver seção 6).

### Tier 2 — pesado, bloqueia, um por vez

`Dialog` (`FormDialog`/`DeleteDialog`), `Drawer`, Command Palette. Sempre com backdrop +
focus trap + só um aberto por vez **entre si** (regra já existente, agora explicitamente
estendida a `Drawer` e Command Palette): abrir um segundo overlay tier 2 enquanto um já está
aberto **substitui o conteúdo do primeiro** (mesmo padrão que `FormDialog` já usa para uma
confirmação de exclusão dentro de um formulário) — nunca empilha um modal sobre outro modal,
nem um drawer sobre um modal.

## 3. Quando usar qual — a heurística de decisão (regra permanente)

Promovida de `docs/analise-arquitetural-rich-pickers.md` (seção 1.1, agora removida de lá em
favor desta seção canônica) — pedido explícito do usuário, vale para **toda** interação
futura do projeto, não só pickers:

Sempre que uma interação exigir mais de 2 cliques para completar, ou a visualização ficar
comprometida pelo espaço disponível (texto cortado, grade apertada, opção sem espaço para
mostrar o que precisa), avaliar nesta ordem:

1. **Tooltip** — não é uma escolha, é só informação complementar sob hover/foco. Usado quando
   o problema é "falta contexto", não "falta espaço para escolher".
2. **Popover** — quando o conjunto de opções é pequeno e cabe ancorado ao campo/botão que o
   abriu, sem precisar de mais contexto que isso (ex. `RichPicker`).
3. **Dialog** — quando a escolha/ação precisa de mais espaço ou contexto que um popover
   comporta, ou acontece fora de um formulário (ex. confirmar uma ação destrutiva, editar uma
   entidade inteira).
4. **Drawer** — quando o conteúdo é uma lista que pode crescer e cada item pode ter suas
   próprias ações, sem justificar tomar a tela inteira (ex. detalhes/ações de um item dentro
   do contexto de uma página maior).
5. **Context Menu** — quando a escolha é um conjunto curto de *ações* (não valores) sobre um
   elemento específico, disparado por clique-direito ou por um botão "mais opções" — nunca
   para selecionar um valor de formulário (isso é sempre `Popover`/`RichPicker`/`Select`).
6. **Command Palette** — quando o conjunto é grande, heterogêneo, e busca é o caminho
   principal (o usuário já sabe o que quer digitar) — reservado para `Cmd/Ctrl+K`
   (`docs/design-system.md`, seção 3), ainda não implementado no projeto.

Nunca manter um `Select`/lista simples só por já ser o caminho mais rápido de implementar.

## 4. Especificação por tipo

Todos compartilham a base de superfície/sombra/blur já definida em `docs/design-system.md`
(seções 6.1, 11, 12) — nenhum overlay usa uma cor ou elevação fora dessa escala.

### 4.1 Tooltip

Já especificado (`docs/design-system.md`, seção 14) — `--color-surface-4`, `--text-caption`,
delay de 400ms, `--duration-base`/`--ease-out`. Sem mudança, incluído aqui só para completar a
família.

### 4.2 Popover

Base de `IconField`/`ColorField`/`SearchSelect` hoje, formalizada como padrão nomeado (não um
componente novo — os três já fazem exatamente isto, cada um reimplementando a mesma mecânica
de abrir/fechar/posicionar; ver seção 7 sobre consolidar isso numa única implementação):
`--color-surface-3`, `--shadow-md`, `--radius-lg`, ancorado ao elemento que o abre (`mt-1`,
mesmo lado). Entrada/saída: fade + 4px slide, `--duration-base`/`--ease-out` na entrada,
`--duration-fast`/`--ease-in` na saída (já correto em todos os três consumidores atuais, sem
mudança). Fecha com `Esc`/clique fora. `RichPicker` (seção 4.3) é este mesmo padrão com
conteúdo mais rico.

### 4.3 RichPicker

Especificação completa em `docs/analise-arquitetural-rich-pickers.md` — é um `Popover` com
busca, grupos, grid/lista e navegação por teclado adicionais. Não repetido aqui.

### 4.4 Dialog (`FormDialog`/`DeleteDialog`)

Já especificado (`docs/design-system.md`, seção 15/22) — `--color-surface-4`, `--radius-xl`,
`--shadow-xl`, backdrop `--blur-lg` sobre `rgba(11,11,13,0.6)`, `scale(0.96→1) + fade` na
entrada (spring `smooth`), focus trap, foco retorna ao gatilho ao fechar. Sem mudança.

### 4.5 Drawer (novo — primeiro consumidor: Fatura, seção 5)

- Ancorado à borda direita da tela, `480px`/`30rem` de largura (tela inteira abaixo de `md`,
  mesmo breakpoint dos demais overlays).
- Mesma superfície/sombra/blur do `Dialog` (`--color-surface-4`/`--shadow-xl`/`--blur-lg`) —
  só a geometria muda (retângulo vertical ancorado à borda em vez de caixa centralizada).
- Entrada: desliza da borda (`x: "100%" → 0`) + fade do backdrop, spring `smooth` — "vem de
  onde logicamente vem" (`docs/motion-principles.md`, seção 5.1): um drawer aberto a partir de
  uma ação específica vem da borda da tela, nunca do centro.
- Saída: trajetória invertida, `--ease-in`, ~70% da duração da entrada.
- Fecha com `Esc`, clique no backdrop, botão de fechar; focus trap + retorno de foco, mesma
  regra do `Dialog`.
- Tier 2: nunca aberto ao mesmo tempo que um `Dialog`/outro `Drawer`/Command Palette (seção 2).

### 4.6 Context Menu (novo — reservado, nenhum consumidor ainda)

Nenhuma tela do projeto usa clique-direito ou um menu de ações contextuais hoje (`RowActions`
do `DataTable` já cobre "ações sobre uma linha" com ícones visíveis no hover — um Context Menu
só se justifica quando as ações forem numerosas demais para caber como ícones, ou quando fizer
sentido oferecer clique-direito de verdade). Especificado agora para não inventar um padrão
ad-hoc no dia em que for necessário:

- Mesma superfície de `Popover` (`--color-surface-3`, `--shadow-md`, `--radius-lg`), lista
  vertical de itens (label + ícone opcional + atalho `Kbd` opcional à direita), sem grid.
- Posicionado na coordenada do clique-direito (ou embaixo do botão "mais opções" que o abriu),
  nunca centralizado na tela.
- Mesmo tratamento de entrada/saída do `Popover` (fade + 4px slide).
- Fecha com `Esc`, clique fora, ou seleção de um item — nunca precisa de confirmação própria
  (uma ação destrutiva dentro do menu abre um `Dialog`/`DeleteDialog` de confirmação, mesmo
  padrão já usado por `RowActions`).

### 4.7 Command Palette (novo — reservado, nenhum consumidor ainda)

Já citado como reservado desde `docs/design-system.md` (seção 3, `Cmd/Ctrl+K`) e seção 12
(único elemento que usa `--blur-xl`) — nenhuma implementação ainda, especificado aqui para
quando um recurso de busca/comando global for construído:

- Modal centralizado, mas maior e mais alto que um `Dialog` comum (até `640px` de largura),
  `--blur-xl` no backdrop (o único overlay que usa esse nível — reservado, seção 12 do
  design-system), input de busca fixo no topo, lista de resultados abaixo com scroll.
- Entrada/saída idênticas ao `Dialog` (`scale(0.96→1) + fade`, spring `smooth`).
- Tier 2 — mesma regra de exclusividade mútua.

## 5. Consumidores já decididos (referência cruzada, não redefinidos aqui)

- **`RichPicker`** (`IconPicker`/`ColorPicker`/`BankPicker`/`CardBrandPicker`) —
  `docs/analise-arquitetural-rich-pickers.md`.
- **`Drawer`** — primeiro uso real: detalhes/ações de uma fatura individual, a partir da nova
  página de detalhes do Cartão (`docs/analise-arquitetural-fatura-frontend.md`, atualizado
  após esta análise para refletir a decisão de página de detalhes em vez de um único drawer
  gerenciando a lista inteira).

## 6. Coordenação de z-index

Camadas, da mais baixa para a mais alta (nenhum valor mágico solto pelo código — uma escala
única em `index.css`, mesmo espírito de `--color-surface-*`):

1. Conteúdo normal da página.
2. `Dialog`/`Drawer`/Command Palette (tier 2) + seus respectivos backdrops.
3. `Tooltip`/`Popover`/`RichPicker`/Context Menu (tier 1) — sempre acima de qualquer tier 2
   já aberto, para que um `RichPicker` dentro de um `Drawer` nunca fique escondido atrás do
   próprio `Drawer`.
4. Toast (sempre a camada mais alta — precisa ser visível mesmo com um modal aberto por trás,
   ex. erro de submit de um formulário dentro de um `Dialog`).

## 7. Consolidação técnica (nota de implementação, não de design)

`IconField`/`ColorField`/`SearchSelect` hoje **cada um reimplementa** a mecânica de
abrir/fechar/clique-fora/`Esc`/posicionamento do `Popover` (três cópias quase idênticas do
mesmo `useEffect` de listeners). Ao construir `RichPicker` (que também precisa dessa mesma
mecânica), a decisão é extrair um hook interno compartilhado — `usePopoverState` ou
equivalente, só a lógica de estado/eventos, não um componente visual novo — para os quatro
consumidores (`IconPicker`/`ColorPicker` migrados, `SearchSelect`, `RichPicker`) pararem de
duplicar o mesmo código. Detalhe de implementação (seção "Fora de escopo de design"), não uma
decisão visual — mencionado aqui só para não ser esquecido quando a implementação começar.

## 8. Fora de escopo (explicitamente)

- Implementar Context Menu ou Command Palette agora — nenhum consumidor real ainda (seções
  4.6/4.7 existem para não inventar o padrão depois, sob pressão, sem tempo de pensar).
- Um sistema de posicionamento genérico tipo Floating UI/Popper — o projeto já resolve
  ancoragem com `absolute`/`mt-1` simples nos três consumidores atuais, suficiente para
  overlays sempre abertos a partir de um campo/botão na mesma área visível (nunca precisou
  lidar com colisão de viewport além do `max-w-[90vw]` já usado) — se um Context Menu ou
  Command Palette futuro precisar de posicionamento mais sofisticado, reavaliar então.

## 9. Critérios de pronto

- `Dialog`, `Drawer` e `Popover`/`RichPicker` nunca aparecem dois tier-2 ao mesmo tempo.
- Um `Popover`/`RichPicker` tier-1 aberto de dentro de um `Drawer` renderiza acima dele
  (z-index correto).
- Todo overlay respeita `Esc`, clique fora, foco preso (tier 2) ou não (tier 1), e
  `prefers-reduced-motion`.

## 10. Próximos passos

Aguardando aprovação — já concedida pelo usuário junto com o ajuste de IA de Fatura (página de
detalhes do Cartão em vez de um drawer único). Implementação segue a ordem já registrada nos
demais documentos de F10, começando pela infraestrutura de overlay (`Drawer` novo,
consolidação do `Popover`) antes de qualquer tela específica.
