# Motion Principles — Finanças Pessoais

Documento de design puro — **nenhum código é escrito nesta etapa**. Define os princípios de
motion (por que, quando, quanto e como qualquer coisa se move na interface) antes da Etapa
F2 (Design System) começar a implementar. É a **fonte canônica** de duração, curva, spring e
regra de estado para todo o projeto — `docs/design-system.md` (seção 10) referencia este
documento em vez de duplicá-lo, para nunca haver duas fontes de verdade divergentes sobre
timing de animação.

Motivo de existir como documento separado: motion é fácil de especificar mal — "use Framer
Motion com bom gosto" não é uma decisão, é a ausência de uma. Este documento força cada
animação futura a passar por um propósito explícito antes de ser escrita.

## 1. Filosofia

**Movimento com propósito, nunca espetáculo.** A referência a "produtos de alto nível do
Awwwards" que orientou este documento não significa "grande quantidade de animação
impressionante" — significa o oposto: a sofisticação real de motion premiado está na
**precisão** (timing exato, curvas que parecem fisicamente corretas, coreografia onde cada
elemento entra na ordem certa) mais do que na quantidade ou intensidade do efeito. Um site
vitrine do Awwwards é visitado uma vez e precisa impressionar em 10 segundos; este app é
aberto várias vezes por dia pela mesma pessoa e precisa continuar agradável na
centésima abertura, não só na primeira. Essa diferença de contexto de uso é o filtro por trás
de toda decisão deste documento.

**Identidade própria, não a soma de referências.** Nenhuma animação deste sistema deve ser
reconhecível como "isso é exatamente o hover do Linear" ou "isso é a transição de página
da Vercel". As referências (seção 3) são estudadas pelo *princípio* que ensinam — a
combinação de curvas, durações e escolhas de coreografia definidas aqui é específica deste
projeto e não replica a assinatura de nenhum produto existente.

**Toda animação responde a uma pergunta do usuário.** Antes de qualquer motion ser
implementado, ele precisa se encaixar em pelo menos uma destas categorias — se não se encaixa
em nenhuma, não é implementado:

| Categoria | Pergunta que responde | Exemplo |
|---|---|---|
| **Confirmação** | "meu clique/ação registrou?" | scale no botão ao pressionar, checkmark ao salvar |
| **Origem espacial** | "de onde veio esse elemento na tela?" | modal cresce a partir do botão que o abriu, dropdown expande do gatilho |
| **Mudança de estado** | "o que mudou desde a última vez que olhei?" | saldo atualizado (count-up), status de fatura mudou (crossfade do badge) |
| **Direção de atenção** | "para onde eu devia olhar agora?" | toast entrando, erro de validação aparecendo perto do campo |
| **Continuidade/hierarquia** | "esse elemento novo pertence a quê?" | layout animation quando uma linha de tabela é removida e as outras se reorganizam |

Uma animação puramente decorativa (que não responde a nenhuma dessas perguntas) é sempre
rejeitada, mesmo que "fique bonita" isoladamente — ver seção 7.

## 2. Princípios não-negociáveis

Nessa ordem de prioridade quando qualquer decisão de motion entrar em conflito:

1. **Legibilidade financeira sempre vence motion.** Nenhuma animação pode atrasar, ofuscar ou
   tornar ambíguo um valor monetário, status de pagamento ou data. Se uma animação e a leitura
   de um número competem por atenção no mesmo instante, a animação perde — é adiada, encurtada
   ou removida.
2. **Motion comunica estado, nunca decora.** Consequência direta da tabela da seção 1: toda
   animação existe porque um estado mudou (dado, foco, seleção, hierarquia), nunca "porque
   fica bonito" num elemento estático.
3. **Consistência de física vence variedade de efeito.** As mesmas duas ou três curvas e os
   mesmos três presets de spring (seção 4) são reutilizados em toda a interface. Um sistema
   onde tudo se move com a "mesma personalidade" parece mais caro e mais controlado do que um
   com muitos efeitos diferentes, mesmo que cada um individualmente seja bem feito.
4. **Interruptível e responsivo, nunca bloqueante.** Nenhuma animação impede o usuário de
   continuar digitando, clicando ou navegando. Uma transição em andamento pode ser
   interrompida por uma nova ação (ex.: fechar um modal que ainda está entrando) sem travar
   ou pular estados.
