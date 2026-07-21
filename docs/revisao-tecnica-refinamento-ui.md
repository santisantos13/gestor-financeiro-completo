# Revisão técnica — Refinamento de UI (UX/UI/Performance/Responsividade)

Etapa sem funcionalidade nova: revisão crítica de tudo que já existia no frontend
(`/contas`, `/categorias`, Dashboard, `Sidebar`/`Header`, sistema de tabelas e formulários)
seguida de correções pontuais. Pedido explícito do usuário: "o objetivo não é adicionar
funcionalidades novas, e sim elevar a qualidade da experiência". Cada mudança abaixo é
presentational ou de infraestrutura genérica (`DataTable`, hooks de query) — nenhum
contrato de backend, regra de negócio ou schema de formulário mudou.

## 1. Achados e correções, por área pedida

### 1.1 Categoria Pai precisava de destaque

**Antes**: a tabela de `/categorias` mostrava pai e filha como linhas idênticas, na ordem
que o backend devolvesse — só uma coluna de texto "Categoria pai" (e essa coluna nem
aparecia no card mobile, ver 1.2). Não havia nenhuma forma de perceber a hierarquia "sem
precisar pensar".

**Depois**:
- `ordenarCategoriasPorHierarquia()` (nova, em `categoriaTableColumns.tsx`) reordena a
  lista recebida por `CategoriasPage` para que cada categoria pai apareça imediatamente
  seguida de suas subcategorias (recursiva, embora o backend hoje só permita um nível;
  ordem entre irmãos preserva a ordem original). Categorias "órfãs" — cujo
  `categoria_pai_id` aponta para um id fora da lista atual carregada, ex. quando o filtro
  "apenas ativas" esconde o pai — viram raiz visualmente, nunca somem da listagem.
