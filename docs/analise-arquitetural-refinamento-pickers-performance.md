# Análise arquitetural — Refinamento de Pickers + Performance geral

## 0. Escopo

Zero mudança de regra de negócio ou API. Etapa exclusivamente de UX (Pickers) e
performance (auditoria + otimizações medidas, nunca especulativas). Não altera nenhum
contrato de dado, nenhum endpoint, nenhum schema Zod.

## 1. Diagnóstico dos Pickers — causa raiz, não sintoma

`RichPicker` (base de `IconPicker`/`ColorPicker`/`BankPicker`/`CardBrandPicker`) é hoje um
Popover Tier 1 (`docs/analise-arquitetural-overlays.md`, seção 4.2/4.3) posicionado com
`position: absolute` relativo ao próprio gatilho. O gatilho, por sua vez, quase sempre vive
dentro do corpo rolável de um `FormDialog` (`overflow-y-auto`, `docs/design-system.md` seção
15). Um elemento `absolute` é limitado pelo primeiro ancestral com `overflow` diferente de
`visible` — na prática, o painel do picker fica espremido pelo espaço restante dentro do
modal, e por isso precisa de `max-h-96`/`max-h-72 overflow-y-auto` próprios: um scroll dentro
de outro scroll, exatamente o sintoma relatado.

Números reais dos registries por trás de cada picker (contados agora, não estimados):

| Picker | Registry | Itens | Layout atual | Colunas/altura hoje |
|---|---|---|---|---|
| IconPicker | `lib/icons.ts` | 77 ícones | grid | 6 colunas, células 40px, lista com `max-h-72` |
| ColorPicker | `lib/color.ts` (`PALETA_SUGESTAO`) | 44 cores | grid | mesmo grid, painel `w-28` (o mais apertado dos quatro) |
| BankPicker | `lib/institutions.ts` | ~20 instituições + "Outra" | list | `w-80` |
| CardBrandPicker | `lib/bandeiras.ts` | 7 bandeiras | list | `w-80`, sem busca (abaixo do threshold) |

Com 77 itens num grid de 6 colunas a 40px, só ~7 linhas cabem por vez (max-h-72 = 288px) —
o usuário rola dentro do popover, que já está dentro do scroll do próprio `FormDialog`. Isso
confirma o relato ponto a ponto: "pouco espaço", "scroll dentro de scroll", "difícil de
encontrar rapidamente".

`SearchSelect` (base de `CategorySelect`/`AccountSelect`/`CardSelect`), `MultiSelectField`
(base de `TagMultiSelect`), o `Select` genérico e `ColumnVisibility` compartilham exatamente a
mesma arquitetura de popover `absolute` — a mesma classe de problema, só menos grave hoje
porque suas listas costumam ser mais curtas. `docs/analise-arquitetural-overlays.md`, seção 7,
já registrava esta duplicação (cada um reimplementa a mesma mecânica de abrir/fechar/clique-
fora) como dívida técnica pendente — esta etapa é o momento de pagá-la, resolvendo os dois
problemas (UX + duplicação de código) com a mesma mudança.

## 2. Decisão 1 — `position: fixed` com hook compartilhado, não um novo Tier

A escolha não é promover `RichPicker`/`SearchSelect` a Tier 2 (Dialog/Drawer) — isso
quebraria a regra já estabelecida de "nunca dois overlays tier 2 ao mesmo tempo" toda vez que
um picker abrisse dentro de um `FormDialog` já aberto (`docs/analise-arquitetural-overlays.md`,
seção 2), e adicionar um segundo backdrop dentro de um modal já seria mais confuso do que o
problema atual. A causa raiz é puramente geométrica (`absolute` clipado pelo ancestral), não
uma questão de Tier — a correção é geométrica também.

Novo hook `useFloatingPanel` (`hooks/useFloatingPanel.ts`), consolidando a dívida da seção 7
de `overlays.md`:

- Calcula `{ top, left, width }` em coordenadas de VIEWPORT (`getBoundingClientRect` do
  gatilho) uma vez ao abrir — mesmo padrão de cache já usado em `CartaoVisual` (nunca
  recalcula a cada frame/scroll sem necessidade).
