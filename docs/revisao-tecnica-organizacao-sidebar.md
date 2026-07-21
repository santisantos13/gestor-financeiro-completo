# Revisão técnica — Organização personalizada da Sidebar

Implementação completa a partir de `docs/analise-arquitetural-organizacao-sidebar.md`
(aprovada antes de qualquer código). Primeira melhoria de UX global do projeto — não é uma
etapa de CRUD de entidade, é uma reorganização opcional e puramente visual da navegação.

## 1. O que foi entregue

**`contexts/NavOrderContext.tsx`** (novo) — `NavOrderProvider` + função pura
`reconciliarOrdem(navItems, ordemSalva)`. Mesmo formato de `ThemeContext.tsx`: estado React
inicializado de forma síncrona a partir de `localStorage` (`lerOrdemSalva()`, mesmo
`try/catch` de proteção contra `localStorage` indisponível que `ThemeContext`/`tokenStore`
já usam). Expõe `{ itensOrdenados, ordemAtual, salvarOrdem, restaurarPadrao }`.

**`hooks/useNavOrder.ts`** (novo) — mesmo padrão de `hooks/useTheme.ts` (`useContext` +
`throw` se usado fora do Provider).

**`App.tsx`** — `NavOrderProvider` adicionado no mesmo nível de `ThemeProvider` (fora de
`QueryClientProvider`, mesmo comentário já existente no arquivo: "puramente UI local").

**`components/layout/Sidebar.tsx` / `MobileNav.tsx`** — pararam de importar `NAV_ITEMS`
direto para a lista exibida; agora renderizam `[ITEM_DASHBOARD, ...useNavOrder().itensOrdenados]`.
`NAV_ITEMS` continua sendo importado nos dois só para extrair o item fixo do Dashboard
(`NAV_ITEMS.find((item) => item.to === "/")`). Nenhuma outra mudança nos dois componentes —
motion, estilos e mecânica de foco continuam exatamente como estavam.

**`components/layout/OrganizarNavegacaoDialog.tsx`** (novo) — o modal em si. `FormDialog`
como casca (título, "×", backdrop, foco preso, `isDirty`/confirmação de descarte, "só um
modal por vez" — zero duplicação). Corpo: card fixo do Dashboard (fora da lista arrastável,
visualmente distinto — cadeado + opacidade reduzida) seguido de `Reorder.Group` do `motion`
com um `Reorder.Item` por página reordenável. Rodapé com "Restaurar padrão" (esquerda),
"Cancelar"/"Salvar" (direita).

**`components/layout/UserMenu.tsx`** — novo item "Organizar navegação" no bloco "Aparência",
logo abaixo do `ThemeToggle` (posição pedida explicitamente). Abre
`OrganizarNavegacaoDialog`, renderizado fora do popover do menu (portal próprio via
`FormDialog`).

## 2. Onde a ordem vive, e por quê

Só é persistido um array de rotas (`["/tags", "/contas", "/categorias"]`), nunca a lista de
itens inteira — evitaria duplicar `navItems.ts` dentro do `localStorage` e ficaria
desatualizado no dia em que um label/ícone mudasse. A ordem final exibida é sempre
**derivada**, nunca lida direto: `reconciliarOrdem(NAV_ITEMS, ordemSalva)` remove o
Dashboard da lista reordenável, aplica a ordem salva aos itens que ela conhece, e anexa ao
final qualquer item de `NAV_ITEMS` que não apareça no array salvo. Esta é a peça central que
cumpre o requisito "nenhuma página futura deve exigir refatoração": quando uma etapa futura
adicionar uma linha nova em `navItems.ts` (exatamente como já acontecia antes desta etapa,
para Contas/Categorias/Tags), o item novo aparece automaticamente no fim da navegação de
todo usuário que já personalizou a ordem — nenhuma migração de `localStorage`, nenhuma
mudança em `NavOrderContext.tsx`, nenhuma mudança nesta feature.

Rotas salvas que não existem mais (página removida) são descartadas silenciosamente pela
mesma função — sem item fantasma, sem erro.

## 3. Sincronização entre Sidebar/MobileNav e o modal

`Sidebar` (dentro de `AppLayout`) e o botão que abre o modal (dentro de `UserMenu`, em
`Header`) são ramos irmãos da árvore — sem relação pai-filho. Uma ordem salva no modal
precisa refletir nos dois sem recarregar a página. É exatamente o mesmo problema que
`ThemeContext` já resolve para tema claro/escuro, resolvido com a mesma solução: um Context
acima dos três (`NavOrderProvider` em `App.tsx`). Nenhum mecanismo novo foi inventado —
`NavOrderContext.tsx` segue a forma de `ThemeContext.tsx` linha por linha (estado inicial
síncrono de `localStorage`, funções memoizadas com `useCallback`, degradação silenciosa se
`localStorage` estiver indisponível).

## 4. O modal: `FormDialog` reaproveitado sem nenhuma adaptação

