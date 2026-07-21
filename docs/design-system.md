# Design System — Finanças Pessoais

Documento de design puro — **nenhum código é escrito nesta etapa**. Define a identidade
visual, a linguagem de interação e as regras de uso de cada padrão antes da Etapa F2
(Design System) começar a implementar. Convenção: a Etapa F2 lê este documento como a
Etapa F1 leu `docs/analise-arquitetural-frontend.md` — nada aqui é implementado sem este
documento existir primeiro.

## 0. Decisões que expandem a arquitetura já aprovada

`docs/analise-arquitetural-frontend.md` fechou a stack em React + TypeScript + Vite +
Tailwind + React Router (+ React Query, React Hook Form, Zod, aprovados depois). Projetar um
sistema visual no nível pedido (Linear/Raycast/Vercel/Framer, "premiado no Awwwards")
genuinamente precisa de mais três coisas que não estavam nessa lista. Cada uma foi
consultada antes de decidir, como pedido:

1. **`motion` (Framer Motion)** — biblioteca de animação. **Aprovado por você nesta
   conversa.** Sem ela, orquestrar entrada/saída, layout animations e spring physics no
   nível dos produtos citados exigiria uma quantidade grande de JS/CSS manual, frágil e
   difícil de manter — exatamente o tipo de esforço que uma lib pequena e madura resolve
   bem. Usada com moderação: a maior parte da interface usa CSS puro (seção 12); `motion`
   entra só onde a coreografia genuinamente precisa dela (listas com stagger, layout
   animations automáticas, modais, o número animado dos cards do dashboard).
2. **`lucide-react`** — set de ícones. **Aprovado por você nesta conversa.** Stroke-based,
   grade consistente, é o set usado por shadcn/ui e boa parte dos produtos com essa estética;
   tree-shakeable (só o ícone importado entra no bundle).
3. **Fonte via `@fontsource-variable` (self-hosted, sem chamada externa)** — decisão minha,
   sinalizada aqui em vez de travar a conversa por algo de baixo risco (é um asset, não
   lógica): ver seção 7 para a fonte escolhida e a justificativa.