5. **Acessível por padrão, não como exceção.** `prefers-reduced-motion` não é um caso especial
   tratado depois — é verificado em todo componente com motion desde a primeira versão (seção
   8).

## 3. Referências — o que é herdado de cada uma, e o que não é

Estudadas pelo princípio que ensinam sobre movimento especificamente, nunca copiadas
literalmente (herda o critério já estabelecido em `docs/design-system.md`, seção 4, mas
aplicado a motion):

| Referência | O que herdamos | O que NÃO herdamos |
|---|---|---|
| **Motion design premiado (Awwwards, geral)** | precisão de timing, curvas com sensação física real (não `ease` genérico do CSS), coreografia onde a ordem de entrada dos elementos conta uma história espacial | densidade de efeito de página vitrine (scroll-jacking, parallax grande, reveals a cada scroll) — este é um dashboard denso de dado, revisitado dezenas de vezes, não uma landing page vista uma vez |
| **Apple (HIG / motion de sistema)** | a ideia de "spring física real" em vez de curva artificial, resposta imediata (<100ms) a toque/clique antes de qualquer animação maior começar | a abundância de profundidade/parallax entre camadas — aqui, hierarquia visual vem de superfície+borda (seção 11 do design-system), não de camadas 3D |
| **Linear / Raycast** (já citados no design-system) | microinterações rápidas (150-200ms), layout animations automáticas em listas | — (já coberto no design-system, seção 4) |
| **Stripe (documentação/dashboard)** | como comunicar mudança de valor numérico com um pulso de cor sutil em vez de um efeito chamativo, transições de estado de formulário (erro → válido) suaves e imediatas | a quantidade de motion decorativo do site de marketing da Stripe (fora do produto/dashboard) |

**Regra de síntese:** nenhuma combinação específica de duração+curva+easing deste documento
foi copiada inteira de uma única fonte — cada token da seção 4 foi decidido pelo caso de uso
deste app (dado financeiro, uso diário, usuário único), usando as referências acima como
critério de qualidade, não como template.

## 4. Vocabulário de duração e curva

Tokens espelhados em `docs/design-system.md` (seção 10.1) — este documento é a fonte
canônica; se algum dia os dois divergirem, este vale.

### 4.1 Durações

| Token | Valor | Quando usar | Por que esse valor |
|---|---|---|---|
| `--duration-instant` | 100ms | feedback de clique/toque (scale do botão, check de checkbox) | abaixo do limiar de ~100-130ms em que o cérebro humano deixa de perceber "atraso" — é o mínimo que ainda parece uma resposta, não um efeito |
| `--duration-fast` | 150ms | hover, toggle, ícone, rotação de seta de ordenação | rápido o bastante para não atrasar uma sequência de hovers ao passar o mouse por uma lista |
| `--duration-base` | 200ms | entrada/saída de dropdown, tooltip, popover | o "padrão" para elementos pequenos que aparecem perto de onde o usuário já está olhando |
| `--duration-moderate` | 300ms | modal, painel lateral, crossfade de badge de status | espaço suficiente para uma curva com leve overshoot ser percebida como física, sem parecer lenta |
| `--duration-slow` | 450ms | transição de página, stagger de lista (soma do delay entre itens + duração individual), draw-in de gráfico | o teto do sistema — nada dura mais que isso, mesmo em coreografias com múltiplos elementos (ver seção 5.2 sobre stagger com orçamento total) |

Não existe um token acima de 450ms. Se uma coreografia parece precisar de mais tempo, o
problema é o número de elementos em sequência (reduzir), não a duração de cada um (esticar).

### 4.2 Curvas (`cubic-bezier`)

| Token | Valor | Uso | Sensação |
|---|---|---|---|
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | ENTRADA — elemento aparecendo, crescendo, chegando | começa rápido, desacelera suave — objeto que "chega" e se acomoda, nunca bate |
| `--ease-in` | `cubic-bezier(0.7, 0, 0.84, 0)` | SAÍDA — elemento sumindo, encolhendo, saindo | começa devagar, acelera para fora — sai de cena sem chamar atenção de volta |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | movimento que começa e termina em repouso (drag, reordenação, layout shift) | simétrico — nem entrada nem saída, um deslocamento entre dois estados de repouso |