`isDirty` de `OrganizarNavegacaoDialog` não vem de React Hook Form — vem da comparação entre
a ordem em edição (`ordemEmEdicao`, estado local) e a ordem que estava ativa quando o modal
abriu. A análise arquitetural já havia identificado que `FormDialog.isDirty` é "decoupled de
propósito" (comentário original do próprio componente, de quando foi construído na etapa de
Formulários) — esta é a primeira vez que esse desacoplamento é exercido na prática, e
funcionou exatamente como o comentário previa, sem nenhuma mudança em `FormDialog.tsx`.

Consequência direta: fechar o modal com `Esc`, clique no backdrop, "×" ou "Cancelar" depois
de reordenar dispara a mesma confirmação de "Descartar alterações?" que qualquer formulário
de entidade do projeto já usa — nenhum caminho de fechar contorna essa checagem, "Cancelar"
inclusive (chama o mesmo `requestClose` do `Esc`/backdrop, não um `onClose` direto).

"Restaurar padrão" só reseta a lista **em edição** para a ordem natural de `NAV_ITEMS` — não
persiste sozinho. O usuário ainda precisa clicar "Salvar" para confirmar, mantendo um único
ponto de persistência no fluxo inteiro (evita dois caminhos de gravação com semânticas
diferentes). Isso também faz "Restaurar padrão" participar do `isDirty` normalmente: restaurar
e fechar sem salvar ainda pede confirmação de descarte.

## 5. Drag-and-drop: `Reorder.Group`/`Reorder.Item` do `motion`

Primeira aplicação de `Reorder` no projeto — já fazia parte do pacote `motion@^12.42.2`
instalado desde a Etapa F2 (é um re-export de `framer-motion`, confirmado lendo
`node_modules/framer-motion/dist/index.d.ts`), nenhuma dependência nova.

- **Alça isolada** (`GripVertical`) — cada `Reorder.Item` usa `dragListener={false}` e uma
  `dragControls` própria (`useDragControls()`, chamada dentro de um componente por item,
  `ReorderableNavItem` — nunca dentro do `.map()` do pai, porque hooks não podem ser
  chamados condicionalmente/em loop de forma seura ali). O gesto de arrastar só começa no
  `onPointerDown` do ícone da alça — clicar em qualquer outra parte do card (label, ícone da
  página, botões de mover) não inicia um drag por acidente.
- **Preview imediato é intrínseco ao `Reorder.Group`** — `onReorder` atualiza o estado local
  a cada troca de posição durante o próprio gesto (não só ao soltar), então a lista visível
  já é a prévia da nova ordem, sem lógica extra.
- **`transition={SPRING.smooth}`** em cada item — exatamente o preset que
  `docs/motion-principles.md` (seção 5.9) já define para "reordenação/mudança de lista", sem
  nenhum timing novo.
- **Card do Dashboard fica fora do `Reorder.Group`** — elemento estático separado, nunca um
  `Reorder.Item` com drag desabilitado (o que ainda pareceria "quase arrastável"). Visual
  distinto (opacidade, ícone de cadeado, legenda "Sempre primeiro") comunica a regra sem o
  usuário precisar tentar arrastar para descobrir que não funciona.

## 6. Acessibilidade e teclado

`Reorder` do `motion` não tem suporte nativo a teclado — é puramente baseado em gesto de
ponteiro. Cada item ganhou um par de botões `ChevronUp`/`ChevronDown` ("mover para
cima"/"para baixo"), **sempre visíveis** (não condicionados a hover, o que excluiria
teclado/leitor de tela), com `aria-label` que inclui o nome do item, e `disabled` no
primeiro/último item da lista (mesmo padrão de limite que `Pagination`/`RowActions` já
usam). Mover via teclado dispara a mesma função de mutação de estado que o `onReorder` do
drag dispara — um único caminho de mutação, dois gatilhos de UI, mesma animação
(`SPRING.smooth`) em ambos os casos.

`prefers-reduced-motion`: coberto globalmente por `MotionConfig reducedMotion="user"` (já no
root de `App.tsx` desde a Etapa F2) — a reordenação continua funcionando (drag e teclado), só
sem a animação de deslocamento entre posições.

## 7. Mobile e responsividade

Modal: mesma casca responsiva que todo `FormDialog` já tem
(`max-w-lg`, `p-4` de margem de viewport, `max-h-[85vh]` com corpo scrollável) — nenhum
ajuste extra. Drag por toque funciona sem código condicional (`Reorder` do `motion` já
unifica mouse/touch via pointer events). Alça e botões cima/baixo usam `h-10 w-10` (40px),
cumprindo a área de toque mínima da seção 23 do design-system para telas <768px. `touch-none`
na alça evita que o gesto de arrastar também dispare scroll da página por trás em
iOS/Android.

## 8. Validação realizada

