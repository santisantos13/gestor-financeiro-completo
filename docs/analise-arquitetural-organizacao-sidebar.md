# Análise arquitetural — Organização personalizada da Sidebar

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Primeira melhoria de
UX global do projeto (não é uma etapa de CRUD de entidade): permite ao usuário reordenar os
itens de navegação (exceto "Dashboard", sempre fixo em primeiro), com a ordem persistida só em
`localStorage`. Segue o mesmo protocolo já usado em toda etapa anterior — análise primeiro,
implementação só depois de aprovação explícita.

## 0. Checagem de arquitetura de projeto — nenhuma pendência encontrada

Antes de desenhar a feature em si, esta seção responde à pergunta que o pedido do usuário
exige responder primeiro: "isto exige alguma mudança de arquitetura do projeto inteiro?"

**Não.** Toda peça necessária já existe e é diretamente reaproveitável, sem adaptação:

- `components/layout/navItems.ts` já é a fonte única de verdade consumida por `Sidebar` e
  `MobileNav` (extraída exatamente para este tipo de crescimento, na etapa de Refinamento de
  UI) — reordenar é uma operação sobre essa lista, não uma lista nova.
- `ThemeContext`/`ThemeProvider` já é o precedente exato de "preferência de UI pura,
  persistida em `localStorage`, lida por componentes que não têm relação pai-filho entre si,
  alterada por um controle que mora em `UserMenu`". A nova preferência de ordenação segue a
  mesma forma (Provider + `localStorage`), não inventa um mecanismo novo.
- `FormDialog` já é decoupled de React Hook Form por design (`isDirty` é uma prop booleana
  pura, conforme o próprio comentário do componente) — reaproveitável como casca do modal de
  reordenação sem nenhuma mudança, mesmo o conteúdo não sendo um formulário de campos.
- `motion` (pacote `motion@^12.42.2`, já instalado) expõe `Reorder.Group`/`Reorder.Item` —
  primitivo de drag-and-drop com física real, mesma biblioteca já usada em todo o projeto.
  Nenhuma dependência nova.
- `lib/motion.ts` já tem todos os tokens de duração/curva/spring necessários
  (`SPRING.smooth` é o preset indicado por `docs/motion-principles.md`, seção 5.9, para
  "reordenação/mudança de lista").

A única decisão de composição (não de arquitetura de projeto) é **onde a ordem compartilhada
vive em memória** — resolvida na seção 4 abaixo pelo mesmo padrão do `ThemeProvider`, então
não é tratada como pendência a confirmar com o usuário.

## 1. Objetivo

Permitir que o usuário reorganize a ordem dos itens de navegação (Contas, Categorias, Tags, e
qualquer entidade futura) conforme sua preferência pessoal de uso, sem tocar o backend —
"é uma preferência exclusivamente visual", nas palavras do pedido. Dashboard nunca se move.

## 2. O que persiste, e onde

**Não é persistida a lista inteira de itens** (isso duplicaria `navItems.ts` em
`localStorage` e quebraria no dia em que um item for renomeado ou um ícone trocado — a cópia
salva ficaria com o label/ícone antigo). É persistida só a **ordem**, como um array de
identificadores estáveis:

```ts
// localStorage, chave "financas:ordem-navegacao"
["/tags", "/contas", "/categorias"]
```

Cada string é o `to` do `NavItem` (já é um identificador único e estável — é a própria rota).
`"/"` (Dashboard) nunca aparece nesse array: ele é tratado fora da lista reordenável em todas
as camadas (persistência, hook, UI), nunca como "o primeiro elemento de um array que por
convenção não deve mover" — reforçar a regra por construção evita a categoria inteira de bug
"esqueceram de checar se é o Dashboard antes de mover".

### 2.1 Reconciliação com `NAV_ITEMS` (por que nenhuma página futura exige refatoração)

A ordem final exibida nunca é o array salvo puro — é sempre derivada assim:

1. Pega `NAV_ITEMS` (sem o item Dashboard) como base.
2. Para os `to` que aparecem no array salvo, usa essa ordem relativa.
3. Qualquer item de `NAV_ITEMS` que **não** aparece no array salvo (página nova, adicionada
   depois que o usuário salvou sua preferência) é **anexado ao final**, na ordem em que já
   aparece em `NAV_ITEMS`.
4. Qualquer `to` no array salvo que **não** existe mais em `NAV_ITEMS` (rota removida) é
   descartado silenciosamente — nunca renderiza um item fantasma nem quebra.

Consequência direta: quando a Etapa F9 adicionar `{ to: "/cartoes", ... }` a `NAV_ITEMS`, o
item "Cartões" simplesmente aparece no fim da navegação de todo usuário que já tinha
personalizado a ordem — nenhuma migração de dado salvo, nenhum código novo no array de
`localStorage`, nenhuma alteração na etapa de Cartão além de adicionar a linha em
`navItems.ts` (exatamente como já acontece hoje sem esta feature). Esta reconciliação é uma
função pura (`reconciliarOrdem(navItems, ordemSalva) => NavItem[]`), testável isoladamente.

## 3. Onde o estado compartilhado vive: `NavOrderProvider`

Sidebar (em `AppLayout`) e o botão "Organizar navegação" (dentro de `UserMenu`, em `Header`)
não têm relação pai-filho — são ramos irmãos da árvore. Uma mudança salva no modal precisa
refletir em `Sidebar` e `MobileNav` sem recarregar a página. Mesmo problema que `ThemeContext`
já resolve para o tema claro/escuro, mesma solução:

- Novo `contexts/NavOrderContext.tsx`, mesmo formato de `ThemeContext.tsx`: lê
  `localStorage` de forma síncrona no `useState` inicial (`lerOrdemSalva()`, com o mesmo
  `try/catch` de proteção a `localStorage` indisponível que `ThemeContext`/`tokenStore` já
  usam), expõe `{ itensOrdenados: NavItem[], salvarOrdem: (ids: string[]) => void,
  restaurarPadrao: () => void }`.
- `itensOrdenados` já é o resultado da reconciliação da seção 2.1 — `Sidebar`/`MobileNav`
  passam a consumir `useNavOrder().itensOrdenados` em vez de importar `NAV_ITEMS` direto (a
  importação direta de `NAV_ITEMS` só continua existindo dentro do próprio
  `NavOrderContext.tsx`, que é o novo único ponto que precisa da lista "crua").
- `NavOrderProvider` entra em `App.tsx` no mesmo nível de `ThemeProvider` — "puramente UI
  local", fora de `QueryClientProvider`, mesmo comentário já existente no arquivo se aplica
  literalmente à nova preferência.

Este é o único novo Context do projeto desde `ThemeContext` — justificado pelo mesmo
critério que já existe implicitamente no código (comentário em `App.tsx`): preferência de UI
pura, sem servidor, lida por múltiplos ramos da árvore.

## 4. Onde o modal é aberto: `UserMenu`