Nunca `ease`, `linear` ou `ease-in-out` genérico do CSS — todas as curvas deste sistema são
custom, calibradas para a sensação de "objeto físico com massa", não a curva default do
navegador (que é perceptivelmente mais "mecânica").

### 4.3 Springs (`motion`, física real)

Usados onde a animação precisa reagir a interrupção/gesto em vez de só tocar do início ao fim
(diferença chave entre spring e `duration`+`easing`: um spring pode ser interrompido e
continuar de forma fisicamente coerente a partir da velocidade atual; uma transição de
duração fixa, se interrompida, salta):

| Preset | Config | Uso | Sensação |
|---|---|---|---|
| `snappy` | `stiffness: 500, damping: 30` | microinterações (toggle, checkbox, botão, chip selecionado) | resposta quase instantânea, quicadinha mínima — "objeto leve e rígido" |
| `smooth` | `stiffness: 300, damping: 30` | modais, painéis, cards entrando, mudança de layout de lista | equilíbrio — nem lento nem abrupto, o spring "neutro" do sistema |
| `gentle` | `stiffness: 200, damping: 26` | número animado (count-up), barra de progresso, elementos grandes/hero | mais lento a se acomodar — apropriado para elementos grandes ou números onde um movimento abrupto pareceria errático |

Regra de escolha: se o elemento pode ser interrompido por uma ação do usuário no meio do
caminho (arrastar, fechar antes de terminar de abrir), usa spring. Se é uma transição que
sempre roda até o fim sem interação no meio (fade de tooltip, dropdown abrindo), usa
`duration`+`easing`.

## 5. Estados e transições

Taxonomia de toda transição de estado que existe na interface, e a regra de motion para cada
uma. Se um estado não está nesta lista quando um novo componente for construído, a
implementação para e a lista é atualizada antes de inventar um padrão ad-hoc.

### 5.1 Mount / unmount (entrada e saída de elemento)

Entrada: opacidade 0→1 + um deslocamento pequeno (4-8px, nunca mais que isso — um elemento
que "voa" de longe parece um efeito de apresentação, não uma aparição natural) na direção de
onde ele logicamente vem (dropdown vem de cima do gatilho, painel lateral vem da borda da
tela). `--ease-out`, duração conforme o tamanho do elemento (seção 4.1).

Saída: o inverso, mas mais rápido — sair de cena não precisa do mesmo cuidado perceptivo que
entrar (o usuário já processou o conteúdo), então a saída usa ~70% da duração da entrada
equivalente e `--ease-in`.

### 5.2 Hover / press / focus (microinteração)

Hover: mudança de cor/borda/sombra em `--duration-fast`, sem `--ease-out`/`--ease-in`
custom — transição CSS simples é suficiente e mais barata aqui (não é uma entrada/saída de
elemento, é uma reafirmação de um elemento que já existe).

Press: `scale(0.98)` com `snappy`, `--duration-instant`. Sempre acompanhado de alguma mudança
não-motion também (cor de fundo mais escura) — nunca só escala, para o estado continuar
detectável em screenshot/print e para usuários com sensibilidade a movimento perceberem a
mudança mesmo com motion reduzido.

Focus: aparição do anel de foco é instantânea (sem animação) — um atraso na indicação de foco
por teclado é uma barreira de acessibilidade, não uma oportunidade de polish.

### 5.3 Loading → carregado

Skeleton nunca "pisca" para dentro/fora abruptamente — crossfade de `--duration-base` entre
skeleton e conteúdo real. O shimmer do skeleton em si é contínuo enquanto carrega (ver seção
7 para o limite de tempo depois do qual isso deixa de ser aceitável) e para instantaneamente
(sem animação de "desligar") no exato frame em que o crossfade para o conteúdo começa.

### 5.4 Idle → selecionado/ativo

Item de navegação, linha de tabela selecionada, tab ativa: transição de cor/fundo em
`--duration-fast`, mais um indicador de posição que usa `layout` (o "pill" ou sublinhado que
se desloca de uma tab para outra desliza suavemente entre as duas posições em vez de
teleportar) — `smooth` spring.

### 5.5 Mudança de valor financeiro — a mais sensível de todas

Tratada em detalhe na seção 6 por ser o caso mais específico deste projeto.

### 5.6 Erro

