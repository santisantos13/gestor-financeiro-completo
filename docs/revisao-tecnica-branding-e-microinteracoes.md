# Revisão técnica — Branding de Instituições + Microinterações (Etapa de Refinamento Visual)

Revisão final da etapa, mesmo padrão de toda revisão técnica anterior do projeto. Escopo:
etapa de polish puramente visual/UX sobre o que já existe — nenhuma regra de negócio,
nenhum contrato de API, nenhum arquivo de backend tocado. Pedido explícito do usuário,
em sete frentes (branding de instituições, hover em geral, cards, tabelas, sidebar,
StatCard, laboratório `/dev`) mais um pedido adicional (menu do usuário com toggle de
tema). Releitura de `docs/design-system.md`, `docs/motion-principles.md`,
`docs/analise-arquitetural-frontend.md` e `docs/analise-arquitetural-dashboard.md` feita
antes de qualquer código, conforme convenção do projeto.

## 1. O que foi entregue

**Registry de branding** (`lib/institutions.ts`): `resolveInstitution(instituicao)`
resolve nome/cor de marca/monograma para qualquer valor livre de `instituicao` —
normaliza acento/caixa e casa contra uma lista de 17 instituições conhecidas (Nubank,
Inter, Santander, Itaú, Bradesco, Caixa, Banco do Brasil, C6, Neon, PicPay, Mercado
Pago, Wise, PayPal, XP, BTG, Sicredi, Sicoob); instituição digitada mas não reconhecida
ainda resolve para um objeto sintético com o próprio texto do usuário e cor neutra
(nunca falha, nunca inventa nome). `corDeContraste()` escolhe preto ou branco para o
texto do monograma por luminância relativa — necessário porque a paleta real inclui
cores muito claras (Banco do Brasil, `#FADB00`) e muito escuras (C6, `#242424`).
`components/ui/InstitutionBadge.tsx` é a única peça visual que consome esse registry
(selo colorido com monograma + nome opcional, ícone `Landmark` neutro quando
`instituicao` é `null`) — usada em `contaTableColumns.tsx`, `ContaFormDialog.tsx`
(preview ao vivo via `useWatch`, isolado num componente próprio para não re-renderizar
o diálogo inteiro a cada tecla) e nos cards `ContasCard`/`CartoesCard` do Dashboard, no
lugar dos ícones genéricos fixos (`Landmark`/`CreditCard`) que existiam antes.

**Tema claro/escuro** (`src/index.css`, `contexts/ThemeContext.tsx`,
`hooks/useTheme.ts`, `components/ui/ThemeToggle.tsx`, `index.html`): `[data-theme="light"]`
adicionado ao lado do `:root`/`[data-theme="dark"]` original — tipografia, espaçamento,
radius, motion e blur são idênticos entre temas (não dependem de cor); só as seções 6.1-
6.6 de `design-system.md` (superfícies, texto, acento, semânticas financeiras, cores de
gráfico) têm um bloco por tema. `ThemeProvider` persiste em `localStorage`
(`financas:tema`) e escreve `data-theme` no `<html>`; um script síncrono em `index.html`
já aplica o tema salvo antes do React montar, evitando flash do tema errado.
`ThemeToggle` é um segmented control de dois ícones (`Moon`/`Sun`) com um indicador que
desliza entre eles (`layoutId`, mesmo padrão do item ativo da `Sidebar`).

**Menu do usuário** (`components/layout/UserMenu.tsx`): abre ao clicar no nome/avatar no
`Header` (pedido explícito, "adicionar um botão de configurações ao clicar no nome do
usuário"). Mesma mecânica de popover de `Select.tsx` (clique-fora fecha, `Esc` fecha,
fade+slide de 4px). Contém: cabeçalho com avatar/nome/email, seção "Aparência" com o
`ThemeToggle`, e o botão "Sair" (que antes vivia solto no `Header`, agora só aqui
dentro). O código documenta explicitamente que este menu é a âncora para onde futuras
opções de personalização (densidade de tabela, cor de acento, fonte) devem crescer —
pedido explícito do usuário para não espalhar preferências de UI pelo app.