- Painel usa `position: fixed` com essas coordenadas em vez de `position: absolute` — escapa
  do clipping de QUALQUER ancestral com `overflow` (o `FormDialog`, uma `Table` com scroll
  horizontal, etc.), sem precisar de `createPortal` (o elemento continua no mesmo lugar da
  árvore DOM, então continua dentro do focus trap do `FormDialog` pai — nenhuma mudança de
  comportamento de acessibilidade).
- Reposiciona em `scroll`/`resize` da janela enquanto aberto (listener leve, sem debounce
  necessário — é só releitura de `getBoundingClientRect`, a mesma operação já cacheada uma
  vez por abertura).
- Continua Tier 1 (sem backdrop, sem focus trap próprio, fecha com `Esc`/clique fora) —
  nenhuma mudança na regra de empilhamento existente, só na geometria.

Consumidores migrados para o hook (parando de duplicar a mecânica, cada um mantendo seu
próprio visual): `RichPicker`, `SearchSelect`, `MultiSelectField`, `Select`,
`ColumnVisibility`. `useDismissableOverlay` (clique fora/`Esc`) continua existindo e é
absorvido pelo novo hook por composição, não duplicado.

## 3. Decisão 2 — `RichPicker` recebe um painel muito maior

- Grid: 6 → 10 colunas (célula 40px → 44px), largura do painel de grid sobe de `w-96`
  (384px) para algo como `560px` — cabe confortavelmente numa tela desktop comum sem virar
  "dropdown gigante" (o painel continua ancorado perto do campo, só maior).
- Lista (`BankPicker`/`CardBrandPicker`): largura sobe de `w-80` (320px) para `~380-400px` —
  mais espaço para nome + monograma sem truncar.
- Altura útil: de `max-h-96`/`max-h-72` fixos para algo como `min(70vh, 480px)` — aproveita a
  tela disponível de verdade em vez de um limite arbitrário pequeno, com UMA área de scroll
  (a lista em si), não duas.
- `ColorPicker` deixa de ser o mais apertado dos quatro (hoje forçado a `w-28` por causa do
  input de hex ao lado) — o painel do picker abre com a largura cheia calculada acima
  (`position: fixed` não herda mais a largura do container `w-28` que só o GATILHO precisa
  ter).
- Hover mais evidente: mantém o `hover:scale-110` já existente, adiciona um anel de foco mais
  visível (`ring-2 ring-accent/40`) no item ativo por teclado, distinguindo claramente
  hover-mouse de navegação-teclado.
- Mobile (`useIsMobileViewport`) continua como hoje (Dialog full-width centralizado) — já
  correto, fora do escopo de mudança.

## 4. Decisão 3 — Busca mais confortável

- Destaque do trecho encontrado: nova função pura `destacarTrecho(texto, query)` em
  `utils/highlight.tsx`, usada no `label` de cada item do `RichPicker`/`SearchSelect` — envolve
  o trecho correspondente num `<mark>` estilizado (`bg-accent-subtle text-accent`, sem cor
  "amarelo genérico de navegador").
- Navegação por teclado (setas/Enter, já existente) e foco automático no campo de busca ao
  abrir (já existente) são mantidos — funcionam corretamente, não precisam de mudança.
- Espaçamento entre grupos aumenta ligeiramente (`mb-2` → `mb-3`, cabeçalho de grupo com mais
  respiro) — o painel maior da Decisão 2 dá espaço de sobra para isso sem custo.

## 5. Consolidação adicional

- `ColumnVisibility` migra para `useFloatingPanel` (hoje duplica seu próprio
  `useEffect`/listener de clique-fora, nem usa o já existente `useDismissableOverlay`) —
  mesmo visual, menos código duplicado.
- Nenhuma mudança em `Drawer`/`FormDialog`/`ConfirmAction` (Tier 2) — fora do escopo, e não
  apresentam o sintoma relatado.

## 6. Auditoria de performance — identificado antes de corrigir

Levantamento real (grep/leitura direta do código, não suposição):

- **Zero code-splitting no projeto inteiro** — nenhuma ocorrência de `React.lazy`/
  `import()` dinâmico em nenhum lugar (confirmado por busca). `routes/AppRoutes.tsx` importa
  todas as páginas (Dashboard, Contas, Cartões, Categorias, Tags, Transações, `/dev/*`)
  estaticamente — o primeiro carregamento da aplicação baixa o código de TODAS as telas, não
  só da que o usuário está vendo.