Borda muda para `--color-negative` instantaneamente (sem transição de duração perceptível —
um erro precisa ser visto imediatamente, não "chegar suavemente"). A mensagem de erro
(`ValidationMessage`) entra com fade+slide-down de 4px, `--duration-fast`. **Sem shake.**
Decisão explícita: o padrão "input treme" de muitos formulários foi avaliado e rejeitado —
tremor é um efeito de alarme, e um formulário financeiro já usa cor+ícone+texto para
sinalizar erro; adicionar tremor é intensidade redundante que também é desconfortável para
usuários sensíveis a movimento (ver seção 8).

### 5.7 Sucesso

Toast de sucesso (`--color-positive`, ícone de check) — o check dentro do ícone é desenhado
via `pathLength` do `motion` de 0 a 1 em `--duration-base`, uma vez, `--ease-out`. Ação
concluída em um botão (`LoadingButton`) volta ao estado normal sem nenhuma celebração extra
além do toast — o objetivo emocional é "silenciosamente correto", nunca "comemoração", ver
seção 1 do design-system (confiança silenciosa).

### 5.8 Vazio → populado

Quando uma lista/tabela vazia recebe o primeiro item (ex. usuário cria a primeira Conta),
o `EmptyState` sai (`--ease-in`, `--duration-base`) e o primeiro item da lista entra
(`--ease-out`, mesmo padrão de mount normal) — nunca simultâneos de forma que se sobreponham
visualmente; o `EmptyState` termina de sair antes do conteúdo começar a entrar (evita dois
elementos concorrendo pelo mesmo espaço na tela ao mesmo tempo).

### 5.9 Reordenação / mudança de lista

`layout` do `motion` faz a transição automática (FLIP) quando um item é removido/adicionado/
reordenado — os itens vizinhos se movem suavemente para preencher o espaço, `smooth` spring.
Nunca implementado com animação manual de `top`/`margin` (motivo de performance, seção 9).

### 5.10 Transição de rota (página)

Fade simples do conteúdo de saída (`--duration-fast`, `--ease-in`) seguido do conteúdo de
entrada (`--duration-base`, `--ease-out`) — sem slide/wipe entre páginas. Decisão deliberada:
transições de página mais elaboradas (slide lateral, morph) são um dos efeitos mais citados
de sites premiados no Awwwards, mas exigem que a relação espacial entre as duas páginas faça
sentido (ex. "navegando para a direita na hierarquia") — a navegação deste app (sidebar fixa,
páginas irmãs sem hierarquia espacial entre si) não tem essa relação, então um slide seria
motion sem significado espacial real, violando o princípio 2 da seção 2. A barra de progresso
fina no topo (já especificada no design-system, seção 14) continua sendo o indicador
principal de navegação em andamento.

### 5.11 Hover com profundidade — tilt 3D + glow seguindo o mouse

Adicionado nos Ajustes de UX/UI que precederam a Etapa F9, para o `CartaoVisual` (`layout=
"full"`) — primeiro elemento do projeto com esse nível de resposta ao mouse. Regras, para
qualquer uso futuro do mesmo padrão:

- Implementado exclusivamente com `useMotionValue`/`useSpring`/`useMotionTemplate` do
  `motion` — nunca `useState` a cada `mousemove`. Um `set()` em motion value não dispara
  re-render de componente React; só a propriedade CSS (`transform`/`background`) muda a cada
  frame, mesmo princípio de performance da seção 9.
- Rotação máxima pequena (±5° neste caso, calculada como `(posição relativa - 0.5) × 10`) —
  um tilt exagerado (dezenas de graus) sai do território "profundidade sutil" (pedido
  explícito do usuário: "sem exagero, elegante") e passa a parecer instável/brincalhão,
  errado para um app financeiro (design-system.md, seção 1).
- O glow (`radial-gradient` de baixa opacidade posicionado na coordenada do mouse) usa o
  MESMO spring `gentle` (`lib/motion.ts`) que qualquer outra transição suave do projeto —
  nenhum spring novo inventado só para este componente.
- **Desligado inteiramente sob `prefers-reduced-motion`** (`useReducedMotion`, seção 8) —
  diferente de um crossfade que só perde a suavidade, tilt+glow desligados removem os
  listeners de `mousemove` por completo (não só zeram os valores), evitando trabalho de JS
  desnecessário para quem pediu menos movimento.