**Microinterações**:
- `Button.tsx` — elevação de 1px no hover via `whileHover` do Framer Motion (nunca
  `translate` via classe Tailwind no mesmo elemento — ver seção 2), glow discreto de
  acento (`--shadow-glow-accent`, token novo) na variante primária, borda reagindo na
  secundária.
- `Card.tsx` — elevação de 2px no hover (`whileHover`), borda `--color-border-strong`,
  `--shadow-sm` (já existia); ganhou uma prop opcional `animateEntrance` (fade + 8px
  slide-up na montagem, `--duration-moderate`/`--ease-out`) — desligada por padrão para
  não reanimar em remontagens frequentes (ex. item de lista filtrada).
- `StatCard.tsx` — usa `animateEntrance` do `Card`; ícone reage com escala+rotação sutil
  no próprio hover (`SPRING.snappy`). `AnimatedNumber` não foi tocado — pedido explícito
  do usuário ("números mantendo o padrão já existente").
- `TableRow.tsx` — barra de acento de 3px na borda esquerda via `box-shadow: inset` no
  hover e permanentemente quando `selected` (mesma linguagem visual para os dois
  estados).
- `Sidebar.tsx` — ícone do item de navegação ganha `scale-110` no hover do item inteiro
  (CSS `group-hover`, não `whileHover` aninhado — ver seção 2); indicador do item ativo
  ganha o mesmo glow discreto do botão primário.

**`/dev`**: três seções novas ("Aparência", "Branding de instituições financeiras",
"Botões — microinterações de hover") mais notas atualizadas nas seções existentes
(`StatCard`, rodapé) explicando onde ver o resto (Sidebar só é visível na navegação
real; tabela em `/dev/tables`).

## 2. Decisões tomadas sem pausar — e por quê

- **`whileHover` do Framer Motion em vez de classe Tailwind `translate` para a elevação
  de `Button`/`Card`.** Os dois componentes já usam `motion.button`/`motion.div` (o
  segundo, novo nesta etapa) para `whileTap`. `whileTap` e uma classe CSS
  `hover:-translate-y-px` no MESMO elemento disputariam a mesma propriedade `transform`
  — o Framer Motion controla `transform` diretamente via seu próprio sistema de motion
  values, e uma classe CSS aplicando `transform` por cima entraria em conflito
  (nenhuma composição automática entre os dois sistemas). A correção foi usar
  `whileHover` do próprio Framer para a elevação também — `whileHover` e `whileTap`
  compõem corretamente entre si por design da biblioteca, então elevação de hover e
  "press" de clique nunca brigam, mesmo em sequência rápida (passar o mouse e clicar
  imediatamente).