- A coluna "Nome" (`buildCategoriaTableColumns`) agora calcula `profundidade` (0 para
  raiz, 1+ para subcategorias, via `calcularProfundidade` andando pelos pais com proteção
  contra ciclo) e `totalFilhos` (contagem de subcategorias diretas) para cada linha, e
  indenta 20px por nível com um conector sutil (`CornerDownRight`, `lucide-react`,
  `text-text-tertiary`) — nunca um badge escrito "Pai"/"Filha", conforme pedido
  explicitamente. Categorias com filhos ganham uma legenda discreta ao lado do nome ("2
  subcategorias").
- `ordenarCategoriasPorHierarquia` só decide a ORDEM; `buildCategoriaTableColumns` só
  decide a APARÊNCIA de cada linha — as duas funcionam juntas mas são independentes.
  Ordenar explicitamente por uma coluna (clique no cabeçalho) sobrepõe a ordem
  hierárquica dentro de `useDataTable`, o que é o comportamento esperado (é uma ação
  explícita do usuário).
- A coluna de texto "Categoria pai" foi mantida (útil quando a hierarquia visual está
  quebrada por um sort explícito), mas continua fora do card mobile via `hideOnMobile`
  (agora de fato respeitado, ver 1.2) — a indentação por si só já comunica a hierarquia
  lá.

### 1.2 Bug real de responsividade: `hideOnMobile` nunca era aplicado

`ColumnDef.hideOnMobile` existe no tipo (`types/table.ts`) desde a Etapa F4 e é usado por
`categoriaTableColumns.tsx` (coluna "Categoria pai") e `contaTableColumns.tsx` (coluna
"Instituição") — mas `DataTable.tsx` nunca filtrava por ele: o card mobile iterava
`table.visibleColumns` inteiro, mostrando todas as colunas, inclusive as marcadas para
ficar de fora. Corrigido com `mobileColumns = table.visibleColumns.filter((c) =>
!c.hideOnMobile)`, usado só na renderização de card (a tabela real em `md+` continua
usando todas as `visibleColumns`, sem mudança).

### 1.3 Bug real de responsividade: não havia navegação nenhuma abaixo de `md`

`Sidebar` é `hidden md:flex` — abaixo de `md` a `<aside>` inteira desaparece, e até esta
etapa não existia nenhum substituto: no celular era impossível navegar entre `/`,
`/contas` e `/categorias` a não ser digitando a URL manualmente.

Corrigido com:
- `components/layout/navItems.ts` (novo) — `NAV_ITEMS` extraído de dentro de
  `Sidebar.tsx` para um módulo compartilhado, para `Sidebar` e a navegação mobile nunca
  divergirem.
- `components/layout/MobileNav.tsx` (novo) — painel desliza da esquerda (`x: "-100%" →
  0`, spring `{ stiffness: 300, damping: 30 }`), backdrop com blur (mesmo par visual de
  `FormDialog`), fecha com `Esc`, clique no backdrop ou ao selecionar um item. Foco preso
  dentro do painel enquanto aberto e devolvido ao botão que abriu ao fechar — mesma
  mecânica de acessibilidade já usada por `FormDialog` (nenhum padrão novo inventado).
- `Header.tsx` ganhou um botão de menu (ícone `Menu`, `lucide-react`) visível só abaixo de
  `md`, que abre o `MobileNav`. `px-6` fixo virou `px-4 sm:px-6` (menos espaço perdido em
  telas muito estreitas).
- `AppLayout.tsx`: `<main>` de `p-6` fixo para `p-4 sm:p-6` — 24px de padding de cada lado
  em uma tela de ~360px de largura sobrava pouco espaço útil.

### 1.4 Performance percebida: causa concreta, não só latência

Investigação encontrou uma causa real, não hipotética:

- `<motion.tbody>` em `DataTable.tsx` usava como `key` a string
  `${table.page}-${table.query}-${...}` — incluindo `table.query`, a busca **crua**, não
  `deferredQuery`. Resultado: cada tecla digitada no campo de busca trocava a `key`,
  forçando o React a desmontar e remontar o `<tbody>` inteiro (disparando o fade de
  `--duration-base` de novo a cada caractere), mesmo com `useDeferredValue` já presente em
  `useDataTable.ts` — o adiamento existia mas era anulado pelo remonte. Essa é a causa
  mais provável do "site parece lento" relatado, especificamente durante busca em
  tabelas. Corrigido removendo `table.query` da `key` — trocar de página, filtro ou
  ordenação continua remontando com fade (mudança de contexto real, vale a transição
  visual); digitar não mais.
- `useCategorias`/`useContas` ganharam `placeholderData: keepPreviousData`
  (`@tanstack/react-query` v5). Alternar o switch "mostrar inativas" troca a `queryKey`
  (o parâmetro `apenasAtivas` muda) — sem isso, a tabela piscava um `LoadingTable`
  (skeleton cheio) a cada toggle; agora mantém a lista anterior visível até a nova
  chegar. O refetch de rede continua acontecendo normalmente, isso é só sobre o que fica
  na tela enquanto ele resolve.
- `RowActions` ganhou uma prop `size` (`"sm" | "md"`, default `"sm"`) — usada como `"md"`
  apenas no card mobile de `DataTable` (as ações lá já ficam sempre visíveis, ao contrário
  do hover-only do desktop), dando um alvo de toque de 36px em vez dos 28px fixos
  anteriores.
- `TableCell` foi de `px-3 py-2.5` para `px-4 py-3` — aplica-se a toda tabela do projeto
  (Conta, Categoria, `/dev/tables`) de uma vez, por ser um componente central; não é uma
  otimização de performance, é a correção de "tabelas apertadas" pedida na seção de
  distribuição de elementos.

Não foi encontrado nenhum outro gargalo real de render (sem `useMemo`/`useCallback`
faltando em ponto quente, sem `key` instável fora do caso acima, sem componente
recriando função em loop de forma que custe visivelmente). O restante da lentidão
percebida, se houver, é latência real de rede local (`localhost:8000`) — mitigada pelas
duas mudanças de `placeholderData` acima, que é exatamente a ferramenta certa para esse
caso (não há como eliminar uma requisição real com otimização de render).

### 1.5 Responsividade — demais telas revisadas

`ColorField`: popover de paleta de sugestão não tinha limite de largura — em telas muito
estreitas podia ultrapassar a borda do `FormDialog`. Ganhou `w-56 max-w-[85vw]` (mesmo
padrão já usado por `IconField`, que já tinha `max-w-[90vw]`).

Dashboard (`IndicadoresStrip`, grid de `StatCard`/`MetricCard`, `DashboardPage`) já usava
breakpoints `grid-cols-2 → sm:grid-cols-4 → lg:grid-cols-8` e `lg:col-span-*` de forma
consistente — revisado, nenhuma mudança necessária ali.

### 1.6 Distribuição de elementos e tipografia

`TableCell` (seção 1.4) foi o ajuste de distribuição com maior alcance — toda tabela do
projeto ganhou mais respiro sem mudar a densidade de informação.

A escala tipográfica (`docs/design-system.md`, seção 7) não foi alterada. O texto de
tabela (`--text-sm`, 13px) é intencionalmente compacto — dado tabular denso é o caso de
uso documentado — e o pedido explícito foi "ajuste apenas quando realmente melhorar a
usabilidade, não aumente tudo indiscriminadamente". Nenhum ponto encontrado na revisão
justificava aumentar fonte por si só sem mexer em espaçamento/densidade junto (o que
mudaria a escala planejada do Design System sem necessidade real).

`Card` (usado em 16 arquivos, 36 ocorrências — todo o Dashboard) não foi alterado por
decisão deliberada: aumentar o padding padrão arriscaria quebrar layouts densos já
ajustados (StatCard, MetricCard, os cards de resumo) sem uma verificação visual de cada
um, fora do escopo de uma revisão que deveria ser conservadora sobre o que já funciona.

### 1.7 Áreas clicáveis

Coberto em 1.4 (`RowActions` `size="md"` no mobile). Verificados e considerados
adequados: `Input`/`ColorField`/`IconField` (h-9 = 36px), `Switch` (36×20px, alvo real
maior que o trilho visual pelo `<button>` envolvente), `SortHeader` (área clicável é o
`<button>` inteiro do cabeçalho, não só o texto), `Pagination` (`Button size="sm"`,
consistente com o resto do design system em contexto desktop).

### 1.8 Motion

A correção da seção 1.4 (remoção de `table.query` da `key` do `tbody`) é tanto uma
correção de performance quanto de motion: elimina uma transição que disparava sem
necessidade real (motion-principles.md, seção 7 — "habituação": animação repetida sem
propósito cansa e não comunica nada). Nenhum timing novo foi inventado em nenhuma
mudança desta etapa — `MobileNav` reaproveita exatamente o par
`modalBackdrop`/spring `{ stiffness: 300, damping: 30 }` já usado por `FormDialog`.

### 1.9 Consistência visual

Auditoria não encontrou inconsistência real de radius/sombra/cor — esses já são
disciplinados pelos tokens do Design System em todo o projeto. O único ponto de
inconsistência corrigido foi estrutural: `hideOnMobile` declarado e usado por dois
domínios (Conta, Categoria) mas nunca aplicado pelo componente genérico (seção 1.2) — a
mesma correção resolve os dois de uma vez, por estar no componente compartilhado.

## 2. Validação

- `tsc -b`: limpo.
- `vite build` (via workaround de diretório temporário, `node_modules` montado não tem o
  binário nativo `@rollup/rollup-linux-x64-gnu`): 2481 módulos, bundle principal ~638 KB
  (aviso de tamanho de chunk pré-existente, não uma regressão desta etapa).
- `vite preview` local: servidor sobe e serve o HTML raiz corretamente (200).
- Instabilidade recorrente do mount FUSE (já documentada em etapas anteriores) voltou a
  ocorrer nesta etapa em praticamente todo arquivo tocado — mesma causa e mesma correção
  de sempre: `Read` como fonte da verdade, reescrita completa via heredoc, verificação de
  bytes/NUL. Um caso adicional apareceu pela primeira vez: uma reescrita via heredoc
  produziu um arquivo genuinamente truncado no disco (faltando as duas últimas linhas,
  `];` de fechamento) apesar do `wc -c` reportar o tamanho esperado logo em seguida —
  detectado pelo próximo `tsc -b` (`']' expected`), corrigido reabrindo o arquivo e
  reanexando o fechamento faltante, e revalidado byte a byte com Python antes de seguir.

## 3. Como validar visualmente no navegador

Com backend (`uvicorn app.main:app --reload`, dentro de `backend/`) e frontend (`npm run
dev`, dentro de `frontend/`) rodando ao mesmo tempo em dois terminais:

1. **Hierarquia de Categoria pai**: em `/categorias`, crie uma categoria (ex. "Moradia")
   e depois uma segunda com "Categoria pai" = Moradia (ex. "Aluguel"). Na tabela, "Aluguel"
   aparece logo abaixo de "Moradia", indentada, com um pequeno ícone de conector, e
   "Moradia" mostra "1 subcategoria" ao lado do nome.
2. **Navegação mobile**: reduza a janela do navegador (ou abra o DevTools em modo
   responsivo, `F12` → ícone de celular/tablet) para menos de 768px de largura. Um botão
   de menu (☰) aparece no canto superior esquerdo do `Header`; clicar nele abre um painel
   lateral com Dashboard/Contas/Categorias.
3. **`hideOnMobile` funcionando**: ainda em modo responsivo, abra `/contas` ou
   `/categorias` — os cards da lista não mostram mais "Instituição"/"Categoria pai" (só
   aparecem na tabela de telas largas).
4. **Busca sem flicker**: em `/contas` ou `/categorias` (telas largas, tabela real),
   digite algo rápido no campo de busca — a tabela não deve mais "piscar" (fade) a cada
   tecla, só quando a página/filtro/ordenação mudar de fato.
5. **Toggle "mostrar inativas" sem flash de skeleton**: desative uma categoria/conta e
   ligue/desligue o switch "Mostrar inativas" — a lista atual permanece visível até a nova
   chegar, em vez de mostrar um esqueleto cheio a cada clique.
6. **Toque em `RowActions` no mobile**: em modo responsivo, os botões de ação
   (Ver/Editar/Desativar) em cada card ficam visivelmente maiores do que antes.
