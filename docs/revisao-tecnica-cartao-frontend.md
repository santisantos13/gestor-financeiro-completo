# Revisão técnica — Ajustes de UX/UI + Etapa F9 (CRUD de Cartão, frontend)

Implementação completa a partir de `docs/analise-arquitetural-cartao-frontend.md` (aprovada
antes de qualquer código) mais um bloco de melhorias de UX/UI pedido pelo usuário *antes* da
implementação do CRUD começar ("quero incorporar alguns ajustes de UX/UI ao Design System e
ao próprio módulo, mantendo toda a arquitetura já aprovada") — os dois foram feitos juntos
porque o segundo pedido chegou antes de qualquer código de Cartão existir. Quarta entidade de
CRUD real do frontend, depois de Conta (F6), Categoria (F7) e Tag (F8).

## 1. Ajustes de UX/UI ao Design System (antes do CRUD em si)

### 1.1 Escala global da interface

Pedido: aumentar a interface inteira em ~20-25%, sem hardcoded por componente, preparado
para uma futura preferência de densidade real. Mecanismo escolhido: `--ui-scale: 1.2`
(`src/index.css`) documenta o multiplicador; tipografia (`--text-*-size`) e radius
(`--radius-*`) já são variáveis CSS lidas por `tailwind.config.js` (`theme.extend.fontSize`/
`borderRadius`) — bumpar os valores em px em `index.css` propaga para todo componente sem
nenhuma mudança de código, mesmo mecanismo de baixo risco já usado pelo tema claro/escuro.

Espaçamento/altura/largura (`p-*`/`gap-*`/`h-*`/`w-*`, a escala padrão do Tailwind) NÃO é
uma variável CSS — não há como conectar isso a `--ui-scale` com segurança dentro de
`theme.spacing` (afetaria a geração automática de utilities negativas, ex. `-mt-1`, de forma
não testável sem um navegador real). Decisão: escalar em **build-time**, sobrescrevendo
`theme.spacing` inteiro em `tailwind.config.js` a partir da escala real do Tailwind
(`tailwindcss/defaultTheme`, nunca copiada à mão) multiplicada por uma constante
`UI_SCALE = 1.2` centralizada — `0px`/`1px` nunca escalam (a borda de 1px continua 1px).
Confirmado por inspeção do CSS gerado: `.p-4 { padding: 1.2rem }` (era `1rem`), `.gap-2 {
gap: .6rem }` (era `.5rem`), `.h-9 { height: 2.7rem }` (era `2.25rem`) — exatamente ×1.2 em
cada caso, nenhuma exceção encontrada.

Uma futura preferência de densidade real (Compacto/Padrão/Confortável) é a evolução natural
documentada em ambos os arquivos: trocar por `[data-density]` (mesmo padrão de
`[data-theme]`) e o `UI_SCALE` do Tailwind por `calc(valor * var(--ui-scale))` — não feito
agora porque exige teste em navegador real antes de ativar (indisponível neste ambiente de
desenvolvimento) e porque o próprio pedido do usuário já continha essa ressalva ("se
aumentar muito a complexidade, apenas reorganize os tokens").

### 1.2 `CartaoVisual` — "carteira digital premium"

Novo componente de apresentação puro (`components/domain/cartao/CartaoVisual.tsx`), não
acoplado a `CartaoRead`:

- Proporção real de cartão físico (`aspect-[1.586/1]`), gradiente de fundo com a cor de
  marca da instituição (seção 1.3), texto/dígitos mascarados (`•••• 1234`), badges de
  instituição e bandeira, `ProgressBar` de limite.
- Hover: elevação leve (`scale(1.02)`) + tilt 3D (rotação até ±5°, calculada a partir da
  posição do mouse relativa ao card) + glow (`radial-gradient` de baixa opacidade
  posicionado na coordenada do mouse) — implementado inteiramente com
  `useMotionValue`/`useSpring`/`useMotionTemplate` do Framer Motion, nunca `useState` a cada
  `mousemove` (evitaria re-render React por frame). Desligado por completo sob
  `prefers-reduced-motion` (`useReducedMotion`).
- Dois `layout`s no mesmo componente — `"full"` (o cartão premium completo, usado no preview
  ao vivo do `CartaoFormDialog` e automaticamente promovido a elemento principal do card
  mobile do `DataTable`, mecanismo que já existia) e `"compact"` (linha horizontal sem tilt,
  usada na coluna "Cartão" da tabela em desktop — uma tabela densa com dezenas de tilts 3D
  simultâneos prejudicaria performance e escaneabilidade; ver `docs/motion-principles.md`,
  nova seção 5.11).

### 1.3 `lib/cardThemes.ts` — temas visuais por instituição

Registry novo: resolve a instituição real via `resolveInstitution` (mesmo `id` de
`lib/institutions.ts`) e devolve as variantes de tema conhecidas — cada uma com um gradiente
de marca real (fato público) e uma cor de texto legível. Instituições sem tema específico (ou
não reconhecidas) caem num tema "Padrão" com tokens do Design System, nunca uma cor
inventada. Curadoria pequena e deliberada: Nubank, Inter, Santander, Itaú e Mercado Pago
ganharam uma segunda variante "premium" (ex. "Nubank Ultra", "Inter Black", "Mercado Pago
Premium Black") — as demais instituições citadas pelo usuário (Bradesco, Caixa, Banco do
Brasil, C6, PicPay, Neon, Sicredi, Sicoob, XP, BTG) têm só a variante de marca padrão.

Sobre a pedido de "Visa Platinum/Gold, Mastercard Platinum/Gold" (seção 2 abaixo): como
`Bandeira` é um enum fechado no backend sem nenhum conceito de tier, essa riqueza visual
foi resolvida **aqui**, como variante de tema por instituição, não como uma extensão
inventada do enum `Bandeira`.

A preferência de variante é **por cartão, puramente visual, persistida em `localStorage`**
(chave `financas:variante-tema-cartao`, um objeto `{ [cartaoId]: variantId }`) — nunca um
campo novo no backend, mesmo padrão já estabelecido por `ThemeContext`/`NavOrderContext`
para qualquer preferência de UI que não é dado de domínio. Um cache em memória do módulo
evita reler/parsear o JSON a cada linha da tabela a cada render (seção 5, Performance).

### 1.4 `lib/bandeiras.ts` + `BandeiraBadge`

Mesmo espírito de `lib/institutions.ts`/`InstitutionBadge`, mas para o enum fechado
`Bandeira` — monograma sobre a cor de marca pública real, sem `normalizar()`/aliases (não
precisa, é um mapa direto `Bandeira → { label, cor, sigla }`), sem SVG de logo real embutido
(mesma decisão de direitos de marca já documentada em
`docs/revisao-tecnica-branding-e-microinteracoes.md`, seção 2).

### 1.5 `ProgressBar` — prop `tone`

Evolução do componente existente (não um componente paralelo): ganhou `tone?:
"accent"|"warning"|"negative"`, default `"accent"` (comportamento idêntico ao de antes para
quem já usava o componente, ex. progresso de Meta). Usado pelo "progresso do limite" de
Cartão, que reage à proximidade do limite.

## 2. CRUD de Cartão (Etapa F9)

Contrato lido direto de `app/models/cartao.py`, `app/schemas/cartao.py`,
`app/services/cartao_service.py`, `app/repositories/cartao_repository.py` e
`app/api/routes/cartao.py`:

- `limite_disponivel` é sempre calculado pelo `CartaoService` (nunca uma coluna, mesmo
  princípio de `ContaRead.saldo_atual`) e **pode ficar negativo de propósito** (cartão
  "estourado") — o frontend exibe o valor exatamente como vem, nunca "clampado" em zero
  (`CartaoVisual` já mostra `formatMoney` de um número negativo sem tratamento especial, o
  `ProgressBar` também já lida com `value` acima de 100 via `clamped`).
- Reativação implícita ao criar com nome de cartão desativado (sobrescreve todos os campos),
  mesmo padrão exato de Tag/Categoria — tratado de forma inteiramente genérica pelo
  frontend, nenhum código condicional.
- Renomear nunca reativa/mescla — colisão de nome ao editar é sempre 409 puro.
- `conta_pagamento_id` de outro usuário é 404 (anti-enumeração/BOLA), mesmo padrão de
  `CategoriaService._resolver_pai` — `AccountSelect` só lista contas do próprio usuário, a UI
  naturalmente não oferece um ID inválido, mas a defesa real continua sendo o backend.

**Camada de dados** (mesmo molde de Conta/Categoria/Tag): `types/cartao.ts`
(`CartaoRead`/`CartaoCreate`/`CartaoUpdate`, monetário sempre `string`), `schemas/cartao.ts`
(Zod de formato — `instituicao` obrigatória, diferente de Conta, refletindo
`Field(min_length=1, ...)` sem `| None` em `CartaoCreate`; campo extra `variante_tema`,
nunca enviado ao backend), `services/cartaoService.ts`, `queryKeys.cartoes` e
`hooks/useCartaoQueries.ts` (mutations invalidam `cartoes.*` + `dashboard.cartoes` +
`dashboard.indicadores`, mesmo padrão de Conta com `dashboard.contas`).

**Componentes de domínio** (`components/domain/cartao/`): `CartaoVisual.tsx` (seção 1.2),
`cartaoTableColumns.tsx` (coluna "Cartão" usa `CartaoVisual layout="compact"`, colunas
"Limite"/"Disponível" com destaque em vermelho quando negativo, filtro por bandeira),
`CartaoFormDialog.tsx` (preview ao vivo com `CartaoVisual layout="full"`, seletor de
variante visual — só aparece quando a instituição digitada tem mais de uma variante
disponível — `AccountSelect`, `SelectField` de bandeira, `dia_fechamento`/`dia_vencimento`
lado a lado numa grade de duas colunas, conforme já antecipado em `design-system.md`, seção
17). `components/domain/conta/AccountSelect.tsx` — segundo select "inteligente" de domínio
do projeto, infraestrutura prevista desde a F1, ativada agora que `conta_pagamento_id`
precisou dela de verdade; mesmo molde de `CategorySelect`, mais simples (sem hierarquia).

**Página `/cartoes`** (`pages/cartoes/CartoesPage.tsx`): mesma composição de
`ContasPage.tsx`/`TagsPage.tsx` (`DataTable` + `*FormDialog` + `ConfirmAction`), com uma
faixa de `MetricCard` de indicadores no topo — primeira página de entidade a ter isso
(limite total, utilizado, disponível, cartões ativos — todos `reduce` sobre a listagem já
carregada, sem requisição nova). Busca inclui últimos 4 dígitos do cartão. Rota adicionada a
`AppRoutes.tsx` e item novo em `navItems.ts` (participa automaticamente da Organização da
Sidebar, sem nenhuma mudança extra nela).

## 3. Achado tratado sem pausa: riqueza visual de bandeira sem campo de tier

A análise arquitetural original (seção 8) já havia decidido `lib/bandeiras.ts` como um mapa
direto simples, sem tier. O pedido de UX/UI (item 3, "Visa Platinum/Gold" etc.) pareceria em
tensão com essa decisão — mas não é um conflito real de arquitetura: `Bandeira` continua um
enum fechado de 7 valores no backend, sem nenhum campo de tier, e nenhum código do frontend
inventa um. A riqueza visual pedida foi resolvida via `lib/cardThemes.ts` (seção 1.3),
reaproveitando o mesmo mecanismo de variante-por-cartão já decidido para o item 2 do pedido
("visual inspirado na instituição financeira... com opção de escolher uma variante visual
específica") — os dois pedidos (2 e 3) convergem para uma única peça de infraestrutura, sem
duplicação e sem alterar o contrato de `Bandeira`.

## 4. Validação realizada

- `tsc -b` limpo.
- `vite build` limpo: 2502 módulos, bundle principal ~693 KB (mesmo aviso de tamanho de
  chunk pré-existente, não uma regressão desta etapa).
- Confirmação direta do CSS gerado para a escala global (seção 1.1): `p-4`/`gap-2`/`h-9`
  todos exatamente ×1.2 do valor default do Tailwind.
- **Smoke test real contra um backend descartável isolado** (SQLite temporário em `/tmp`,
  nunca o `financas.db` do usuário; `SECRET_KEY` só de teste; `alembic upgrade head` rodado
  do zero): registro de dois usuários, login, criação de conta, criação de cartão
  (`limite_disponivel` retornado igual a `limite`, sem gastos ainda), tentativa de criar
  outro cartão com o mesmo nome (409, `"Já existe um cartão com este nome."`), tentativa de
  usar `conta_pagamento_id` de uma conta de outro usuário (404, `"Conta não encontrada."`),
  desativação (204), listagem `apenas_ativos=true` (vazio) e `apenas_ativos=false` (mostra o
  desativado), recriação com o mesmo nome (reativação implícita confirmada: mesmo `id`,
  campos sobrescritos com o payload novo, `ativo: true`), criação de um segundo cartão,
  tentativa de renomear o primeiro para o nome do segundo (409 puro, sem reativar — diferente
  do `POST`), reativação explícita via `PATCH {ativo:true}` (200, idempotente, preserva os
  dados da reativação implícita anterior). Todas as regras de negócio documentadas na
  análise arquitetural se comportaram exatamente como esperado.

### Como validar no navegador

1. Backend: `cd backend && cp .env.example .env` (edite `SECRET_KEY`), `alembic upgrade
   head`, `uvicorn app.main:app --reload`.
2. Frontend: `cd frontend && npm install && npm run dev`, abrir `http://localhost:5173`.
3. Registrar um usuário, criar ao menos uma Conta.
4. Ir em "Cartões" (novo item da Sidebar) → "Novo cartão": digitar "Nubank" em Instituição e
   observar o preview (`CartaoVisual`) mudar de gradiente cinza (padrão) para roxo (marca
   Nubank); se aparecer o seletor de variante (círculos de gradiente abaixo do campo
   Instituição), clicar na segunda opção ("Nubank Ultra") e ver o preview trocar para o
   gradiente escuro/violeta.
5. Passar o mouse sobre o preview do cartão (`layout="full"`) e observar o tilt 3D sutil +
   glow seguindo o cursor; testar com "Reduzir movimento" ativado no SO/navegador e
   confirmar que o cartão fica estático.
6. Preencher bandeira, últimos 4 dígitos, limite, dias de fechamento/vencimento (lado a lado)
   e conta de pagamento; salvar.
7. Na listagem, conferir que a coluna "Cartão" mostra o visual compacto (badges + nome +
   dígitos + barra de progresso) e que a faixa de indicadores no topo bate com a soma manual
   dos cartões visíveis.
8. Redimensionar a janela para mobile (< 768px) e confirmar que a linha da tabela vira um
   card com o `CartaoVisual` completo (mesmo componente, `layout="full"` automático).
9. Comparar o tamanho geral da interface com uma página antiga (ex. `/contas`) — ambas devem
   parecer maiores que antes desta etapa (mesma escala, ~20% acima do "Padrão" original).

## 5. Performance

- `useCartoes` já nasceu com `placeholderData: keepPreviousData`.
- Indicadores agregados são `reduce` simples sobre uma lista pequena (um usuário não tem
  dezenas de cartões na prática) — só um `useMemo` dependente de `cartoes`.
- `lib/cardThemes.ts` ganhou um cache em memória da preferência de tema por cartão — sem
  isso, `cartaoTableColumns`' `render` chamaria `lerVariantePreferida` (que faz `JSON.parse`
  de `localStorage`) uma vez por linha a cada render da tabela, incluindo a cada tecla
  digitada na busca (`DataTable` re-renderiza a lista filtrada inteira). O cache é invalidado
  só por uma escrita na própria sessão (`salvarVariantePreferida` atualiza os dois juntos).
- Tilt/glow do `CartaoVisual` usa exclusivamente motion values (`useMotionValue`/
  `useSpring`/`useMotionTemplate`) — nenhum `useState` no caminho do `mousemove`, então
  nenhum re-render React por frame; `layout="compact"` (usado na tabela, onde múltiplas
  linhas renderizam ao mesmo tempo) não anexa nenhum listener de `mousemove`.

## 6. Instabilidade recorrente do mount (FUSE) — mesma causa já documentada

Como em etapas anteriores, escritas via `Edit` neste ciclo mostraram conteúdo correto pela
ferramenta `Read` mas erro de sintaxe/truncamento pelo lado do `bash` em
`tailwind.config.js`, `src/index.css`, `api/queryKeys.ts`, `components/layout/navItems.ts`,
`components/ui/ProgressBar.tsx`, `routes/AppRoutes.tsx` e `lib/cardThemes.ts` — em todos os
casos o arquivo montado ficou **truncado em um ponto específico** (não corrompido com bytes
aleatórios), sempre coincidindo com o fim de uma janela de escrita. Mesma correção de
sempre: reescrita completa via heredoc + verificação de contagem de bytes, usando o conteúdo
confirmado pelo `Read` como fonte da verdade — `tsc -b`/`vite build` limpos na rodada
seguinte, toda vez.

## 7. Riscos conhecidos / decisões deixadas em aberto

- **Tilt 3D + glow não foram verificados visualmente** — este ambiente de desenvolvimento
  não tem acesso a um navegador real (`puppeteer`/`playwright` falham por falta de rede para
  baixar o binário do Chromium). A implementação foi revisada por código (mecânica de
  `useMotionValue`/`useSpring`/`useMotionTemplate`, ranges de rotação, desligamento sob
  `prefers-reduced-motion`) mas o resultado visual final deve ser conferido pelo usuário
  seguindo a seção 4, passo 5.
- **Slot de ícone/badge por opção em `SearchSelect`** — `AccountSelect` não mostra
  `InstitutionBadge` por opção no dropdown (decisão já registrada na análise arquitetural,
  seção 7): estender o `SearchSelect` genérico para isso é uma melhoria de infraestrutura
  futura, não decidida isoladamente para um único consumidor.
- **`CardSelect`** (`domain/cartao/CardSelect.tsx`) continua fora de escopo — nasce quando
  Transação for implementada, mesma decisão já tomada para `AccountSelect`/`TagSelect` antes
  de suas entidades consumidoras existirem.
- **Verdadeira preferência de densidade** (`[data-density]`, `calc()` em vez de valor
  estático) documentada como próximo passo natural em `index.css`/`tailwind.config.js`, não
  implementada agora por exigir teste em navegador real antes de ativar.

## 8. Conclusão

Ajustes de UX/UI e Etapa F9 concluídos juntos, sem nenhum conflito real de arquitetura
encontrado (a única tensão aparente — "tier" de bandeira sem campo correspondente no
backend — foi resolvida reaproveitando o mesmo mecanismo de variante de tema já necessário
para o pedido de personalização visual por instituição, seção 3). Escala global da interface
resolvida inteiramente no nível de token (zero mudança por componente); cartão de crédito
ganhou uma identidade visual própria e reaproveitável em três lugares (tabela, mobile,
formulário) sem duplicação. CRUD de Cartão valida ponta a ponta contra um backend real
descartável, incluindo os casos de reativação implícita/explícita, 409 de nome duplicado (em
criação e renomeação) e 404 anti-enumeração de conta de outro usuário.