- **Nunca em elementos de lista densa** (ex. uma tabela com dezenas de linhas) — reservado
  para no máximo um ou dois elementos "hero" visíveis por vez (o preview do formulário, o
  card de destaque de uma página). `CartaoVisual` resolve isso com dois `layout`s
  (`"full"` tem o efeito, `"compact"`, usado na coluna da tabela, não tem) — mesmo raciocínio
  da seção 7 (habituação: motion rico demais, visto com frequência, para de comunicar
  qualquer coisa e vira ruído visual, além do custo real de dezenas de listeners de
  `mousemove` simultâneos).

## 6. Comunicando mudança de estado em dados financeiros

A categoria de motion mais específica deste projeto — nenhuma das referências da seção 3 é
primariamente um produto financeiro, então as regras abaixo foram desenhadas para este caso,
não emprestadas.

### 6.1 Count-up de valor monetário

- Acontece **uma única vez**: na primeira renderização real do valor (dado chegou da API pela
  primeira vez nesta sessão de navegação). Nunca ao trocar de aba e voltar, nunca ao
  revisitar com dado já em cache do React Query — um número que conta toda vez que a tela é
  vista deixa de comunicar "isso é novo" e passa a ser ruído (ver seção 7).
- Duração **não escala com a magnitude do valor**. Contar de R$ 0 a R$ 50.000 não pode
  demorar mais que contar de R$ 0 a R$ 500 — ambos usam o mesmo teto de tempo
  (`--duration-slow`, 450ms, spring `gentle`), senão um saldo alto vira uma animação
  visivelmente mais lenta que o normal, o que é um efeito colateral não intencional.
- O valor formatado (R$, separador de milhar, duas casas decimais) é aplicado a cada frame do
  spring, não só no valor final — evita o número "pular" de um formato intermediário estranho
  para o formato final no último frame.

### 6.2 Valor que muda depois de já visível (ex. saldo atualiza após uma transação)

Diferente do count-up (que é uma chegada), isto é uma **mudança** — o padrão é um pulso de
cor sutil, não uma recontagem do zero:

1. O número em si faz uma transição rápida do valor antigo para o novo (`--duration-base`,
   `gentle`, sem passar por valores "aleatórios" no meio — é uma interpolação direta antigo→
   novo).
2. Simultaneamente, o fundo do elemento (ex. célula ou card) recebe um pulso de
   `--color-positive-subtle` (se aumentou) ou `--color-negative-subtle` (se diminuiu) que
   aparece e desaparece em ~600ms total, **uma vez só**, nunca em loop.
3. Nunca as duas cores (número mudando de cor de texto + fundo pulsando) ao mesmo tempo —
   o pulso de fundo já comunica a direção; colorir o texto do número por cima seria
   redundante e competiria com as cores semânticas fixas (positive/negative da seção 6.4 do
   design-system, que têm significado fixo em badges de tipo — reaproveitar a mesma cor num
   contexto de "isto mudou" e não de "isto é receita/despesa" arrisca confundir os dois
   significados).

### 6.3 Transição de status (badge)

Ex. fatura muda de `ABERTA` para `FECHADA`, ou de `PENDENTE` para `PAGA`. Nunca um "pulo" de
cor abrupto — crossfade do Badge inteiro (cor de fundo + texto) em `--duration-moderate`,
`--ease-in-out`. Se a mudança de status é resultado direto de uma ação do próprio usuário
nesta tela (ex. clicou em "marcar como paga"), o crossfade acontece imediatamente após a
resposta da API confirmar. Se é um dado que já veio assim do servidor (ex. abriu a tela e a
fatura já estava fechada), **não anima** — anima só a transição que o usuário está
presenciando em tempo real, nunca o estado inicial de uma tela (reforça o princípio: motion
comunica mudança, e um estado que já chegou pronto não mudou durante a sessão do usuário).

### 6.4 Regra dura

Nenhuma animação pode fazer um valor financeiro passar visualmente por um número
intermediário que pareça um valor real por tempo suficiente para ser mal-lido (ex. um
count-up mal calibrado onde o número passa 200ms parado em um valor errado antes de
continuar). Interpolação sempre contínua, sem paradas no meio do caminho.

## 7. Quando animações NÃO devem acontecer

Lista explícita — cada item aqui já foi considerado e rejeitado, não é uma omissão:

- **Dado ainda carregando.** Nunca animar um placeholder numérico "contando" enquanto o valor
  real não chegou (é enganoso — parece que o número real já está sendo mostrado).
- **Sem relação com mudança de estado.** Qualquer motion que existiria só "porque fica
  bonito" num elemento que não mudou de estado (hover de decoração sem função, ícone que
  balança sozinho, background animado atrás de conteúdo) — rejeitado pelo princípio 2 da
  seção 2, sem exceção.
- **Ações repetidas rapidamente.** Se o usuário dispara a mesma transição várias vezes em
  sequência rápida (ex. incrementar um campo numérico clicando repetidamente), animações não
  se acumulam/enfileiram — cada nova ação cancela a anterior e começa da posição atual (usar
  spring, que suporta isso nativamente, nunca `duration` fixa reiniciando do zero a cada
  clique).
- **Bloqueando input.** Nenhuma animação impede o usuário de continuar digitando, clicando em
  outro lugar, ou navegando enquanto ela roda. Um modal que ainda está entrando já aceita
  `Esc` ou clique fora para começar a fechar antes de terminar de abrir.
- **`prefers-reduced-motion: reduce`.** Toda animação de posição/escala é substituída por um
  fade curto de opacidade (150ms) ou removida inteiramente quando a mudança em si é óbvia sem
  motion (ex. troca de cor de badge não precisa de nenhuma transição sob motion reduzido,
  a mudança instantânea de cor já comunica). Detalhe completo na seção 8.
- **Duas animações competindo pelo mesmo elemento.** Nunca um `Spinner` central sobreposto a
  uma área que já está em `Skeleton`, nunca um count-up rodando enquanto um pulso de mudança
  de valor (seção 6.2) também dispara para o mesmo número — sempre escolher uma.
- **Scroll de tabela/lista densa.** Nenhum efeito de reveal, parallax ou fade aplicado a itens
  conforme entram na viewport durante scroll de uma tabela de transações — o padrão "scroll
  reveal" comum em sites Awwwards é para conteúdo visto uma vez; numa tabela revisitada
  dezenas de vezes por dia, o mesmo efeito vira atraso perceptível cada vez que o usuário
  rola para ver mais linhas.
- **Habituação — mesmo o bem feito cansa com uso repetido.** Qualquer animação de entrada
  "grande" (stagger de vários itens, draw-in de gráfico) que existe hoje só acontece na
  primeira carga real dos dados (seções 6.1, 5.8) — nunca a cada visita à mesma tela com dado
  em cache. Este é o filtro mais importante que distingue "motion de vitrine vista uma vez" de
  "motion de ferramenta usada todo dia": o sistema é deliberadamente mais quieto na 50ª
  abertura do que na 1ª.

## 8. Acessibilidade

- **`prefers-reduced-motion: reduce` respeitado globalmente.** `motion` (Framer Motion)
  suporta nativamente via `MotionConfig reducedMotion="user"` no root da aplicação — toda
  animação de `motion` já cai automaticamente para um fade curto sem precisar de código
  condicional em cada componente. Para as transições CSS puras (`docs/design-system.md`,
  seção 10.1 — hover/foco/toggle), usa `@media (prefers-reduced-motion: reduce)`
  explicitamente em cada utilitário de transição, revertendo para opacidade em 150ms ou
  nenhuma transição.
- **Nenhuma informação é comunicada exclusivamente por motion.** Toda mudança de estado
  sinalizada por animação (seção 6) também é sinalizada por cor+texto+ícone de forma
  estática — motion é sempre reforço perceptual, nunca o único canal (um usuário com motion
  reduzido precisa entender o app inteiro sem ver nenhuma das transições descritas nas
  seções 5-6).
- **Segurança vestibular.** Sem parallax de grande amplitude, sem movimento contínuo/looping
  no conteúdo principal (o shimmer do skeleton é a única exceção — sutil, de baixo contraste,
  e já removido sob motion reduzido), sem autoplay de qualquer animação que o usuário não
  possa pausar (não aplicável hoje — não há vídeo/GIF no sistema).
- **Timing não interfere em foco/teclado.** Navegação por teclado (`Tab`, setas, atalhos) nunca
  espera uma animação terminar para responder — o estado lógico (o que está focado, o que
  está aberto) muda instantaneamente; só a representação visual é que anima por trás.