- `tsc -b` limpo, sem nenhuma rodada de correção necessária (diferente de quase todas as
  etapas anteriores, que sempre enfrentaram pelo menos um round de instabilidade do mount
  FUSE — não ocorreu desta vez).
- `vite build` limpo via workaround de diretório temporário: 2491 módulos, bundle principal
  654 KB (crescimento de ~10 KB sobre a F8, esperado pela adição de `Reorder`/modal novo —
  mesmo aviso de tamanho de chunk pré-existente, não uma regressão desta etapa).
- `vite preview` + `curl` confirmando HTTP 200 e HTML servido corretamente (sem corrupção de
  build).
- **Limite desta validação**: o sandbox de execução não tem acesso de rede para baixar um
  Chromium (`npx playwright install`/`puppeteer` falharam por `getaddrinfo EAI_AGAIN` ao
  tentar buscar o binário), então não foi possível automatizar o próprio gesto de
  arrastar-e-soltar nem o clique nos botões dentro de um navegador real neste ambiente. A
  lógica foi verificada por leitura cuidadosa do código e pelo fato de `tsc -b` validar os
  tipos de toda a integração com `Reorder`/`useDragControls` (a API do `framer-motion` é
  suficientemente tipada para pegar a maioria dos erros de uso incorreto em tempo de
  compilação). Passos de validação manual no navegador estão na seção "Como testar" abaixo —
  recomendado antes de considerar a etapa definitivamente fechada.

## 9. Riscos conhecidos / decisões deixadas em aberto

- **Sem sincronização entre dispositivos/sessões** — decisão explícita do pedido original
  ("não quero backend"), documentada também na análise arquitetural.
- **Sem suporte a ocultar itens** — só reordenar, conforme escopo pedido.
- **Lista pequena hoje (3 itens reordenáveis)** — a mecânica de drag/teclado foi desenhada
  para escalar (nenhuma virtualização necessária até algumas dezenas de itens), mas só será
  exercida de verdade com uma lista maior conforme F9+ adicionar entidades.
- **Nenhum teste automatizado de interação (drag real) existe para esta feature** — mesma
  limitação de sandbox da seção 8; se o projeto ganhar Playwright/Cypress no futuro, este é
  um bom candidato a primeiro teste E2E de UI pura (sem depender de backend).

## 10. Conclusão

Etapa concluída seguindo exatamente a análise arquitetural aprovada, sem nenhuma pausa para
pergunta durante a implementação. Reaproveitamento total de `FormDialog` (casca do modal),
`lib/motion.ts` (`SPRING.smooth`, nenhum timing novo), e do padrão já estabelecido por
`ThemeContext` (Provider + `localStorage` para preferência de UI pura). Único componente
novo de fato: `OrganizarNavegacaoDialog` (e seu subcomponente interno
`ReorderableNavItem`). `Sidebar`/`MobileNav` tiveram a menor mudança possível (uma linha de
import trocada, uma linha de dado trocada) — toda a lógica de ordenação/persistência mora
isolada em `NavOrderContext.tsx`.

## 11. Como testar no navegador

1. Suba o backend (`uvicorn app.main:app --reload`, dentro de `backend/`, com o venv ativado)
   e o frontend (`npm run dev`, dentro de `frontend/`) em dois terminais separados.
2. Faça login normalmente.
3. Clique no seu nome/avatar no canto superior direito (abre o `UserMenu`).
4. Logo abaixo do toggle de tema (claro/escuro), clique em **"Organizar navegação"**.
5. No modal: arraste os itens pela alça (ícone de "pontinhos" à esquerda de cada linha) para
   reordenar — a lista já reflete a nova ordem em tempo real. "Dashboard" aparece separado no
   topo, com um cadeado, e não pode ser arrastado.
6. Alternativa por teclado: use `Tab` para focar os botões de seta (▲/▼) de cada item e
   `Enter`/`Espaço` para mover — sem precisar do mouse.
7. Clique **"Salvar"** — o modal fecha e a `Sidebar` (desktop, ≥768px) já mostra a nova
   ordem imediatamente, sem recarregar a página.
8. Reduza a janela para <768px (ou abra o menu hambúrguer no celular) — confira que
   `MobileNav` (o painel que desliza da esquerda) mostra a mesma ordem.
9. Recarregue a página inteira (F5) — a ordem personalizada continua lá (persistida em
   `localStorage`, sem precisar de login novamente nem de rede).
10. Abra o modal de novo, mude a ordem e feche com "×", `Esc` ou clicando fora — deve
    aparecer a tela "Descartar alterações?" (porque a ordem foi mexida e não foi salva).
11. Abra o modal, clique **"Restaurar padrão"** e depois **"Salvar"** — a navegação volta à
    ordem original (Contas, Categorias, Tags).
12. (Opcional, avançado) No DevTools do navegador, em "Rendering" → "Emulate CSS media
    feature prefers-reduced-motion: reduce" — repita os testes de arrastar/teclado acima e
    confirme que a reordenação ainda funciona, só sem a animação de deslocamento.