Novo item de menu "Organizar navegação" dentro de `UserMenu.tsx`, no bloco "Aparência"
(mesmo bloco do `ThemeToggle`, logo abaixo dele — exatamente a posição pedida). O próprio
comentário já existente em `UserMenu.tsx` ("âncora para futuras opções de personalização... 
devem ganhar espaço NESTE menu no futuro") já antecipa este tipo de adição — não é a primeira
vez que o próprio código sinaliza essa direção.

```tsx
<Divider className="my-1.5" />
<button
  type="button"
  role="menuitem"
  onClick={() => { setOpen(false); setModalAberto(true); }}
  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm
             text-text-secondary transition-colors duration-fast ease-out
             hover:bg-surface-2 hover:text-text-primary"
>
  <ListOrdered size={14} aria-hidden="true" />
  Organizar navegação
</button>
```

Ícone `ListOrdered` (`lucide-react`, já disponível) — comunica "lista com ordem", coerente
com o significado da ação, sem colidir com nenhum ícone de entidade já usado em
`navItems.ts`/`lib/icons.ts`.

## 5. O modal: novo componente sobre `FormDialog`, não um modal novo do zero

`components/layout/OrganizarNavegacaoDialog.tsx` (mora em `layout/` como `MobileNav.tsx` e
`UserMenu.tsx` — é peça de navegação, não um componente de domínio de entidade nem um
primitivo genérico de `ui/`).

Reaproveita `FormDialog` inteiro como casca (título, botão "×", backdrop, foco preso, "só um
modal por vez", scroll do body bloqueado — tudo já implementado, zero duplicação):

```tsx
<FormDialog
  open={aberto}
  title="Organizar navegação"
  description="Arraste os itens para mudar a ordem do menu. O Dashboard permanece fixo."
  isDirty={ordemMudou}
  onClose={fechar}
  footer={(requestClose) => (
    <div className="flex items-center justify-between gap-2">
      <Button variant="ghost" size="sm" onClick={handleRestaurarPadrao}>
        Restaurar padrão
      </Button>
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={requestClose}>Cancelar</Button>
        <Button variant="primary" size="sm" onClick={handleSalvar}>Salvar</Button>
      </div>
    </div>
  )}
>
  {/* lista reordenável, seção 6 */}
</FormDialog>
```

Pontos de decisão registrados explicitamente (nenhum é uma pendência de arquitetura, são
decisões de composição desta feature):

- **`isDirty` aqui não vem de RHF** — vem de um `useState<string[]>` local com a ordem em
  edição, comparado ao array persistido (`ordemMudou = !arraysIguais(ordemEmEdicao,
  ordemPersistidaOuPadrao)`). É exatamente o caso que o comentário de `FormDialog`
  já previa ("não sabe nada de RHF por si, decoupled de propósito") — primeira vez que esse
  desacoplamento é exercido na prática, confirmando a decisão de design daquele componente.
- **"Cancelar" usa `requestClose`, não um `onClose` direto** — passa pelo mesmo fluxo de
  "descartar alterações?" que `Esc`/backdrop/"×" já usam se `isDirty`, nunca um atalho que
  perde a reordenação sem avisar (mesma regra que qualquer `FormDialog` de entidade já
  segue).
- **"Restaurar padrão" não salva sozinho** — só reseta a lista **em edição** para a ordem
  natural de `NAV_ITEMS` (a mesma reconciliação da seção 2.1, com `ordemSalva = []`). O
  usuário ainda precisa clicar "Salvar" para persistir — mantém um único ponto de
  confirmação (`Salvar`), consistente com o resto do formulário do app, em vez de duas ações
  que persistem por caminhos diferentes. Isso também faz "Restaurar padrão" participar do
  fluxo de `isDirty` normalmente: se restaurar e depois fechar sem salvar, a confirmação de
  "descartar alterações" dispara do mesmo jeito.
- **`Cancelar` e "×"/backdrop/Esc são logicamente idênticos** — todos chamam `requestClose`.
  Não existe um botão "Cancelar" com comportamento mais brando que fechar no X, coerente com
  o padrão já estabelecido em todo `FormDialog` do projeto.

## 6. Lista reordenável: `Reorder.Group` do `motion`

Dentro do corpo do modal (`children` do `FormDialog`, já com `overflow-y-auto` herdado):

```tsx
<div className="flex items-center gap-3 rounded-md border border-border-subtle bg-surface-2 px-3 py-2.5 opacity-70">
  <Lock size={14} className="text-text-tertiary" aria-hidden="true" />
  <LayoutDashboard size={18} className="text-text-tertiary" aria-hidden="true" />
  <span className="text-sm font-medium text-text-secondary">Dashboard</span>
  <span className="ml-auto text-caption text-text-tertiary">Sempre primeiro</span>
</div>

<Reorder.Group
  as="ul"
  axis="y"
  values={ordemEmEdicao}
  onReorder={setOrdemEmEdicao}
  className="mt-2 flex flex-col gap-2"
>
  {ordemEmEdicao.map((to) => {
    const item = itensPorTo.get(to)!;
    return (
      <Reorder.Item
        key={to}
        value={to}
        as="li"
        dragListener={false}
        dragControls={controlesPorTo.get(to)}
        transition={SPRING.smooth}
        className="flex items-center gap-3 rounded-md border border-border bg-surface-3 px-3 py-2.5 shadow-sm"
      >
        <button
          type="button"
          onPointerDown={(e) => controlesPorTo.get(to)!.start(e)}
          aria-label={`Arrastar para reordenar ${item.label}`}
          className="cursor-grab touch-none rounded-sm p-1.5 text-text-tertiary active:cursor-grabbing hover:bg-surface-4 hover:text-text-primary"
        >
          <GripVertical size={16} aria-hidden="true" />
        </button>
        <item.icon size={18} className="text-text-secondary" aria-hidden="true" />
        <span className="text-sm font-medium text-text-primary">{item.label}</span>
        <div className="ml-auto flex gap-0.5">
          <button type="button" onClick={() => moverParaCima(to)} disabled={ehPrimeiro(to)}
                  aria-label={`Mover ${item.label} para cima`} className="...">
            <ChevronUp size={16} aria-hidden="true" />
          </button>
          <button type="button" onClick={() => moverParaBaixo(to)} disabled={ehUltimo(to)}
                  aria-label={`Mover ${item.label} para baixo`} className="...">
            <ChevronDown size={16} aria-hidden="true" />
          </button>
        </div>
      </Reorder.Item>
    );
  })}
</Reorder.Group>
```

Decisões de mecânica, com justificativa:

- **`dragListener={false}` + `useDragControls` por item + `onPointerDown` só no ícone
  `GripVertical`** — em vez do item inteiro ser arrastável a partir de qualquer ponto. Um
  clique nos botões de mover-para-cima/baixo (seção 7) ou em qualquer área do card não deve
  iniciar um drag por acidente; só a alça explícita inicia.
- **"Preview imediato" já é intrínseco ao `Reorder.Group`** — `onReorder` atualiza o estado
  local a cada troca de posição durante o próprio gesto de arrastar (não só ao soltar), então
  a lista visível já É a prévia da nova ordem, sem lógica extra de "modo preview".
- **`transition={SPRING.smooth}`** em cada `Reorder.Item` — mesmo preset que
  `docs/motion-principles.md`, seção 5.9, já define para "reordenação/mudança de lista"
  (`layout` FLIP com spring `smooth`). Nenhum timing novo inventado.
- **Card do Dashboard fica fora do `Reorder.Group`** — não é um `Reorder.Item` com drag
  desabilitado (o que ainda apareceria como um item "quase arrastável" na lista, ambíguo
  visualmente); é um elemento estático separado, visualmente distinto (`opacity-70`, ícone de
  cadeado, legenda "Sempre primeiro") — a UI comunica a regra sem o usuário precisar tentar
  arrastar para descobrir que não funciona.

## 7. Acessibilidade e teclado — alternativa sem gesto de arrastar

`Reorder.Group` do `motion` não tem suporte nativo a teclado (é puramente baseado em gesto de
ponteiro) — o princípio 3 de `docs/design-system.md` ("teclado em primeiro lugar") e a seção
23 (acessibilidade) exigem que a funcionalidade inteira funcione sem mouse/toque. Solução:
cada item ganha um par de botões `ChevronUp`/`ChevronDown` ("mover para cima"/"mover para
baixo"), sempre visível (não só em hover — visibilidade condicionada a hover exclui
teclado/touch), com:

- `aria-label` descritivo por botão (inclui o nome do item, não só "mover para cima" genérico
  — útil para leitor de tela que não vê a proximidade visual do botão ao item).
- `disabled` no primeiro item (botão "cima") e no último (botão "baixo") — mesmo padrão de
  `disabled` que `Pagination`/`RowActions` já usam para limites de lista.
- Foco por `Tab` alcança a alça de drag e os dois botões de cada item, na ordem visual —
  `Reorder.Item as="li"` não precisa de `tabIndex` próprio (não é ele o alvo interativo, os
  botões dentro são).
- Mover via teclado dispara a mesma função que atualiza `ordemEmEdicao` que o `onReorder` do
  drag dispara — um único caminho de mutação de estado, dois gatilhos de UI. Reordenação por
  teclado também anima com `SPRING.smooth` (é o mesmo `layout`/`Reorder.Item`, só a origem do
  evento muda).
- **Checklist da seção 8 de `docs/motion-principles.md`** aplicado: funciona com
  `prefers-reduced-motion` (o `Reorder.Item` ainda reordena, só sem a animação de
  deslocamento — `MotionConfig reducedMotion="user"` já global no `App.tsx` cobre isso sem
  código extra); a informação (nova posição) existe sem animação; interrompível (arrastar um
  item enquanto outro ainda está em transição não trava, `Reorder` já lida com isso
  nativamente); nenhum loop contínuo.

## 8. Mobile

- Modal: mesma casca responsiva que todo `FormDialog` já tem (`max-w-lg`, `p-4` de margem de
  viewport, `max-h-[85vh]` com corpo scrollável) — nenhum ajuste extra necessário.
- Drag por toque: `Reorder` do `motion` já suporta `pointer events` (mouse e touch
  unificados) — funciona em mobile sem código condicional. A alça (`GripVertical`) mais os
  botões cima/baixo têm `p-1.5` de padding somado ao ícone, atingindo os 40px mínimos de área
  de toque exigidos pela seção 23 do design-system para telas <768px (classe utilitária já
  usada em `RowActions`/botões de ação de tabela para o mesmo fim).
- `touch-none` na alça de drag (Tailwind `touch-action: none`) — evita que o gesto de
  arrastar o item também dispare scroll da página por trás em iOS/Android, problema comum de
  drag-and-drop touch sem esse ajuste.

## 9. Motion — resumo do que é novo vs. reaproveitado

| Elemento | Padrão | Novo ou reaproveitado |
|---|---|---|
| Abertura/fechamento do modal | `modalBackdrop`/`modalPanel` (`FormDialog`) | 100% reaproveitado |
| Reordenação (drag ou teclado) | `layout` + spring `smooth` (`Reorder.Item`) | Reaproveita o preset (`SPRING.smooth`), primeira aplicação de `Reorder` no projeto |
| Hover da alça/botões | transição de cor CSS, `--duration-fast` | 100% reaproveitado (mesmo padrão de qualquer botão ghost) |
| Press da alça (início do drag) | nenhuma animação de escala própria — o próprio deslocamento já comunica "agarrado" | decisão consciente: um `scale` de press somado ao drag já em andamento seria dois efeitos competindo pelo mesmo elemento (motion-principles.md, seção 7, "duas animações competindo pelo mesmo elemento") |
| Card fixo do Dashboard | nenhuma animação (elemento estático) | não aplicável — reforça que ele não participa do gesto |

Nenhuma duração/curva/spring nova é introduzida — toda a coreografia usa vocabulário já
existente em `lib/motion.ts`.

## 10. Consistência visual

- Cards de item reordenável usam os mesmos tokens de superfície/borda/radius que qualquer
  card de lista do projeto (`bg-surface-3`, `border-border`, `rounded-md`) — mesma hierarquia
  visual de `TableRow`/itens de popover, não uma linguagem visual nova.
- Ícones de cada item são os mesmos já usados em `Sidebar`/`MobileNav` (`item.icon` vem do
  mesmo `NavItem`) — o usuário reconhece visualmente qual item é qual sem reaprender nada.
- Tipografia/spacing do modal seguem exatamente `FormDialog` (título `text-h3`, descrição
  `text-sm text-text-secondary`, padding `p-5`) — zero CSS novo em nível de estrutura do
  modal, só o conteúdo interno (lista) é próprio desta feature.

## 11. Performance

Lista pequena por natureza (hoje 3 itens reordenáveis + Dashboard fixo; crescimento é uma
entidade por etapa, então mesmo em um horizonte de anos dificilmente passa de ~15-20) — sem
necessidade de virtualização. `Reorder.Group`/`layout` do `motion` já usa `transform` (GPU),
consistente com a seção 9 de `docs/motion-principles.md`. Persistência em `localStorage` é
síncrona e do tamanho de um array de strings curtas — sem custo perceptível mesmo no clique
de "Salvar".

## 12. Fora de escopo (explicitamente, para não crescer sozinho)

- Ocultar itens de navegação (só reordenar — "todas as demais páginas podem ser
  reorganizadas", não removidas).
- Agrupar itens em seções/categorias dentro da navegação.
- Sincronizar a ordem entre dispositivos/sessões (explicitamente rejeitado pelo usuário —
  "não quero backend").
- Reordenar os itens `/dev/*` (não aparecem em `NAV_ITEMS`, continuam fora da navegação real
  e fora deste sistema, mesma regra que já existia).

## 13. Critérios de pronto

- Dashboard nunca aparece na lista reordenável e nunca perde a primeira posição, em nenhum
  cenário (localStorage vazio, corrompido, ou com uma ordem válida salva).
- Reordenar via drag e via teclado (`ChevronUp`/`ChevronDown`) produzem o mesmo resultado
  final e a mesma persistência.
- Fechar sem salvar (`Esc`, backdrop, "×" ou "Cancelar") depois de reordenar dispara a
  confirmação de descarte já existente em `FormDialog`, e a ordem visível em
  `Sidebar`/`MobileNav` permanece a anterior.
- "Restaurar padrão" seguido de "Salvar" volta a navegação para a ordem natural de
  `NAV_ITEMS`, e um novo "Restaurar padrão" sem salvar não altera nada persistido.
- Uma página nova adicionada a `NAV_ITEMS` no futuro aparece automaticamente ao final da
  ordem de todo usuário que já personalizou a navegação, sem nenhuma mudança em código fora
  do próprio `navItems.ts`.
- `prefers-reduced-motion` testado de verdade: reordenação ainda funciona (drag e teclado),
  só sem a animação de deslocamento.
- `tsc -b` e `vite build` limpos; validação manual em desktop e em viewport mobile
  (drag por toque simulado + os dois botões de teclado).

## 14. Próximos passos

Aguardando aprovação. Se aprovado, implementação segue esta ordem:

1. `contexts/NavOrderContext.tsx` (`NavOrderProvider`, `useNavOrder`) + wire em `App.tsx`.
2. Atualizar `Sidebar.tsx`/`MobileNav.tsx` para consumir `useNavOrder().itensOrdenados` em vez
   de `NAV_ITEMS` direto.
3. `components/layout/OrganizarNavegacaoDialog.tsx` (lista + `Reorder.Group` + botões de
   teclado + rodapé Restaurar/Cancelar/Salvar).
4. Item "Organizar navegação" em `UserMenu.tsx`.
5. Validação: `tsc -b`, `vite build`, teste manual (drag mouse, drag touch via devtools,
   teclado, `prefers-reduced-motion`, item novo simulado em `NAV_ITEMS` para confirmar
   auto-extensão).
6. Atualizar README se necessário; `docs/revisao-tecnica-organizacao-sidebar.md` com o
   resumo de entrega.

Sem código escrito nesta etapa, conforme solicitado.