- **Checklist de implementação** (aplicado a cada componente com motion antes de ser
  considerado pronto): (1) funciona com `prefers-reduced-motion` ligado, testado de verdade,
  não assumido; (2) a informação que a animação comunica também existe sem ela; (3) pode ser
  interrompida por uma nova ação do usuário; (4) não há loop contínuo fora do shimmer de
  skeleton.

## 9. Performance

- **Só propriedades aceleradas por GPU são animadas continuamente:** `transform` (translate,
  scale, rotate) e `opacity`. Nunca `width`/`height`/`top`/`left`/`margin` diretamente em uma
  animação — quando um efeito de redimensionamento é necessário (ex. accordion), usa a técnica
  FLIP do `motion` (`layout` prop), que internamente anima `transform` e só ajusta o layout
  real no frame final.
- **Orçamento de stagger:** no máximo ~8-10 elementos em uma sequência com delay entre eles
  (ex. cards do dashboard aparecendo em sequência); acima disso, o delay entre o primeiro e o
  último item começa a ultrapassar a sensação de "uma coreografia" e vira "estar esperando a
  lista carregar" — listas maiores (ex. tabela de 50 transações) não fazem stagger item a
  item, só um fade único do conjunto.
- **Alvo de 60fps** em qualquer animação rodando simultaneamente a scroll ou digitação —
  testado em devtools (throttling de CPU) antes de um padrão novo ser considerado pronto.

## 10. Referência rápida (cheat sheet de implementação)

| Evento de UI | Padrão | Duração/curva |
|---|---|---|
| Hover de botão/link/linha | transição de cor CSS | `--duration-fast`, transição simples |
| Clique/press | `scale(0.98)` | `--duration-instant`, spring `snappy` |
| Dropdown/tooltip/popover abrindo | fade + 4-8px slide | `--duration-base`, `--ease-out` |
| Dropdown/tooltip/popover fechando | fade + slide inverso | ~140ms, `--ease-in` |
| Modal abrindo (+ backdrop) | scale(0.96→1) + fade | `--duration-moderate`, spring `smooth` |
| Modal fechando | fade + scale sutil para fora | ~210ms, `--ease-in` |
| Toast entrando | slide-up + fade | spring `smooth` |
| Badge/status mudando | crossfade | `--duration-moderate`, `--ease-in-out` |
| Valor monetário — primeira carga | count-up | `--duration-slow` (teto fixo), spring `gentle` |
| Valor monetário — mudou depois de visível | interpolação direta + pulso de fundo | `--duration-base` (número) + ~600ms (pulso) |
| Erro de validação | fade + slide-down 4px, sem shake | `--duration-fast` |
| Sucesso (ícone de check) | `pathLength` 0→1 | `--duration-base`, `--ease-out` |
| Linha de lista removida/reordenada | `layout` (FLIP) | spring `smooth` |
| Skeleton → conteúdo | crossfade | `--duration-base` |
| Transição de rota | fade saída → fade entrada | `--duration-fast` saída, `--duration-base` entrada |
| Stagger de lista (≤10 itens, primeira carga) | fade + 8px slide, delay ~40ms entre itens | `--duration-slow` total, `--ease-out` |

## 11. Relação com `docs/design-system.md`

Este documento substitui o conteúdo detalhado da seção 10 do design-system (que passa a ser
um resumo curto apontando para cá) e é a referência normativa para qualquer dúvida de timing
durante a implementação da Etapa F2 em diante. Nenhum outro documento deve introduzir uma
nova duração, curva ou spring sem atualizar a tabela da seção 4 aqui primeiro.

## 12. Próximos passos

Este documento não implementa nada. Ordem sugerida, junto com o restante da Etapa F2:

1. `MotionConfig reducedMotion="user"` no root da aplicação (`App.tsx`) — antes de qualquer
   outro componente com motion ser escrito, para que a regra da seção 8 nunca seja esquecida
   caso a caso.
2. Tokens de duração/curva como variáveis CSS (`:root`), presets de spring como constantes
   TypeScript exportadas (`lib/motion.ts` ou similar) para reuso em todos os componentes.
3. Implementar os padrões da seção 10 conforme cada componente da seção 14 do design-system
   for construído — nunca inventar timing novo por componente sem checar esta tabela primeiro.

Aguardando sua validação antes da implementação da Etapa F2 começar.