- **`group-hover` CSS (não `whileHover` aninhado) para o ícone da `Sidebar`.** Um
  `motion.span` com `whileHover` próprio só dispara quando o cursor está exatamente
  sobre aquele span — passar o mouse no resto do item (o texto do label, por exemplo)
  não acionaria a reação do ícone. `group-hover` reage ao hover do item INTEIRO
  (`NavLink` pai com a classe `group`), que é o comportamento esperado ("item reage ao
  passar o mouse", não "só o ícone reage a ser mirado com precisão").
- **Barra de acento em `TableRow` via `box-shadow: inset`, não `border-left`.** A
  `Table` usa `border-collapse: collapse` (design-system.md, seção 18 e `Table.tsx`
  original) — bordas reais em células/linhas de uma tabela com `border-collapse` têm
  comportamento de renderização inconsistente entre navegadores nas bordas
  compartilhadas entre linhas adjacentes. `box-shadow` não é afetado por
  `border-collapse` (a propriedade é ortogonal ao modelo de bordas colapsadas da
  tabela) e renderiza de forma confiável em `<tr>` nos navegadores atuais — a mesma
  técnica list em blogs e usada em produtos como o Notion para esse exato efeito.
- **`animateEntrance` como prop opt-in no `Card` genérico, não um comportamento
  automático.** `Card` é reaproveitado em dezenas de lugares, muitos deles remontando
  com frequência (ex. um item de lista filtrada, que remonta a cada mudança de filtro
  se a `key` mudar). Dar entrada automática a TODO `Card` violaria a regra de
  "habituação" de `motion-principles.md`, seção 7 ("qualquer animação de entrada
  'grande' só acontece na primeira carga real dos dados... nunca a cada visita/remontagem
  com dado já familiar"). Tornar opt-in e usá-lo só em `StatCard` (cujo mount real
  coincide com a chegada do dado do Dashboard, a mesma garantia que já protege o
  count-up de `AnimatedNumber`) mantém a regra sem exigir um `Card` "burro" reescrito do
  zero.
- **Sem SVGs de logo real de instituição financeira.** O pedido era "sempre que
  possível utilize os logotipos oficiais em SVG". Avaliado e conscientemente adiado:
  reunir e embutir artes vetoriais oficiais precisas de 17 marcas dentro do tempo desta
  etapa exigiria visitar cada site/imprensa oficial, validar licença de uso de cada uma
  individualmente, e garantir consistência de `viewBox`/proporção entre elas — risco
  real de qualidade (arte incorreta ou mal proporcionada) maior que o benefício de
  "logo real aproximado de memória". Em vez disso, cada instituição ganhou um monograma
  sobre a cor de marca REAL (fato público, não protegido por direito autoral) — resolve
  visualmente "logo/nome/cor" pedido, e a arquitetura do registry já isola esse ponto:
  adicionar uma arte SVG real no futuro é um campo novo em `InstitutionInfo` mais um
  branch em `InstitutionBadge.tsx`, sem tocar em nenhum dos quatro consumidores atuais
  (Conta, Cartão, Dashboard) nem em qualquer entidade futura.
- **Cores semânticas financeiras recalibradas por tema, não reaproveitadas.** Os tons
  "400" da escala usados no tema escuro (`#34D399`/`#FB7185`/`#FBBF24`) foram calibrados
  especificamente para contraste sobre fundo escuro (design-system.md, seção 6.5,
  "tonalidades 400 da escala Tailwind, deliberada para funcionar bem sobre fundo
  escuro"). Usar os MESMOS tons sobre fundo branco reduziria o contraste abaixo do
  confortável para leitura de dado financeiro (princípio 1 de design-system.md, seção
  1: "clareza do dado financeiro sempre vence"). O tema claro usa os tons "600"
  correspondentes (mais escuros/saturados) da mesma família de cor — mesma identidade,
  contraste ajustado ao fundo.
- **Ripple explicitamente descartado.** O pedido listava "ripple elegante (se fizer
  sentido)" como opcional. Avaliado e rejeitado: um ripple (onda expandindo do ponto de
  clique) é um efeito reconhecível de Material Design, inconsistente com a identidade
  "confiança silenciosa" e "identidade visual própria, não a soma de referências
  reconhecíveis" já estabelecida em `design-system.md`, seções 1 e 4 — mesmo raciocínio
  que já rejeitou "shake" em erro de validação na Etapa F5
  (`docs/revisao-tecnica-formularios.md`).
- **Toggle de tema reabre uma decisão registrada como fechada.** `design-system.md`,
  seção 0, havia decidido explicitamente "dark-only, sem toggle" mas deixou escrito
  "se você queria um toggle de verdade... me avise antes de eu seguir para a
  implementação". O pedido desta etapa é exatamente esse aviso, chegando depois. A
  seção 0 foi atualizada com uma nota de "Atualização" preservando o registro histórico
  da decisão original (por que ela fazia sentido NAQUELE momento) em vez de apagá-la —
  mesmo padrão já usado no próprio documento para a mudança de direção estética
  anterior.