**Um quarto ponto, esse sim uma reinterpretação de algo já decidido — sinalizado com
destaque:** `docs/analise-arquitetural-frontend.md` (seção 15) listava "dark mode" como
fora de escopo. Lida literalmente contra o pedido desta etapa (visual no nível de
Linear/Raycast/Vercel/Framer — todos dark-first), a leitura que faz sentido é: **o que
estava fora de escopo era construir um TOGGLE claro/escuro** (feature dobrada, ninguém além
de você usa este app, não há necessidade de dar a opção). Não estava implícito "a interface
tem que ser clara". Decisão desta etapa: **a aplicação é dark-only, sem toggle** — isso é
*menos* trabalho que suportar os dois temas (mantém a etapa fiel a "fora de escopo: dark
mode" no sentido de não construir a feature de alternância) e entrega exatamente a estética
pedida. Os tokens de cor (seção 6) são estruturados como variáveis CSS para não fechar a
porta a um tema claro no futuro, se um dia fizer sentido — mas nenhum código de alternância
é construído agora. **Se você queria um toggle de verdade, ou preferia claro como padrão,
me avise antes de eu seguir para a implementação.**

**Atualização (Etapa de Refinamento Visual, pós-F6):** o toggle de verdade foi pedido
explicitamente pelo usuário. A decisão "dark-only sem toggle" acima documenta por que a
etapa original não construiu a feature — não que ela nunca deveria existir. Implementado
em `[data-theme="light"]` (`src/index.css`) + `contexts/ThemeContext.tsx`, acessível pelo
`ThemeToggle` dentro do menu do usuário (`UserMenu`, `components/layout/`). Dark continua
o padrão para quem nunca escolheu nada. Ver `docs/revisao-tecnica-branding-e-microinteracoes.md`
para o detalhamento completo (paleta clara, decisões de contraste, etc.).

**Ajuste de direção estética aprovado após revisão deste documento (registrado aqui para o
histórico da decisão):** dark-only, `motion` e `lucide-react` seguem confirmados, assim como
a identidade "confiança silenciosa" (seção 1) — inalterados. O que muda é o *raio* da
inspiração: em vez de ancorar majoritariamente em Linear/Vercel, a referência se abre para
motion design e polish de nível Awwwards, com o objetivo explícito de uma **identidade
visual própria** — não a soma reconhecível de produtos existentes. A tabela de referências
da seção 4 foi reescrita nesse espírito, e a especificação detalhada de motion foi
promovida a documento próprio: `docs/motion-principles.md`, criado especificamente para
essa mudança de direção e agora a fonte canônica de timing/curva/estado de qualquer
animação do projeto (a seção 10 deste documento passa a ser um resumo que aponta para lá).

**Atualização (Ajustes de UX/UI que precederam a Etapa F9 — Cartão):** dois pedidos do
usuário, ambos implementados sem alterar a arquitetura já aprovada:

1. **Escala global da interface (~20-25% maior)** — todos os valores de tipografia (seção 7)
   e radius (seção 9) em `index.css` foram multiplicados por `--ui-scale: 1.2` (documentado
   na própria variável, com o valor "Padrão" original preservado em comentário ao lado de
   cada linha, só como referência histórica). Espaçamento/altura/largura (`p-*`/`gap-*`/
   `h-*`/`w-*` do Tailwind, seção 8) usam o MESMO multiplicador `1.2`, mas resolvido em
   `tailwind.config.js` (`theme.spacing` sobrescrito a partir de `tailwindcss/defaultTheme`
   × `UI_SCALE`), não via a variável CSS — Tailwind não lê `var(--ui-scale)` de forma
   confiável dentro de `theme.spacing` (afetaria utilities negativas geradas
   automaticamente, ex. `-mt-1`). Resultado: nenhum componente existente precisou de
   alteração — a escala inteira do Design System cresceu de uma vez, no token, não em cada
   uso. Uma futura preferência real de densidade (Compacto/Padrão/Confortável) é a evolução
   natural deste mecanismo: trocar o bloco por `[data-density]` (mesmo padrão de
   `[data-theme]`) e o `UI_SCALE` do Tailwind por `calc(valor * var(--ui-scale))` — não
   implementado agora porque exige teste em navegador real antes de ativado (indisponível
   neste ambiente de desenvolvimento) e o pedido original já vem com essa ressalva
   ("se aumentar muito a complexidade, apenas reorganize os tokens").
2. **Cartão de crédito com visual de "carteira digital premium"** — nova peça de
   apresentação (`CartaoVisual`, seção 15) com proporção real de cartão físico
   (`aspect-[1.586/1]`), gradiente de marca da instituição (`lib/cardThemes.ts`, novo
   registry, mesmo espírito de `lib/institutions.ts`), tilt 3D + glow seguindo o mouse
   (`docs/motion-principles.md`, nova seção sobre o padrão). `ProgressBar` (seção 15) ganhou
   uma prop `tone` (`accent`/`warning`/`negative`) para o "progresso do limite" reagir à
   proximidade do limite — evolução do componente existente, não um componente paralelo.

## 1. Filosofia de design

**"Confiança silenciosa."** Não é um dashboard bancário que precisa parecer sério para
convencer alguém a confiar dinheiro nele (você já confia — é seu próprio sistema). Não é um
produto de consumo que precisa parecer amigável e óbvio para converter um usuário
desconhecido. É uma ferramenta pessoal de uso diário, no mesmo espírito de Linear (gestão de
projeto que parece rápida e precisa) ou Raycast (utilitário que é um prazer abrir toda hora).
O objetivo emocional: abrir o app todo dia e sentir que foi bem-feito, sem esse sentimento
depender de nenhum efeito chamativo — a beleza vem de precisão (alinhamento, espaçamento,
tipografia, timing de animação), não de decoração.

Isso não significa imitar Linear ou qualquer outro produto específico. A inspiração é
deliberadamente mais ampla — motion design e acabamento de nível Awwwards (seção 4) somam-se
a essa base para formar uma identidade visual própria deste projeto, com sofisticação vindo
de coreografia, timing e microinteração bem calibrados (`docs/motion-principles.md`), nunca
de um efeito emprestado reconhecível de outro produto.

Três princípios não-negociáveis, nessa ordem de prioridade quando qualquer decisão de design
entrar em conflito:

1. **Clareza do dado financeiro sempre vence.** Nenhuma escolha estética pode introduzir
   ambiguidade sobre um valor monetário, uma data de vencimento ou um status de pagamento.
   Cor, contraste, alinhamento numérico e hierarquia tipográfica em torno de dinheiro são
   tratados como parte da usabilidade, não da decoração.
2. **Densidade de informação de "ferramenta profissional", não de "app de consumo".** Este
   projeto lida com 14 entidades de domínio e um usuário que vai olhar isso todo dia — o
   design se inspira em ferramentas de trabalho (Linear, Raycast, editores de código) mais
   do que em apps de consumo com tipografia grande e muito espaço em branco. Fonte-base
   pequena (14px), tabelas densas, mas nunca apertado a ponto de cansar.
3. **Todo efeito visual precisa justificar seu custo de manutenção.** Motion, blur e
   glassmorphism são ferramentas usadas com intenção específica (seções 10-12), nunca
   aplicadas "porque fica bonito" em superfícies onde atrapalhariam a leitura de um número.

## 2. Linguagem visual

- **Dark-only**, base grafite (nunca preto puro — ver seção 6), com UM acento de cor
  (índigo-violeta) reservado para interação/marca, e cores semânticas (verde/vermelho/âmbar)
  reservadas exclusivamente para significado financeiro (positivo/negativo/pendente) — nunca
  usadas decorativamente, para que o usuário aprenda rápido "se está verde ou vermelho, é
  dinheiro" e nunca mais precise pensar sobre isso.
- **Bordas finas (hairline) em vez de sombras pesadas** para separar superfícies — a
  assinatura visual de Linear/Raycast: painéis se distinguem do fundo por uma borda de baixa
  opacidade + uma leve variação de luminosidade, não por sombra dramática. Sombra existe
  (seção 11), mas é reservada para elementos que literalmente flutuam sobre o conteúdo
  (modais, dropdowns, toasts).
- **Números tabulares, sempre.** Toda cifra monetária ou tabela numérica usa fonte
  monoespaçada com features tabulares (seção 7) — alinhamento perfeito em colunas é tratado
  como requisito de usabilidade financeira, não capricho tipográfico.
- **Cantos precisos, não arredondados-demais.** Raio pequeno em controles (botão, input),
  raio médio em cards — nunca o estilo "pill" exagerado de apps de consumo (exceto onde
  `full` é semanticamente correto: avatar, badge, switch).
- **Motion como confirmação, não como espetáculo.** Toda animação existe para responder a
  uma pergunta do usuário ("meu clique registrou?", "de onde veio esse painel?", "esse valor
  mudou?") — nunca decorativa/gratuita. Ver seção 10.

## 3. Princípios de UX

1. **Teclado em primeiro lugar.** Usuário único, uso diário — vale a pena investir em
   atalhos de teclado desde o início (Cmd/Ctrl+K para busca/comando, `Esc` fecha qualquer
   overlay, `Enter` confirma o formulário focado, setas navegam listas/tabelas). Ver
   `Kbd`/Command Palette na seção 14.
2. **Feedback imediato, nunca silencioso.** Toda ação (criar, editar, excluir, pagar
   parcela) tem uma resposta visível em menos de 100ms (estado de loading do botão) e uma
   confirmação clara ao terminar (toast, atualização otimista quando seguro, nunca um
   "nada aconteceu visualmente" enquanto uma requisição roda por trás).
3. **Densidade sem sacrificar respiração.** Tabelas e listas são densas (linha de ~40-44px),
   mas nunca comprimidas a ponto de números/textos quase se tocarem — espaçamento interno
   consistente com a escala da seção 8.
4. **Erros são específicos e acionáveis**, nunca genéricos — herda diretamente do que já foi
   decidido em `docs/analise-arquitetural-frontend.md` (seção 8: 422 vira mensagem de campo
   quando possível), e este documento define como isso aparece visualmente (seção 21).
5. **Nada de dados financeiros "pulando".** Skeletons reservam o espaço exato do conteúdo
   final (seção 20) — layout shift em uma tela de dinheiro é o tipo de detalhe que quebra a
   sensação de "confiança silenciosa" da seção 1.

## 4. Referências e o que é herdado de cada uma

Estudadas pelo que ensinam sobre um princípio específico, não copiadas literalmente — e
combinadas de um jeito que não replica nenhuma delas inteira. O teste de "identidade
própria" usado em cada decisão desta seção: se alguém reconhecesse a interface e dissesse
"isso é o Linear" ou "isso é a Vercel", a decisão falhou; o objetivo é que a combinação em si
seja específica deste projeto.

| Referência | O que herdamos | O que NÃO herdamos |
|---|---|---|
| **Linear** | bordas hairline em vez de sombra pesada, paleta grafite muito controlada, um único acento de cor, densidade de informação, fonte compacta, `Kbd`/atalhos como cidadão de primeira classe | o acento roxo-azulado exato deles (o nosso é levemente diferente, ver seção 6) |
| **Raycast** | command palette como padrão de interação central, microinterações muito rápidas (150-200ms), ícones stroke consistentes | o tema de cor (Raycast usa vermelho como acento; aqui reservamos vermelho para "despesa/negativo") |
| **Vercel** | monocromia como base + acento mínimo, tipografia (a família Geist é literalmente da Vercel, ver seção 7), grid limpo, uso de blur em headers com scroll | o branco-puro-no-claro como tema principal (somos dark-only) |
| **Framer** | motion como linguagem central (spring physics, layout animations), transições de página suaves | a densidade de efeitos visuais de uma landing page de marketing — este é um dashboard de uso diário, não uma vitrine |
| **Motion design premiado (Awwwards, geral)** | precisão de timing e coreografia (não quantidade de efeito), curvas com sensação física real, micro-detalhes de polish (hover states com profundidade sutil), a disciplina de fazer poucos efeitos muito bem calibrados — ver `docs/motion-principles.md` para o tratamento completo | qualquer efeito pensado para impressionar numa primeira visita (scroll-jacking, parallax grande, reveals a cada scroll) — o padrão "site vitrine" prioriza impacto na primeira vez; este app prioriza ser agradável na centésima vez |
| **Apple (HIG / motion de sistema)** | resposta imediata a toque/clique antes de qualquer animação maior, spring física em vez de curva artificial | a abundância de profundidade/parallax entre camadas visuais |
| **Stripe (produto/dashboard, não o site de marketing)** | como comunicar mudança de valor numérico com precisão e discrição, transições de estado de formulário suaves | o volume de motion do site institucional, que não é o produto |
| **Bento grids / glassmorphism (tendência de dashboard 2024-2025)** | bento grid para o layout do dashboard, glass aplicado com moderação em overlays (seção 12) | glass ou efeito decorativo em qualquer superfície que compita com a leitura de um número — regra dura, seção 1 |

Nenhum produto citado acima é copiado como um todo — cada um contribui um princípio isolado,
e a combinação (paleta, tipografia, timing, coreografia) é a identidade própria deste
projeto. Detalhamento de motion (o eixo mais específico dessa identidade) vive inteiramente
em `docs/motion-principles.md`, não duplicado aqui.

## 5. Design tokens — arquitetura

Todos os tokens abaixo (cor, tipografia, espaçamento, radius, sombra, blur, motion) são
implementados como **CSS custom properties** no `:root` (não só valores hardcoded no
`tailwind.config.js`), com o Tailwind configurado para ler dessas variáveis
(`colors: { bg: { DEFAULT: 'var(--color-bg)', ... } }`). Motivo: variáveis CSS podem ser
trocadas em runtime sem rebuild (relevante se um tema claro for adicionado no futuro, ver
seção 0) e são a forma mais direta de manter um único "source of truth" que tanto
Tailwind quanto `motion` (que às vezes anima valores fora do Tailwind, ex. um `boxShadow`
customizado) conseguem ler. Nomenclatura: `--<categoria>-<nome>`, ex. `--color-surface-2`,
`--space-4`, `--radius-lg`, `--shadow-md`, `--ease-out`.

## 6. Sistema de cores

### 6.1 Superfícies (dark, base grafite — nunca preto puro)

| Token | Valor | Uso |
|---|---|---|
| `--color-bg` | `#0B0B0D` | fundo da aplicação |
| `--color-surface-1` | `#131316` | sidebar, header, painéis elevados de primeiro nível |
| `--color-surface-2` | `#18181C` | cards, linhas de tabela em hover |
| `--color-surface-3` | `#212126` | popovers, dropdowns, inputs em foco |
| `--color-surface-4` | `#27272D` | modais, superfície mais alta da aplicação |
| `--color-border-subtle` | `rgba(255,255,255,0.06)` | divisórias internas discretas (linhas de tabela) |
| `--color-border-default` | `rgba(255,255,255,0.10)` | borda padrão de card/painel/input |
| `--color-border-strong` | `rgba(255,255,255,0.16)` | borda em foco/hover intencional |

### 6.2 Texto

| Token | Valor | Uso |
|---|---|---|
| `--color-text-primary` | `#F5F5F7` | texto principal (nunca branco puro — mais suave para leitura prolongada) |
| `--color-text-secondary` | `#A1A1AA` | texto de apoio, labels preenchidas |
| `--color-text-tertiary` | `#6E6E76` | placeholder, labels de campo, timestamps |
| `--color-text-disabled` | `#45454B` | texto/ícone desabilitado |
| `--color-text-on-accent` | `#FFFFFF` | texto sobre superfície de acento sólido |

### 6.3 Acento (marca/interação) — reservado para interação, nunca para dado financeiro

| Token | Valor | Uso |
|---|---|---|
| `--color-accent` | `#6D5EF5` | ação primária, link, foco, item de navegação ativo, série principal de gráfico |
| `--color-accent-hover` | `#7D70F7` | hover de elemento de acento |
| `--color-accent-active` | `#5B4DE0` | pressed/active |
| `--color-accent-subtle` | `rgba(109,94,245,0.12)` | fundo de estado selecionado/hover discreto (ex. item de menu ativo) |
| `--color-accent-ring` | `rgba(109,94,245,0.45)` | anel de foco (`focus-visible`) |

Índigo-violeta deliberadamente: é a família de cor "software premium" (Linear/Framer estão
nessa vizinhança), e — ponto importante para um app financeiro — não compete visualmente com
verde/vermelho semânticos abaixo. Um acento verde ou vermelho obrigaria a inventar uma
segunda cor só para "ação" vs. "dinheiro positivo/negativo", ambiguidade que este token evita
de propósito.

### 6.4 Semânticas financeiras — únicas cores com significado fixo no app inteiro

| Token | Valor | Significado | Uso |
|---|---|---|---|
| `--color-positive` | `#34D399` | receita, saldo positivo, meta atingida | valor de RECEITA, `saldo_atual` ≥ 0, badge de fatura PAGA |
| `--color-positive-subtle` | `rgba(52,211,153,0.12)` | fundo de badge/chip positivo | |
| `--color-negative` | `#FB7185` | despesa, saldo negativo, atraso | valor de DESPESA, `saldo_atual` < 0, badge ATRASADA |
| `--color-negative-subtle` | `rgba(251,113,133,0.12)` | fundo de badge/chip negativo | |
| `--color-warning` | `#FBBF24` | pendente, aguardando ação | badge PENDENTE, fatura PARCIALMENTE_PAGA, alerta de vencimento próximo |
| `--color-warning-subtle` | `rgba(251,191,36,0.12)` | fundo de badge/chip de aviso | |
| `--color-info` | `#38BDF8` | informativo, em andamento (nem sucesso nem alerta) | badge ABERTA (fatura), ATIVO (financiamento/empréstimo) |
| `--color-info-subtle` | `rgba(56,189,248,0.12)` | fundo de badge/chip informativo | |

**Regra dura, sem exceção:** estas quatro cores (positive/negative/warning/info) só aparecem
vinculadas ao significado da tabela acima. Nunca usadas para decorar um elemento sem relação
com dinheiro/status — é o que garante que o usuário nunca precise "pensar" sobre o que uma
cor significa neste app. `info` foi adicionado na revisão de UX de Cartões
(`docs/analise-arquitetural-revisao-ux-cartoes.md`, "sistema semântico de status") para dar a
um estado "em andamento, sem alerta" (ex. fatura `ABERTA`) uma cor própria em vez de cair em
`neutral` por falta de opção — `neutral` (cinza) fica reservado para o que é de fato
inativo/sem estado (ex. `AtivoBadge` de um cadastro desativado).

**Funções puras de decisão de tone** (`frontend/src/utils/status.ts`, reutilizáveis por
qualquer entidade, não só Cartão): `tonePorUtilizacao(percentual)` decide o tone de um
limite/orçamento utilizado (positive < 80% ≤ warning < 100% ≤ negative); `tonePorPrazo(dias)`
decide o tone de urgência de um prazo (negative ≤ 1 dia, warning ≤ 7 dias, info daí em
diante). Nenhuma tela deve reimplementar esse limiar com seu próprio ternário — é a mesma
régua para Fatura hoje e para Transação/Parcelamento/Conta Recorrente/Financiamento/
Empréstimo/Meta quando cada um precisar de um indicador equivalente.

**`StatusChip` vs. `Badge`:** `Badge` (fundo `-subtle`/translúcido) pressupõe estar sobre a
superfície neutra do app; `StatusChip` (`components/ui/StatusChip.tsx`) tem fundo SÓLIDO
(cor semântica cheia) com o texto resolvido por um token dedicado por semântica
(`--color-text-on-positive/negative/warning/info`, mesmo princípio de `--color-text-on-accent`)
— usar sempre que a informação for desenhada sobre um fundo que o componente não controla
(ex. o gradiente de marca de um `CartaoVisual`), onde `Badge` translúcido perderia contraste
dependendo da cor por trás.

### 6.5 Contraste — verificado, não assumido

Todos os pares texto/fundo usados por padrão foram checados contra WCAG 2.1 AA (mínimo 4.5:1
para texto normal, 3:1 para texto grande/ícone):

- `--color-text-primary` (#F5F5F7) sobre `--color-bg` (#0B0B0D): ~17.9:1 — excelente.
- `--color-text-secondary` (#A1A1AA) sobre `--color-bg`: ~7.9:1 — passa AA com folga.
- `--color-text-tertiary` (#6E6E76) sobre `--color-bg`: ~4.6:1 — passa AA (texto normal),
  usado só para labels/placeholder, nunca para conteúdo que precise ser lido com certeza.
- `--color-positive`/`--color-negative`/`--color-warning` sobre `--color-bg`: todos acima de
  6:1 — a escolha das tonalidades (400 da escala Tailwind, não 500/600 mais escuras) foi
  deliberada para funcionar bem sobre fundo escuro.
- `--color-text-on-accent` (#FFFFFF) sobre `--color-accent` (#6D5EF5): ~4.6:1 — passa AA;
  texto em botão primário nunca usa peso `light`, sempre `medium`+ (reforça legibilidade no
  limite do contraste).
- **`corDeContraste` (`lib/color.ts`) corrigido na revisão de UX de Cartões** — a fórmula
  antiga decidia preto/branco por um limiar fixo de luminância SEM correção de gama (aproximação
  grosseira da fórmula real do WCAG). Auditoria encontrou que 11 das 43 cores de
  `PALETA_SUGESTAO` recebiam a recomendação de PIOR contraste (ex. `#fb7185`: a fórmula antiga
  recomendava branco, 2.69:1, reprovando AA; preto dá 7.31:1). Corrigido para calcular a razão
  de contraste WCAG real contra preto e branco e escolher a maior — mesma assinatura, benefício
  automático para todo consumidor (`InstitutionBadge`, `BandeiraBadge`, `CategoryBadge`, preview
  do `ColorPicker`).
- `--color-text-on-positive/negative/warning/info` sobre a cor semântica cheia correspondente:
  preto vence nas quatro cores do tema escuro (todas ≥ 7:1); no tema claro é MISTO — `positive`/
  `info` (tons mais claros mesmo no tier "600") preferem preto, `negative`/`warning` (mais
  escuros/saturados) preferem branco — por isso cada token é um valor fixo por tema, calculado
  uma vez, nunca um cálculo em runtime assumindo "sempre preto" ou "sempre branco".

### 6.6 Cores de dado (gráficos) — fora das semânticas financeiras

Para séries de gráfico que não são positivo/negativo/pendente (ex. distribuição de gastos
por categoria), uma paleta categórica de 6 cores, todas testadas para não colidir
visualmente com as semânticas da seção 6.4 (nenhuma é um tom de verde/vermelho/âmbar que
possa ser mal-lido como "financeiro"):

`#6D5EF5` (accent) · `#38BDF8` (azul-céu) · `#C084FC` (violeta claro) · `#F472B6` (rosa) ·
`#FB923C` (laranja) · `#94A3B8` (slate, para "outros/sem categoria")

## 7. Tipografia

**Família: Geist Sans (UI) + Geist Mono (números e dados tabulares).** Geist é a fonte da
própria Vercel — referência explícita do pedido — open source, com excelente suporte a
`tabular-nums` e um caráter geométrico que combina com Linear/Raycast sem imitar a fonte
exata de nenhum dos dois. Distribuída via `@fontsource-variable/geist-sans` e
`@fontsource-variable/geist-mono` (self-hosted, sem chamada a fontes externas em runtime —
melhor performance e privacidade que um `<link>` para Google Fonts).

**Toda cifra monetária, número de tabela, data e "kbd" usa Geist Mono com
`font-variant-numeric: tabular-nums`** — é o que garante alinhamento perfeito em colunas de
valores (ver princípio 1 da seção 1).

### 7.1 Escala tipográfica

Base de UI em **14px** (não 16px) — decisão deliberada: este é um instrumento de trabalho de
uso diário, não uma página de marketing; a densidade de informação de Linear/Raycast (13-14px
de base) é mais apropriada que a tipografia grande de um app de consumo.

| Token | Tamanho | Peso | Line-height | Uso |
|---|---|---|---|---|
| `--text-display` | 36px | 600 (semibold) | 1.1 | número hero de um card de dashboard (ex. saldo total) |
| `--text-h1` | 24px | 600 | 1.2 | título de página |
| `--text-h2` | 18px | 600 | 1.3 | título de seção/card |
| `--text-h3` | 15px | 600 | 1.4 | subtítulo, cabeçalho de grupo em formulário |
| `--text-body` | 14px | 400 | 1.5 | texto padrão da UI |
| `--text-body-medium` | 14px | 500 | 1.5 | texto padrão com ênfase (label de valor, item ativo) |
| `--text-sm` | 13px | 400 | 1.4 | texto secundário, célula de tabela |
| `--text-caption` | 12px | 400 | 1.3 | timestamp, contador, legenda de gráfico |
| `--text-micro` | 11px | 500 | 1.2 | badge, tag, `Kbd` |

Todos os pesos vêm da variable font (não é preciso carregar múltiplos arquivos por peso).
Letter-spacing: `-0.01em` em `--text-h1`/`--text-display` (aperta ligeiramente títulos
grandes, padrão em type systems modernos), `0` no resto.

## 8. Grid e espaçamento

**Unidade-base: 4px** (idêntica à escala numérica padrão do Tailwind — nenhuma configuração
nova necessária, só nomeação semântica para uso consistente em código):

| Token | Valor | Tailwind equiv. |
|---|---|---|
| `--space-1` | 4px | `1` |
| `--space-2` | 8px | `2` |
| `--space-3` | 12px | `3` |
| `--space-4` | 16px | `4` |
| `--space-5` | 20px | `5` |
| `--space-6` | 24px | `6` |
| `--space-8` | 32px | `8` |
| `--space-10` | 40px | `10` |
| `--space-12` | 48px | `12` |
| `--space-16` | 64px | `16` |

**Grid de página:** container com `max-width: 1440px`, padding lateral responsivo
(`--space-6` em mobile, `--space-10` em desktop). Dashboard usa um **bento grid** de 12
colunas (`grid-template-columns: repeat(12, 1fr)`, `gap: var(--space-4)`) — cards de
tamanhos variados (ex. um card de saldo consolidado ocupando 4 colunas, um gráfico de fluxo
de caixa ocupando 8) em vez de um grid uniforme, seguindo o padrão bento citado na seção 4.
Formulários e tabelas usam layout de coluna única/largura total dentro do container — nunca
o bento grid (seção 22/23: densidade de dado financeiro pede previsibilidade, não
composição visual).

**Atualização (Ajustes de UX/UI, seção 0):** a tabela acima é a escala "Padrão" histórica.
Em uso real (Tailwind `p-*`/`gap-*`/`h-*`/`w-*` etc.), todo valor é multiplicado por
`UI_SCALE = 1.2` em `tailwind.config.js` (`--space-4` → efetivamente `19.2px`/`1.2rem`, e
assim por diante) — a tabela não foi reescrita porque os nomes/proporções relativas dos
tokens continuam os mesmos, só a escala de saída mudou. Ver seção 0 para o racional
completo.

## 9. Radius

| Token | Valor "Padrão" | Valor efetivo (`--ui-scale: 1.2`) | Uso |
|---|---|---|---|
| `--radius-xs` | 4px | 5px | badge, chip pequeno |
| `--radius-sm` | 6px | 7px | botão, input, checkbox |
| `--radius-md` | 8px | 10px | card pequeno, item de dropdown |
| `--radius-lg` | 12px | 14px | card padrão, painel |
| `--radius-xl` | 16px | 20px | modal, popover grande |
| `--radius-full` | 9999px | 9999px | avatar, switch, pill de status |

Cantos precisos (raio pequeno) em controles reforça a leitura "ferramenta profissional"
(seção 2) — nada de botões com raio grande estilo app de consumo. Valores efetivos
aplicados via `--ui-scale` em `index.css` (Ajustes de UX/UI, seção 0) — os tokens
(`--radius-*`) continuam os mesmos nomes/hierarquia, só o valor em px cresceu.

## 10. Motion design

**Especificação completa em `docs/motion-principles.md`** — fonte canônica de toda duração,
curva, spring, taxonomia de estados/transições, regras de coreografia, quando animação não
deve acontecer, e acessibilidade de motion. Este documento não duplica esse conteúdo; o
resumo abaixo é só para orientação rápida durante leitura deste documento.

### 10.1 Resumo

- Cinco durações (`100/150/200/300/450ms`) e três curvas custom (`--ease-out`/`--ease-in`/
  `--ease-in-out`), mais três presets de spring do `motion` (`snappy`/`smooth`/`gentle`) —
  reutilizados em toda a interface, nunca timing ad-hoc por componente.
- `prefers-reduced-motion` respeitado globalmente via `MotionConfig reducedMotion="user"`
  (motion) + `@media` em CSS custom; nenhuma informação é comunicada só por animação.
- CSS puro cobre microinterações simples (hover, foco, toggle); `motion` entra especificamente
  em layout animations, coreografia de modal/toast, stagger de lista e no número que conta.
- Regra central da mudança de direção estética (seção 0): sofisticação de motion vem de
  timing/coreografia precisos, não de quantidade de efeito — ver `docs/motion-principles.md`
  seção 1 para o racional completo.

## 11. Elevação e sombra

Dark UI não comunica elevação bem só com `box-shadow` (sombra escura sobre fundo escuro é
quase invisível) — a combinação usada aqui é **borda hairline + leve aumento de luminosidade
da superfície + sombra suave e grande**, nessa ordem de importância:

| Token | `box-shadow` | Uso |
|---|---|---|
| `--shadow-xs` | `0 1px 2px rgba(0,0,0,0.24)` | item de lista em hover |
| `--shadow-sm` | `0 2px 8px rgba(0,0,0,0.28)` | card em hover, dropdown pequeno |
| `--shadow-md` | `0 4px 16px rgba(0,0,0,0.35), 0 1px 2px rgba(0,0,0,0.2)` | popover, menu de contexto |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,0.45), 0 2px 4px rgba(0,0,0,0.25)` | modal, painel lateral |
| `--shadow-xl` | `0 16px 48px rgba(0,0,0,0.55)` | modal grande, command palette |

Cada nível de sombra é sempre combinado com a superfície correspondente (`--color-surface-N`,
seção 6.1) e `--color-border-default` — nunca um card "flutua" só por sombra sem também subir
um nível de superfície.

## 12. Blur e glassmorphism — regra de aplicação restrita

Glass é uma ferramenta de **overlay/chrome**, nunca de conteúdo:

**Onde USAR** (`backdrop-filter: blur(--blur-md)` = 8px, fundo com opacidade ~0.7-0.8 da
superfície): backdrop de modal/dialog, header/sidebar quando o conteúdo rola por baixo
(efeito "sticky com profundidade"), dropdown/popover sobre conteúdo denso, command palette.

**Onde NUNCA usar**: dentro de uma tabela ou lista de transações, atrás de qualquer texto
numérico financeiro, em cards do dashboard (esses usam `--color-surface-2` sólida — um
número de saldo não pode competir com o conteúdo desfocado atrás dele). Esta é a diferença
central entre "Awwwards aplicado com critério" e o erro comum de usar glass decorativamente
em UI densa de dado — o princípio 1 da seção 1 vence aqui explicitamente.

| Token | Valor |
|---|---|
| `--blur-sm` | 4px (header sticky) |
| `--blur-md` | 8px (dropdown, popover) |
| `--blur-lg` | 16px (backdrop de modal) |
| `--blur-xl` | 24px (command palette, reservado para o elemento mais "flutuante" da UI) |

## 13. Comportamento dos componentes — regras gerais

Antes de listar componente por componente, as regras que valem para todos:

- **Todo elemento interativo tem os 4 estados definidos**: default, hover, focus-visible,
  disabled/loading — nenhum componente base é aceito no Design System sem os quatro
  especificados.
- **`focus-visible`, não `focus`** — anel de foco (`--color-accent-ring`, 2px, offset 2px)
  só aparece em navegação por teclado, nunca em clique de mouse (usa `:focus-visible`
  nativo do CSS, sem JS extra).
- **Todo componente com estado de carregamento assíncrono usa o mesmo vocabulário**: um
  `Spinner` para ações rápidas/pequenas, um `Skeleton` para carregamento de conteúdo
  (nunca os dois ao mesmo tempo para a mesma informação).
- **Toda ação destrutiva passa por confirmação** (`DeleteDialog`, seção 14) — nunca um
  `DELETE` acontece no primeiro clique.

## 14. Componentes base

Especificação visual/comportamental. Contrato de props já definido em
`docs/analise-arquitetural-frontend.md` continua valendo (ex. `Button`/`Input` já existem
desde a F1) — o que muda aqui é o styling e os estados, não a API do componente.

- **Button** — variantes `primary` (fundo `--color-accent`, texto branco),
  `secondary` (fundo `--color-surface-2`, borda `--color-border-default`), `ghost` (sem
  fundo, só texto — usado em toolbars/tabelas), `danger` (fundo `--color-negative`).
  Tamanhos `sm`(28px altura)/`md`(36px)/`lg`(44px). Estado de loading: substitui o label por
  `Spinner` do mesmo tamanho do texto + mantém a largura do botão (evita "pulo" de layout) —
  formaliza o `LoadingButton` já previsto na análise do frontend. Press: `scale(0.98)` com
  `--duration-instant`/`snappy`.
- **Input / Textarea** — fundo `--color-surface-2`, borda `--color-border-default`; em foco,
  borda `--color-accent` + anel `--color-accent-ring`. Erro: borda `--color-negative` +
  ícone de alerta à direita (`lucide-react` `AlertCircle`).
- **Select / Combobox** — mesmo visual do Input, abre um painel `--color-surface-3` com
  `--shadow-md`; item ativo usa `--color-accent-subtle` de fundo. Base para
  `CategorySelect`/`AccountSelect`/`CardSelect`/`TagSelect` (seção 15).
- **Checkbox / Radio** — 16px, borda `--color-border-strong`, marcado usa
  `--color-accent` sólido com check em `motion` (`snappy`, desenha o check em ~150ms).
- **Switch** — trilho `--color-surface-3`/`--color-accent` quando ligado, thumb desliza com
  spring `snappy`.
- **Badge/Tag** — `--radius-full`, `--text-micro`, fundo `-subtle` + texto sólido da cor
  correspondente (positive/negative/warning/neutral) — o componente visual por trás de todo
  `StatusFatura`/`StatusTransacao`/`StatusContratoCredito` na UI.
- **Avatar** — círculo (`--radius-full`), iniciais do nome quando não há foto (não há upload
  de foto no backend hoje — sempre iniciais).
- **Tooltip** — `--color-surface-4`, `--text-caption`, aparece com delay de 400ms (evita
  "piscar" ao passar o mouse rápido), `--duration-base`/`--ease-out`.
- **Kbd** — pequeno chip `--color-surface-3` com borda inferior mais forte (efeito de tecla
  física), `--text-micro` em Geist Mono. Usado para mostrar atalhos (`⌘K`, `Esc`) — reforça
  o princípio "teclado em primeiro lugar" (seção 3).
- **Divider** — 1px `--color-border-subtle`.
- **Progress bar** — trilho `--color-surface-3`, preenchimento `--color-accent`; usada tanto
  em formulário de progresso (ex. barra de progresso de Meta) quanto no indicador de
  navegação entre páginas no topo (padrão Vercel/Linear — barra fina de 2px que atravessa a
  tela durante uma transição de rota). **Atualização (Ajustes de UX/UI):** ganhou uma prop
  `tone` (`accent`/`warning`/`negative`) — usada pelo "progresso do limite" de Cartão, que
  reage à proximidade do limite (≥80% = `warning`, ≥100% = `negative`, estourado). Default
  continua `accent`, nenhum outro consumidor precisou mudar.

## 15. Componentes compostos

Já nomeados em `docs/analise-arquitetural-frontend.md` (seção 12) — aqui, o comportamento
visual de cada um:

- **FormField** — label (`--text-sm`, `--color-text-secondary`) + slot de input +
  `ValidationMessage`. Espaçamento vertical `--space-1` entre label e input, `--space-1`
  entre input e mensagem de erro.
- **ValidationMessage** — `--text-sm`, `--color-negative`, ícone `AlertCircle` de 14px,
  entra com fade+slide-down de 4px (`--duration-fast`).
- **MoneyInput** — Input com prefixo fixo "R$" (`--color-text-tertiary`), valor digitado em
  Geist Mono, alinhado à direita quando o campo não está focado (leitura mais fácil),
  alinhado à esquerda em foco (edição mais natural).
- **CurrencyInput** — o primitivo de máscara por trás do `MoneyInput` (ver nota de
  interpretação em `docs/analise-arquitetural-frontend.md`, seção 14).
- **DateInput** — Input com ícone de calendário (`lucide-react` `Calendar`) à direita,
  abre um popover de calendário custom (não o `<input type=date>` nativo do navegador, cujo
  visual não é controlável e destoaria do resto do sistema) com `--shadow-md` e
  `--radius-lg`.
- **LoadingButton** — ver Button (seção 14), já cobre o comportamento.
- **FormDialog** — modal centralizado, `--color-surface-4`, `--radius-xl`, `--shadow-xl`,
  backdrop com `--blur-lg` sobre `rgba(11,11,13,0.6)`. Entrada: backdrop fade
  (`--duration-moderate`) + dialog `scale(0.96→1) + fade`, spring `smooth`. Fecha com `Esc`,
  clique fora, ou botão de fechar — sempre confirma se há alteração não salva antes de
  fechar (evita perda de dado digitado por engano).
- **DeleteDialog** — variante menor do FormDialog (max-width 400px), ícone de alerta
  (`--color-negative`) + texto de confirmação específico da entidade (nunca um genérico "tem
  certeza?") + botão `danger` como ação primária, `secondary`/"Cancelar" como ação padrão
  (foco inicial no Cancelar, não no destrutivo — previne exclusão acidental por `Enter`).
- **CategorySelect / AccountSelect / CardSelect** — Combobox (seção 14) com um ícone/cor
  por item quando aplicável (`CardSelect` mostra `InstitutionBadge`+`BandeiraBadge` do
  cartão), busca-enquanto-digita client-side (lista já vem inteira da query, sem debounce de
  rede necessário dado o volume de um usuário único). `AccountSelect` nasceu na Etapa F9
  (Cartão), primeiro select de domínio fora de Categoria; `CardSelect` nasceu na Etapa F11
  (Transação), espelhando `AccountSelect` quase literalmente
  (`docs/analise-arquitetural-transacao-frontend.md`, seção 4). Desde a Etapa F10,
  `Select`/`SearchSelect` (seção 14) têm um slot visual genérico (`render`) no gatilho e nos
  itens da lista — `CategorySelect` usa para mostrar ícone + cor de cada categoria (mesmo
  visual de `CategoryBadge`). Na Etapa F11, `CategorySelect` ganhou a prop opcional
  `tipoTransacao` — quando definida, restringe as opções a categorias compatíveis
  (`categoria.tipo === tipoTransacao || categoria.tipo === "AMBOS"`), usada por
  `TransacaoFormDialog` para nunca oferecer uma categoria de Despesa numa transação de
  Receita (filtro de UX; a validação real continua no backend).
- **TagMultiSelect** (`components/domain/tag/`, Etapa F11) — camada de domínio sobre o
  primitivo genérico `MultiSelectField` (mecânica de popover diferente do combobox de busca
  de `SearchSelect`: `Checkbox` por opção, chips truncados no gatilho). Cada chip selecionado
  é um `TagBadge` de verdade (cor real da tag) em vez do `Badge tone="accent"` genérico que
  `MultiSelectField` usa por padrão — `MultiSelectField` ganhou uma prop `renderChip` para
  isso (personaliza o chip sem duplicar a mecânica do popover; omitida, mantém o
  comportamento padrão de sempre).
- **BandeiraBadge** (Ajustes de UX/UI + Etapa F9) — mesmo papel de `InstitutionBadge`
  (monograma sobre a cor de marca real, `corDeContraste` decide o texto), mas para o enum
  fechado `Bandeira` (`lib/bandeiras.ts`) em vez de texto livre — sem fallback "não
  informado", `Bandeira` é sempre obrigatório em `CartaoRead`.
- **CartaoVisual** (Ajustes de UX/UI + Etapa F9; simplificado na revisão de UX de Cartões) —
  componente de apresentação puro (recebe primitivos, nunca `CartaoRead` diretamente): cartão
  físico premium (proporção real `1.586:1`, gradiente de `lib/cardThemes.ts`,
  `InstitutionBadge` + `BandeiraBadge`, nome + últimos 4 dígitos, `ProgressBar tone` de
  limite, tilt 3D + glow no mouse). O `layout="compact"` (linha horizontal usada na antiga
  coluna "Cartão" do `DataTable`) foi removido junto com a migração de `/cartoes` para grid
  de cards (`docs/analise-arquitetural-revisao-ux-cartoes.md`, seções 2 e 9) — sem
  `DataTable`, não sobra consumidor do layout compacto. `tone` da barra corrigido de `accent`
  para `positive` no estado saudável (achado de auditoria da mesma revisão: `accent` é
  reservado para interação, seção 6.3, nunca para dado financeiro).
- **CartaoResumoCard** (`components/domain/cartao/`, revisão de UX de Cartões) — card
  clicável do grid de `/cartoes`, "mini dashboard" do cartão: `CartaoVisual` (identidade +
  utilização) + "Disponível" em destaque (`AnimatedNumber`) + percentual + próxima fatura
  resumida + `CartaoActionBar`. O card inteiro navega para a página de detalhes
  (`role="link"` + `tabIndex` + `onClick`/`onKeyDown`, nunca um `<a>` envolvendo os botões da
  Action Bar — elemento interativo aninhado seria HTML inválido); hover reaproveita a
  elevação padrão de `Card` (`y: -2`, sombra, borda).
- **CartaoActionBar** (`components/domain/cartao/`, revisão de UX de Cartões) — ações
  sempre com ícone + texto (Editar/Faturas/Desativar-Reativar/Excluir), nunca escondidas
  atrás de um menu; compartilhada entre `CartaoResumoCard` e a página de detalhes (sem
  "Faturas" nesta última, que já mostra a lista inline). Todo `onClick` faz
  `stopPropagation` — necessária quando a barra vive dentro de um card inteiro clicável.
- **ProximaFaturaCard** (`components/domain/fatura/`, revisão de UX de Cartões) — card de
  destaque na página de detalhes do Cartão com a fatura mais relevante (`ATRASADA` >
  `ABERTA` > `FECHADA`/`PARCIALMENTE_PAGA` > `PAGA`, função pura `selecionarProximaFatura`
  em `utils/fatura.ts`), com atalho para abrir o `FaturaDrawer` já na ação certa (fechar
  ciclo ou registrar pagamento).
- **Drawer** (Etapa F10) — overlay Tier 2 ancorado à direita (`docs/analise-arquitetural-overlays.md`,
  seção 4.5), `max-w-[30rem]`, mesmo padrão de focus-trap do `FormDialog`
  (`FOCUSABLE_SELECTOR`), `role="dialog"`, trava de scroll do body. Entrada: backdrop fade
  (`--duration-moderate`, igual ao `FormDialog`) + painel `slide-in` de `x: 100%` com spring
  `smooth`; saída mais rápida (`--duration-moderate` × 0.7, `ease-in`), sem spring — abrir
  convida, fechar não deveria demorar. Usado hoje só pelo `FaturaDrawer` (uma fatura por
  vez, nunca a lista inteira).
- **RichPicker\<T\>** (Etapa F10) — overlay Tier 1 genérico (`docs/analise-arquitetural-overlays.md`,
  seção 4.3) para escolha visual entre poucas dezenas de opções (ícone, cor, instituição,
  bandeira). Dois `layout`s: `"grid"` (ícones/cores, navegação por teclado em grade) e
  `"list"` (poucas opções com rótulo textual, ex. bandeira de cartão). Busca aparece
  automaticamente acima de `searchThreshold` itens; agrupamento visual opcional
  (`group` por item). Em viewport mobile (`useIsMobileViewport`), sempre cai para um modal
  centralizado em vez de popover ancorado — popover flutuante não é confiável em telas
  pequenas. Base de `IconPicker`/`ColorPicker`/`BankPicker`/`CardBrandPicker` (abaixo).
- **IconPicker / ColorPicker** (Etapa F10) — substituem `IconField`/`ColorField` (F7),
  agora compostos sobre `RichPicker` em vez de implementação própria de popover/busca/
  navegação. `IconPicker` usa `layout="grid"`, sem preview separado (o próprio gatilho já
  mostra o ícone selecionado). `ColorPicker` usa `layout="grid"` com `searchThreshold=0`
  (busca sempre disponível, filtra por `grupo`) e **preserva o campo de texto livre (hex)**
  ao lado do gatilho do picker — nunca vira uma lista fechada de cores.
- **BankPicker / CardBrandPicker** (Etapa F10) — pickers de domínio compostos sobre
  `RichPicker`. `BankPicker` (`instituicao` de `Conta`/`Cartão`) inclui uma entrada especial
  "Outra instituição" que revela um `<input>` de texto livre — preserva a mesma liberdade do
  campo original no backend, nunca se torna um enum fechado. `CardBrandPicker` (`bandeira`
  de `Cartão`) usa `layout="list"` sem busca (enum fechado, 7 itens).
- **CartaoDetalhePage** (Etapa F10, `/cartoes/:id`) — primeira página de DETALHES do
  projeto (todas as entidades anteriores usam só `FormDialog` para visualizar/editar).
  Layout em duas colunas: `CartaoVisual` (`layout="full"`) + ações (Editar/
  Desativar-Reativar/Excluir) + `MetricCard`s de limite à esquerda; seção "Faturas" com
  mini-formulário inline de criação (`<input type="month">`) e lista completa clicável à
  direita, cada item abrindo um `FaturaDrawer` com o detalhe/ações daquela fatura
  específica. Padrão de referência para a próxima entidade que precisar de página própria
  em vez de só um `FormDialog`.
- **`StatusDot`** (revisão de UX de Cartões, "microindicadores") — ponto colorido de 6px,
  tone do sistema semântico (seção 6.4). Sempre ao lado de um rótulo textual (nunca a única
  fonte de informação); `aria-hidden` implícito quando não recebe `aria-label` próprio.
- **`StatusChip`** (revisão de UX de Cartões, "cores adaptativas") — pill de fundo SÓLIDO
  (ver seção 6.4/6.5) para informação desenhada sobre um fundo que o componente não controla.
- **`AtivoBadge`** (revisão de UX de Cartões) — badge de ativo/inativo único para o projeto
  inteiro (`StatusDot` + `Badge`), substitui o `<Badge tone={x.ativo ? "positive" :
  "neutral"}>` que existia duplicado em `Conta`/`Categoria`/`Tag`/`Cartão`. Rótulos
  (`labelAtivo`/`labelInativo`) parametrizáveis para concordância de gênero ("Ativa"/"Ativo").

## 16. Padrões para dashboards

- **Bento grid de 12 colunas** (seção 8). Cards de métrica (`StatCard`) nas posições de
  maior destaque (topo, 3-4 colunas cada): saldo consolidado, entradas do mês, saídas do
  mês, patrimônio líquido — todos vindos direto de `/central-financeira/resumo` e
  `/saldo-consolidado`.
- **`StatCard`**: label (`--text-sm`, secundário) + valor (`--text-display`, Geist Mono,
  anima com count-up spring `gentle` de 0 até o valor quando os dados chegam — nunca ao
  trocar de aba/revisitar com dado em cache, só na primeira renderização real do valor) +
  variação opcional (badge positive/negative com seta, ex. "+12% vs. mês passado" — cálculo
  já resolvido no backend, o card só formata).
- **Gráfico principal** (fluxo de caixa) ocupa a linha larga (8-12 colunas) abaixo dos
  StatCards. Gráficos secundários (distribuição por categoria, progresso de metas) dividem o
  espaço restante. Biblioteca de gráfico: decisão adiada para a Etapa F5 (fora do escopo
  deste documento), mas a linguagem visual (cores da seção 6.6, sem grid pesado, tooltip
  estilo `--color-surface-4`+`--shadow-md`) já está definida aqui para qualquer lib que for
  escolhida.
- **Agenda financeira** (próximos vencimentos, de `/central-financeira/agenda`) como lista
  compacta lateral ou card de largura total abaixo do fold — cada item com ícone de origem
  (`TipoEntidadeReferenciavel` → ícone `lucide-react` mapeado 1:1) + data + valor.

## 17. Padrões para formulários

- **Coluna única, sempre** — decisão deliberada mesmo tendo espaço para duas colunas: um
  formulário financeiro (ex. criar Financiamento com 8+ campos) tem custo de erro alto o
  bastante para que previsibilidade de leitura vença densidade. Exceção explícita: campos
  logicamente pareados e curtos (ex. `dia_fechamento`/`dia_vencimento` de Cartão) podem
  dividir uma linha em duas colunas iguais.
- **Todo formulário de criar/editar abre em `FormDialog`** (modal), nunca em página cheia —
  consistente com o volume de campos das entidades (nenhuma tem mais que ~10) e mantém o
  usuário no contexto da lista/tabela que estava vendo.
- **Validação: no blur, não a cada tecla** — `react-hook-form` configurado com
  `mode: "onBlur"` (não `onChange`), para não mostrar erro "campo obrigatório" enquanto o
  usuário ainda está digitando a primeira letra.
- **Campos obrigatórios não são marcados com `*`** — em vez disso, campos OPCIONAIS ganham um
  label secundário "(opcional)" em `--color-text-tertiary`. A maioria dos campos deste
  sistema é obrigatória; marcar a minoria opcional é mais limpo visualmente e mais informativo.
- **Botão de submit fica fixo no rodapé do `FormDialog`** (não rola junto com o conteúdo em
  formulários longos), sempre com `LoadingButton`.

## 18. Padrões para tabelas

- **Sem zebra striping** — divisórias de `--color-border-subtle` entre linhas, seguindo
  Linear/Raycast em vez do padrão "linha cinza alternada" de dashboards mais tradicionais/
  bancários (o efeito que este projeto está deliberadamente evitando, ver instrução
  original: "sem o conservadorismo típico de aplicativos bancários").
  Altura de linha ~44px.
- **Toda coluna numérica é alinhada à direita, Geist Mono, tabular-nums.** Toda coluna de
  status usa `Badge` (seção 14), nunca texto puro colorido solto.
  Toda coluna de data usa `--text-sm` + Geist Mono.
- **Ações de linha aparecem só no hover** (ícones `ghost` à direita — editar, excluir,
  ação específica como "pagar parcela") — reduz ruído visual quando a tabela não está sendo
  interagida, sem esconder a funcionalidade (é revelada por proximidade/hover, não por menu
  extra escondido).
- **Cabeçalho sticky** ao rolar tabelas longas; ordenação por coluna (clique no cabeçalho)
  com ícone de seta que anima a rotação (`--duration-fast`).
- **Paginação/ordenação/filtro client-side**, decisão já registrada em
  `docs/analise-arquitetural-frontend.md` (seção 13) — este documento só define o visual
  (controles de paginação no rodapé da tabela, filtro como barra acima do cabeçalho).
- **Exceção deliberada: Cartão não usa `DataTable`.** Na revisão de UX de Cartões
  (`docs/analise-arquitetural-revisao-ux-cartoes.md`), `/cartoes` migrou de `DataTable` para
  um grid de `CartaoResumoCard` — um cartão é tratado como objeto de destaque ("mini
  dashboard"), não como registro tabular, e o volume por usuário é baixo o bastante para
  paginação/ordenação não fazerem falta. `Conta`/`Categoria`/`Tag` permanecem `DataTable`
  (volume/natureza mais simples) — a exceção é só de Cartão, não um novo padrão geral.
- **Segunda exceção deliberada: `/transacoes` usa filtragem híbrida.** Transação (Etapa F11)
  é a primeira entidade com volume real — lançamentos acumulam de verdade, ao contrário de
  todo "dado mestre" anterior. `docs/analise-arquitetural-transacao-frontend.md`, seção 2:
  período (`PeriodoSeletor`) e os filtros de tipo/status/categoria viram parâmetros REAIS de
  `GET /transacoes` (o backend filtra de verdade, refetch a cada mudança), e só o resultado
  já filtrado (tipicamente dezenas de linhas por mês) entra no `DataTable`, que continua
  cuidando só de busca textual adicional/ordenação/paginação de exibição — nenhuma mudança em
  `useDataTable`/`DataTable` em si.

## 19. Padrões para gráficos

- Paleta exclusivamente das seções 6.4 (quando o gráfico representa polaridade financeira,
  ex. entradas vs. saídas) ou 6.6 (quando representa categorias sem polaridade, ex. gastos
  por categoria).
- Sem grid de fundo pesado — no máximo linhas guia horizontais muito sutis
  (`--color-border-subtle`), sem grid vertical.
- Eixos com `--text-caption`, `--color-text-tertiary` — nunca competem visualmente com a
  série de dado.
- Tooltip ao hover: `--color-surface-4` + `--shadow-md` + `--radius-md`, valor em Geist Mono.
- Entrada do gráfico ao montar: draw-in animado (`--duration-slow`, `--ease-out`) — uma vez
  só, não repete ao trocar de aba com dado já em cache (mesma regra do `StatCard`, seção 16).

## 20. Estados vazios, skeletons e loading

### 20.1 EmptyState

Nunca um texto solto "nenhum resultado". Estrutura fixa: ícone `lucide-react` (24-32px,
`--color-text-tertiary`) + título curto (`--text-h3`) + descrição de uma linha
(`--text-sm`, secundário) + ação primária quando fizer sentido (ex. "Nenhuma conta ainda" +
botão "Criar conta"). Usado tanto em tabelas vazias quanto em listas de dashboard sem dado.

### 20.2 Skeleton

Sempre no formato exato do conteúdo final (linha de tabela vira retângulos do tamanho de
cada célula, card vira um bloco do tamanho do card) — nunca um placeholder genérico. Cor
`--color-surface-2`, com um shimmer sutil (gradiente animado deslizando, `--duration-slow`
em loop, respeitando `prefers-reduced-motion` → shimmer desligado, só a cor estática).

### 20.3 Loading — três formas, cada uma com seu caso de uso

| Padrão | Quando usar |
|---|---|
| `Spinner` inline | ação pequena e rápida (botão, ícone de refresh) |
| `Skeleton` | primeira carga de uma seção/página inteira (linhas de tabela, cards do dashboard) |
| Barra de progresso no topo (2px, `--color-accent`) | transição de rota (`React Router` navigation), estilo Vercel/Linear |

Nunca dois padrões ao mesmo tempo para a mesma informação (ex. não usar `Spinner` central
por cima de uma tabela que já está em `Skeleton`).

## 21. Toasts

Já implementado (minimamente) na Etapa F1 via `ToastContext` — esta seção formaliza o
visual, sem mudar o contrato do Context. Posição inalterada (canto inferior direito).
Superfície `--color-surface-4` + `--shadow-lg`, `--radius-lg`, ícone por tipo
(`success`→check verde, `error`→alerta vermelho, `info`→ícone neutro `--color-accent`).
Entra com slide-up + fade (`spring: smooth`), pausa o timer de auto-dismiss (5s, herdado da
F1) quando o mouse está sobre o toast, empilha com `--space-2` de gap quando há mais de um.

## 22. Modais

Cobertos como parte de `FormDialog`/`DeleteDialog` (seção 15). Regras gerais adicionais:
foco é preso dentro do modal (focus trap) enquanto aberto; foco retorna ao elemento que abriu
o modal ao fechar; scroll do `body` é bloqueado enquanto um modal está aberto; só um modal
por vez (nunca modal sobre modal — um `FormDialog` que precisar de uma confirmação extra usa
`DeleteDialog` substituindo o conteúdo, não empilhando).

## 23. Acessibilidade

- Contraste verificado na seção 6.5 — não é aspiracional, são os valores reais dos tokens.
- `focus-visible` obrigatório em todo componente interativo (seção 13).
- Toda animação respeita `prefers-reduced-motion` (`docs/motion-principles.md`, seção 8).
- Componentes compostos (Select/Combobox, Modal, Toast) implementados com os `role`/`aria-*`
  corretos (`role="dialog"` + `aria-modal` no FormDialog, `role="status"`/`aria-live="polite"`
  no Toast — este último já existe desde a F1, mantido).
- Área de toque mínima de 40px em qualquer alvo clicável em telas < 768px (mesmo que o
  elemento pareça menor visualmente, o hit-target é expandido via padding invisível).
- Nenhuma informação é comunicada só por cor — todo Badge tem texto, todo gráfico tem
  legenda, positive/negative também podem ganhar um ícone de seta opcional em contextos de
  baixa visão (não obrigatório, mas o token `Badge` já reserva o espaço para isso).

## 24. Responsividade

Desktop-first (uso primário é uma pessoa numa mesa, gerenciando finanças com atenção), mas
funcional em mobile para consulta rápida:

| Breakpoint | Largura | Comportamento |
|---|---|---|
| `sm` | ≥640px | base mobile |
| `md` | ≥768px | sidebar deixa de colapsar, mas ainda compacta |
| `lg` | ≥1024px | layout completo, sidebar expandida por padrão |
| `xl` | ≥1280px | bento grid do dashboard em largura total (seção 8) |

Abaixo de `md`: sidebar vira menu inferior fixo (ícones apenas, sem label) ou drawer
acionado por ícone de menu no header (a decidir na implementação F2, não estrutural o
bastante para travar este documento); bento grid do dashboard colapsa para coluna única na
mesma ordem de prioridade visual (StatCards primeiro, gráfico principal depois); tabelas
densas viram uma lista de cards (cada linha vira um card compacto) abaixo de `md` — uma
tabela de 6+ colunas não cabe legivelmente numa tela de telefone, e forçar scroll horizontal
é pior experiência que reformatar para card.

## 25. Próximos passos

Este documento não implementa nada. Junto com `docs/motion-principles.md` (fonte canônica de
motion, seção 10), forma o par de documentos que a Etapa F2 lê antes de escrever qualquer
código — mesma convenção que a F1 seguiu com `docs/analise-arquitetural-frontend.md`. Ordem
sugerida para a Etapa F2, uma vez ambos aprovados:

1. `tailwind.config.js` + variáveis CSS (`:root`) com todos os tokens das seções 6-12 deste
   documento + seção 4 de `docs/motion-principles.md`.
2. Instalar `motion`, `lucide-react`, `@fontsource-variable/geist-sans`,
   `@fontsource-variable/geist-mono`.
3. `MotionConfig reducedMotion="user"` no root da aplicação (`docs/motion-principles.md`,
   seção 12) antes de qualquer componente com motion ser escrito.
4. Restilizar os componentes já existentes da F1 (`Button`, `Input`, `Spinner`,
   `ErrorMessage`, `AppLayout`, `AuthLayout`, `LoginPage`, `RegistrarPage`) para os novos
   tokens — contrato de props inalterado, só a superfície visual muda.
5. Construir o restante dos componentes base (seção 14) e as primeiras peças de
   `components/layout/` (Sidebar, Header) que a `AppLayout` ainda não tem.
6. Só depois disso a Etapa F3 (sistema de formulários) começa a usar essas peças.

Aguardando sua validação de `docs/motion-principles.md` (documento novo) antes de qualquer
código — os pontos da seção 0 deste documento (dark-only sem toggle, motion/lucide/fonte, e
agora o ajuste de direção estética) já foram confirmados/decididos.

## 26. Refinamento de Pickers e Performance (pós-F11)

Etapa exclusivamente de UX/performance — nenhuma regra de negócio ou API alterada
(`docs/analise-arquitetural-refinamento-pickers-performance.md`).

- **`useFloatingPanel`** (`hooks/useFloatingPanel.ts`) — hook central que resolve o problema
  de raiz dos Pickers ("scroll dentro de scroll", painel cortado pelo `overflow-y-auto` do
  `FormDialog`): calcula `{top, left, width}` via `getBoundingClientRect()` do elemento-âncora
  e posiciona o painel com `position: fixed`, portalado direto em `document.body`
  (`createPortal`). Portal é necessário (não bastaria trocar `absolute`→`fixed` no lugar)
  porque o painel do `FormDialog` anima `scale` (Framer Motion) — um `transform` em qualquer
  ancestral cria um novo *containing block* para descendentes `fixed`, invalidando as
  coordenadas vindas de `getBoundingClientRect()` a menos que o painel esteja fora dessa
  subárvore. Reaproveitado por `RichPicker`, `SearchSelect`, `MultiSelectField`, `Select` e
  `ColumnVisibility` — todo overlay Tier 1 ancorado do projeto agora usa o mesmo mecanismo,
  em vez de cada componente reimplementar seu próprio posicionamento.
- **`useDismissableOverlay`** ganhou um parâmetro opcional `extraRefs` — necessário porque um
  painel portalado fica fora da `<div>` do gatilho; sem isso, todo clique dentro do próprio
  painel seria tratado como "clique fora" e o fecharia imediatamente.
- **`RichPicker`** — grade de 6→10 colunas, células de 40px→44px, painel com largura fixa
  (independente da largura do gatilho: 560px em grade, 400px em lista) e altura
  `max-h-[min(70vh,480px)]` (antes uma altura fixa menor). Reflete o tamanho real dos
  registros do projeto (77 ícones, 44 cores, ~20 instituições, 7 bandeiras) — a grade antiga
  de 6 colunas forçava rolagem longa para conjuntos que cabem confortavelmente em poucas
  linhas de 10.
- **Destaque de busca** (`utils/highlight.tsx`, `destacarTrecho`) — aplicado em `RichPicker`
  (layout lista) e `SearchSelect`: o trecho que casa com a busca aparece em `<mark>`, não só
  filtrado.
- **Code-splitting por rota** (`routes/AppRoutes.tsx`) — cada página protegida
  (Dashboard/Contas/Cartões/Detalhe do Cartão/Categorias/Tags/Transações/rotas `/dev/*`) agora
  é `React.lazy()` com `<Suspense>` individual por rota (nunca envolvendo o `AppLayout`
  inteiro — Sidebar/Header não desmontam ao trocar de página). `ReactQueryDevtools` também
  passou a import dinâmico condicionado a `import.meta.env.DEV`, eliminado do bundle de
  produção por *dead-code elimination* do Vite/esbuild.
- **Achado real de performance** (auditoria antes de qualquer otimização, não especulativa):
  zero code-splitting existia no projeto inteiro antes deste refinamento; `vite build` já
  acusava um único chunk de 741KB. Após a mudança, o maior chunk isolado por página fica na
  casa de 5-23KB, com um chunk principal (~509KB) concentrando as dependências compartilhadas
  (React, React Query, Framer Motion, React Hook Form, Zod) — redução real de trabalho de
  parse/execução no primeiro carregamento de cada rota, sem tocar em nenhum outro
  comportamento. `React.memo`/`useCallback` fora de Context providers não eram usados em
  lugar nenhum do projeto; nenhum candidato com evidência real de re-render custoso foi
  encontrado, então nenhum memo especulativo foi adicionado (princípio explícito desta etapa:
  "não otimizar por achismo").

## 27. Refinamento de Pagamento de Fatura (pós-F11)

Nenhuma regra de negócio ou API alterada — a integração Fatura↔Transação já existia no
backend (`FaturaService.registrar_pagamento` sempre criou uma `Transacao` real de despesa,
vinculada via `fatura_paga_id`); o trabalho real foi de UX e de uma invalidação de cache que
faltava (`docs/analise-arquitetural-refinamento-fatura-pagamento.md`).

- **Bug real corrigido**: registrar um pagamento de fatura não invalidava `transacoes.*`,
  `contas.detail` nem a maior parte do Dashboard — o saldo da conta de pagamento e o extrato
  de transações só refletiam o pagamento após um F5 manual. `invalidarTransacoes`
  (`hooks/useTransacaoQueries.ts`) passou a ser exportada e é reaproveitada por
  `useRegistrarPagamento` (`hooks/useFaturaQueries.ts`) em vez de duplicar a lista de
  invalidações — um pagamento agora atualiza barra de utilização, limite disponível, status da
  fatura e o extrato de Transações no mesmo instante.
- **Atalhos de pagamento** (`FaturaDrawer`) — "Pagar total" (só quando `valor_pago === 0`) e
  "Pagar restante" preenchem o campo de valor; o payload enviado ao backend é idêntico ao de
  qualquer digitação livre (`FaturaService.registrar_pagamento` aceita qualquer `valor > 0`,
  sem distinção de "tipo" de pagamento na API).
- **Preview client-side não-autoritativo** (`utils/fatura.ts`, `preverStatusPosPagamento`) —
  espelha a mesma prioridade de `FaturaService._derivar_status` (quitada > atrasada > parcial
  > só fechada) para mostrar, enquanto o usuário digita, como o status ficará após o
  pagamento. Nunca persistido; descartado assim que a mutation real resolve.
- **Densidade proposital** (`ProximaFaturaCard`, `FaturaDrawer`) — valor pago e valor restante
  sempre visíveis (não só dentro do formulário de pagamento), com `ProgressBar` de progresso
  de quitação quando a fatura não está mais `ABERTA`. Reflete a diretriz de priorizar a
  experiência de quem usa o sistema todo dia sobre a simplicidade para um usuário iniciante.

## 28. Estabilização e Polimento de Overlays (pós-F11)

Etapa exclusivamente de correção de bugs e consistência — nenhuma funcionalidade nova,
nenhuma regra de negócio ou API alterada.

- **Causa raiz do bug crítico (ColorPicker/IconPicker "tela preta")** — `RichPicker`, em
  viewport móvel (`useIsMobileViewport`, abaixo de 768px), renderizava seu PRÓPRIO backdrop
  (`bg-bg/60 backdrop-blur-lg`, idêntico ao de `FormDialog`) por cima do `FormDialog` já
  aberto que o contém. Dois véus de 60% de opacidade + blur empilhados compõem para ~84% de
  opacidade e cobrem até o conteúdo do `FormDialog` por trás — lido pelo usuário como "a tela
  fica toda preta e trava". Violava a própria regra do projeto
  (`docs/analise-arquitetural-overlays.md`, seção 2: Tier 1 nunca tem backdrop próprio, Tier 2
  nunca empilha — sempre substitui o conteúdo do primeiro). Corrigido removendo o
  escurecimento/blur do wrapper mobile do `RichPicker` — hoje é só um contêiner de
  centralização transparente; a própria tela já está escurecida pelo `FormDialog` que o
  contém (confirmado por auditoria: `RichPicker`/`ColorPicker`/`IconPicker`/`BankPicker`/
  `CardBrandPicker` são usados 100% das vezes de dentro de um `FormDialog`, nunca de forma
  autônoma).
- **Segunda instância do mesmo bug, em qualquer viewport** — `FaturaDrawer` abria um
  `ConfirmAction` (Tier 2, backdrop próprio) para "Fechar ciclo"/"Excluir fatura" enquanto o
  próprio `Drawer` (também Tier 2) já estava aberto — mesmo empilhamento de dois backdrops,
  mas reproduzível em qualquer largura de tela, toda vez que o usuário confirmava uma dessas
  duas ações. Corrigido substituindo o conteúdo do `Drawer` inline (mesma técnica que
  `FormDialog` já usa para "Descartar alterações?"), em vez de abrir um `ConfirmAction`
  separado — `FaturaDrawer` não importa mais `ConfirmAction`.
- **`DateInput` esquecido na migração anterior** — único popover do projeto que ainda usava
  `position: absolute` (cortado pelo `overflow-y-auto` de um `FormDialog` ancestral, mesmo bug
  de clipping que afetava `RichPicker`/`SearchSelect` antes do Refinamento de
  Pickers/Performance) e um `useEffect` próprio de clique-fora/`Esc` duplicando
  `useDismissableOverlay`. Migrado para `useFloatingPanel`, mesmo padrão de todos os outros —
  usado por `DateField` (campo "Data" de Transação, "Data do pagamento" de Fatura).
- **Escala de z-index formal** (`index.css`: `--z-tier2: 50`, `--z-tier1: 60`, `--z-toast: 70`)
  — antes, todo overlay (Tier 1 e Tier 2) usava a mesma classe `z-50` solta, e a ordem correta
  de empilhamento (Tier 1 sempre acima de Tier 2) só funcionava por coincidência da ordem de
  montagem no DOM. Agora é uma garantia estrutural: `Dialog`/`Drawer`/`ConfirmAction`
  (`--z-tier2`) sempre abaixo de `RichPicker`/`SearchSelect`/`Select`/`MultiSelectField`/
  `ColumnVisibility`/`DateInput`/`Tooltip` (`--z-tier1`), e toasts (`--z-toast`) sempre acima
  de tudo — uma confirmação/erro precisa aparecer mesmo com um overlay ainda aberto.
- **Auditoria de consistência** — `ContaFormDialog`/`CartaoFormDialog`/`TagFormDialog`/
  `TransacaoFormDialog` confirmados sem nenhum overlay customizado próprio (100% composição de
  `FormDialog` + campos compartilhados); nenhum deles aninha `ConfirmAction`. `UserMenu`
  (Header) e `MobileNav` usam `z-50`/backdrop próprios mas nunca aparecem de dentro de outro
  overlay já aberto — sem o bug de empilhamento, mantidos como estão.
- **Correção — causa raiz real do bug crítico era outra** (achado por um vídeo do usuário
  reproduzindo o problema em viewport DESKTOP, não só mobile): a correção de backdrop
  duplicado acima era um bug real, mas secundário. A causa raiz de verdade era um **loop
  infinito de render em `useFloatingPanel`** — `RichPicker`/`ColumnVisibility`/`DateInput`
  passam `options.panelWidth` como função inline (nova referência a cada render, nenhum
  memoiza com `useCallback`), e `recompute` tinha `options.panelWidth` nas deps do seu próprio
  `useCallback`. Isso recriava `recompute` a cada render → o `useLayoutEffect` (que depende de
  `recompute`) rodava de novo mesmo com `open` inalterado → chamava `setRect` com um objeto
  novo → outro render → `recompute` mudava de novo → loop infinito, travando o React
  (`Maximum update depth exceeded`). Sem nenhum `ErrorBoundary` no projeto até então, esse erro
  não tratado derrubava a árvore inteira — a tela ficava em branco/preta, dependendo do tema.
  Corrigido guardando `options` numa `ref` sempre atualizada e tornando `recompute` estável
  para sempre (`useCallback` com array de dependências vazio) — lê a `ref` em vez de depender
  de uma função recriada a cada render. Esse bug afetava TODO uso de `RichPicker`
  (`ColorPicker`/`IconPicker`/`BankPicker`/`CardBrandPicker`) e `ColumnVisibility`, em qualquer
  viewport, desde que `useFloatingPanel` foi criado.
- **`ErrorBoundary` novo** (`components/layout/ErrorBoundary.tsx`, envolvendo toda a árvore em
  `App.tsx`) — rede de segurança de topo. Não previne bugs (a causa raiz de cada um continua
  precisando ser corrigida, como sempre), só garante que uma exceção de render não tratada no
  futuro nunca mais derrube a aplicação inteira em silêncio: mostra uma mensagem + botão de
  recarregar, em vez de uma tela em branco sem explicação.

## 29. Auditoria de Identidade Visual — harmonização de paleta (pós-refinamento de Dashboard)

Pedido explícito: a paleta "ficou bagunçada", muitas cores concorrendo, hierarquia pouco clara.
Antes de qualquer alteração, auditoria de todo o código-fonte por cor bypassing o sistema de
tokens (`text-red-500`, `bg-blue-600` etc. do Tailwind puro, fora de `--color-*`) — **zero
ocorrências em todo o projeto**. Ou seja, a disciplina de tokens (seção 6) já era 100% seguida;
o problema não estava nos tokens em si, mas em dois pontos concretos de uso:

- **`CartaoVisual` — causa raiz real da "competição de cores".** O gradiente de marca da
  instituição (`lib/cardThemes.ts`, cor real pública de cada banco) era o fundo INTEIRO do
  cartão em saturação total (ex. roxo Nubank, laranja Inter, vermelho Santander, amarelo BB —
  lado a lado no grid de `/cartoes` ou no `CartoesCard` do Dashboard). Isso contradizia
  diretamente a filosofia "confiança silenciosa" (seção 1) e a regra de cor com significado
  fixo (seção 6.4) — cor de marca não é semântica financeira, mas competia visualmente com
  quem é (`StatusChip`/`ProgressBar` desenhados por cima). Corrigido sem alterar nenhum hex de
  `cardThemes.ts` (continuam sendo o fato público de cada marca): o fundo do cartão agora é
  SEMPRE a base escura padrão (`--color-surface-3`→`--color-surface-4`, mesmo par de qualquer
  superfície elevada do app), com o gradiente de marca aplicado por CIMA como uma tinta
  translúcida (`opacity: 0.55`, `mixBlendMode: soft-light`) — a identidade da marca continua
  reconhecível (ainda dá para ver "isso é roxo/laranja/vermelho"), mas nunca mais em saturação
  total competindo com badges/chips/progress bar. `tema.corTexto` (cor de texto por variante,
  calibrada para o fundo antigo em saturação total) parou de ser usado como cor principal do
  texto — com a base agora sempre escura, `--color-text-primary` sozinho é mais legível E mais
  consistente entre cartões (2 variantes, BB e Neon, tinham `corTexto` escuro que ficaria
  ilegível sobre a nova base escura — bug real que essa mudança também evitou).
- **Badge "Sistema" com tone `accent`** (`categoriaTableColumns.tsx`) — `accent` é reservado
  para interação (seção 6.3), nunca para uma classificação neutra. Achado ainda mais relevante
  depois do seed de categorias padrão (13+ categorias de sistema, ver seção 5 do
  `docs/analise-arquitetural-refinamento-ux-dashboard-cartoes.md`): a tabela de Categorias
  passou a mostrar esse badge em toda linha de categoria padrão, um bloco de roxo repetido sem
  necessidade, competindo com a cor real de cada `CategoryBadge` ao lado. Corrigido para
  `tone="neutral"` (cinza) — mesmo tone já usado por `AtivoBadge` para classificação
  não-interativa/não-financeira.

**Decisão explícita de NÃO alterar os valores dos tokens de cor (seção 6).** A auditoria não
encontrou evidência de que os tokens em si (accent, positive/negative/warning/info, superfícies)
precisassem de re-tonalização — todos já passam WCAG AA (seção 6.5), e a única família "extra"
de cor (marca de instituição, paleta de 44 cores de categoria) é dado real (marca pública,
escolha do usuário), não decoração. O problema real era pontual (dois componentes), não
estrutural — mudar os tokens centrais alteraria a cor de toda a aplicação sem uma causa
correspondente, risco maior que o problema relatado.