- **`vite build` já acusa um chunk único de 741KB minificado** (aviso nativo do próprio Vite,
  presente desde a validação da etapa anterior) — consistente com o ponto acima.
- **`ReactQueryDevtools` importado estaticamente em `App.tsx`** — a RENDERIZAÇÃO já é
  condicional a `import.meta.env.DEV`, mas o import estático não é eliminado do bundle de
  produção só por uma condição em runtime; o código do DevTools é empacotado mesmo que nunca
  apareça.
- **Zero uso de `React.memo`/`useCallback` no projeto** (fora de `Provider`s de Context, onde
  já é esperado e correto) — investigado especificamente se algum componente de lista
  (`DataTable`, grid de `CartaoResumoCard`) sofre re-render caro o bastante para justificar
  memoização: `useDataTable` já pagina (20 itens por página por padrão) e usa
  `useDeferredValue` na busca — nenhum ponto real de recálculo caro sobre volume grande foi
  encontrado. Decisão: **não adicionar memo especulativo** sem uma medição real mostrando
  gargalo (evita otimizar por achismo).
- **`getBoundingClientRect` usado em só um lugar do projeto hoje** (`CartaoVisual`), e já com
  cache correto desde a correção de performance da etapa de revisão de UX de Cartões —
  nenhum outro consumidor recalculando layout a cada frame/scroll.
- **Invalidação de query de Transação** (etapa anterior) é deliberadamente ampla — uma
  transação nova pode mudar saldo de Conta, limite de Cartão e/ou Fatura, então invalida
  praticamente todo o Dashboard. Já documentada e justificada por corretude; nenhuma mudança
  proposta aqui sem evidência real de lentidão perceptível causada por isso.
- **Animações**: revisão do `lib/motion.ts` e dos consumidores de `motion/react` não encontrou
  nenhuma animação de layout pesada nova além da já corrigida em `CartaoVisual` — a maioria
  anima só `opacity`/`transform` (propriedades compositadas, não forçam reflow), conforme já
  documentado em `docs/motion-principles.md`.

## 7. Otimizações a aplicar (com causa identificada)

- **Code-splitting por rota** — `React.lazy` + `Suspense` em `AppRoutes.tsx`, um chunk por
  página. Reduz o JavaScript baixado no primeiro acesso: um usuário que só abre o Dashboard
  não precisa mais baixar o código de `/transacoes`, `/cartoes/:id`, `/dev/*` etc. de
  imediato.
- **`ReactQueryDevtools` via import dinâmico** condicionado a `import.meta.env.DEV` — remove
  o código do DevTools do bundle de produção por completo, não só da árvore renderizada.
- **Fallback de `Suspense`**: um skeleton simples (reaproveita `Skeleton`/`LoadingCard` já
  existentes) — nenhum componente de loading novo.

## 8. Fora de escopo (explicitamente)

- Reavaliar/afinar a invalidação de queries de Transação sem medição real de lentidão.
- Virtualização de listas — nenhuma lista do projeto hoje renderiza volume irrestrito
  (`DataTable` já pagina; `/transacoes` já limita por período, ver
  `docs/analise-arquitetural-transacao-frontend.md`, seção 2).
- Bundle analyzer completo / `manualChunks` fino por biblioteca — avaliar depois que o
  code-splitting por rota (o gargalo mais visível e mais barato de corrigir) já estiver em
  produção.
- Promover qualquer Picker a Tier 2 (Dialog/Drawer) — decisão explícita pela seção 2: o
  problema é geométrico, não de Tier.

## 9. Auditoria final planejada

Ao final da implementação: `tsc -b`, `vite build` (comparar tamanho/composição dos chunks
antes/depois — espera-se múltiplos chunks menores em vez de um único de 741KB), teste manual
dos quatro pickers (`IconPicker`/`ColorPicker`/`BankPicker`/`CardBrandPicker`) e de
`CategorySelect`/`AccountSelect`/`CardSelect`/`TagMultiSelect` dentro de um `FormDialog` real,
documentação do impacto esperado em fluidez (relatório de encerramento, formato já usado nas
etapas anteriores).