## 3. Validação realizada

- **`tsc -b`** — limpo, verificado após cada arquivo novo/editado e novamente no
  fechamento da etapa.
- **`vite build`** (via workaround de build fora do mount) — limpo, `2467` módulos
  transformados; CSS final conferido via `grep` para confirmar que os dois blocos de
  tema (`[data-theme="dark"]`/`[data-theme="light"]`) e o token `--shadow-glow-accent`
  sobreviveram à minificação (`grep -o 'data-theme=' ` encontrou as duas variantes no
  CSS compilado). Mesmo aviso de chunk >500KB já conhecido das etapas anteriores
  (~603KB minificado agora), não é um erro novo desta etapa.
- **Validação visual no navegador**: pendente de confirmação do usuário — este ambiente
  não tem acesso a um navegador conectado à instância real de desenvolvimento do
  usuário. Recomendado abrir `http://localhost:5173/dev` (galeria de badges de
  instituição, toggle de tema, hover de botões), `/dev/tables` (hover/seleção de linha),
  `/` (StatCards com entrada e ícone reagindo, ContasCard/CartoesCard com badge de
  instituição), `/contas` (coluna de instituição, preview ao vivo no formulário) e
  clicar no nome no canto superior direito para abrir o `UserMenu` e alternar o tema.

## 4. Riscos conhecidos / dívida técnica sinalizada, não corrigida agora

- **Sem logotipo oficial real de instituição** — ver seção 2. A arquitetura já suporta a
  extensão; a arte em si fica para uma etapa futura caso o usuário priorize.
- **Paleta de tema claro não passou por verificação formal de contraste WCAG** (a
  verificação da seção 6.5 do design-system original foi feita para o tema escuro
  especificamente). Os tons escolhidos para o tema claro seguem a mesma heurística já
  usada no projeto (tons "600" da escala Tailwind são geralmente considerados seguros
  para texto sobre branco), mas não foram medidos numericamente nesta etapa.
- **`box-shadow: inset` em `<tr>` para a barra de acento de `TableRow`** — funciona nos
  motores de renderização atuais (Chromium/Firefox/WebKit), mas não foi testado
  visualmente nesta sessão (sem acesso a navegador). Se algum navegador específico não
  renderizar corretamente, o pior caso é a barra simplesmente não aparecer (hover em si
  continua funcionando via `bg-surface-2`, que já era a implementação original e é uma
  propriedade CSS mais amplamente suportada em `<tr>`).
- **Cores de gráfico do tema claro** (`--color-chart-*`) foram recalibradas por
  analogia às semânticas financeiras (tons "600"), mas nenhum gráfico real do projeto
  usa esses tokens ainda (a lib de gráfico segue "decisão adiada", design-system.md,
  seção 16) — validação real só será possível quando um gráfico existir.

## 5. Conclusão

Etapa de Refinamento Visual implementada seguindo `docs/design-system.md` e
`docs/motion-principles.md`, sem nenhuma alteração de backend, contrato de API ou regra
de negócio — puramente uma camada de apresentação sobre entidades e fluxos que já
existiam. O registry de branding (`lib/institutions.ts` + `InstitutionBadge`) resolve
exatamente o pedido de "um único lugar decidindo logo/nome/cor/fallback, nunca switch
espalhado", já reaproveitado por Conta/Cartão/Dashboard e pronto para qualquer entidade
futura. O tema claro/escuro reabre, com autorização explícita do usuário, uma decisão
que o próprio `design-system.md` já havia deixado em aberto desde a F2. Todas as
microinterações passam pelos tokens já existentes de `motion-principles.md` (springs
`snappy`/`smooth`, durações e curvas), sem timing novo inventado fora do único token
novo desta etapa (`--shadow-glow-accent`, um glow, não uma duração/curva/spring — fora
do escopo da tabela de motion). Build e typecheck limpos. Falta apenas a confirmação
visual do usuário no navegador para considerar a etapa inteiramente encerrada.
