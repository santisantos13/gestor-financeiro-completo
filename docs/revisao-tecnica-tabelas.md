# Revisão técnica — Sistema de Tabelas (Etapa F4)

Revisão final da etapa, mesmo padrão de toda revisão técnica anterior do projeto
(backend, F1/F2/F3 do frontend). Escopo: infraestrutura reutilizável de tabelas para
todo o restante do projeto — nenhuma entidade real, nenhuma regra de negócio, nenhum
CRUD implementado ainda. Ver `docs/analise-arquitetural-frontend.md`, seção 13
(decisão de busca/filtro/ordenação/paginação 100% client-side, já aprovada antes desta
etapa começar).

## 1. O que foi entregue

**Tipos genéricos** (`types/table.ts`): `SortDirection`/`SortState`, `ColumnAlign`,
`ColumnDef<T>` (accessor/render/sortable/align/width/hideOnMobile), `FilterDef<T>`
(options + predicate), `RowAction<T>` (com `hidden?` por linha) e `BulkAction<T>` (com
`requireConfirmation?`, default `true` quando `tone: "danger"`). Nenhum tipo aqui
conhece uma entidade do backend — quem preenche esses genéricos é sempre quem consome
`DataTable`, numa etapa futura de CRUD.

**Motor de estado** (`hooks/useDataTable.ts`, ~215 linhas): `useDataTable<T>` centraliza
busca (via `useDeferredValue`, para não travar a digitação com milhares de linhas),
filtro, ordenação, paginação, visibilidade de coluna e seleção — um único hook, nenhum
componente visual guarda esse estado. Pipeline: `searched` (substring case-insensitive
em todos os `accessor`s visíveis) → `filtered` (aplica os `predicate`s ativos) →
`sorted` (comparação com nulls por último) → `paginatedRows` (fatiado pela página
atual).

**Dezenove componentes novos** em `components/ui/`: `Table`, `TableHeader`,
`TableBody`, `TableRow`, `TableCell` (renderiza `<th>` ou `<td>` por dois `return`
explícitos, para evitar o atrito de união de props JSX de um `Tag` dinâmico),
`SortHeader`, `SelectionCheckbox`, `TableSkeleton`, `LoadingTable`, `EmptyTable`,
`Pagination`, `SearchBar`, `FilterBar`, `ColumnVisibility`, `Toolbar`, `RowActions`,
`ConfirmAction` (modal genérico via `createPortal` — evita ser cortado pelo
`overflow-x-auto` da `Table`), `BulkActions`, e o orquestrador `DataTable`, que compõe
todos os outros e decide o que renderizar em cada estado (loading/erro/vazio/sucesso).

**Responsividade** (design-system.md, seção 24): `DataTable` renderiza um `<table>`
real em telas `md+` e uma lista de `Card`s com pares label/valor abaixo disso — nunca
scroll horizontal numa tabela densa. `RowActions` no mobile ficam sempre visíveis
(`opacity-100`), já que não há hover em touch.

**Motion** (motion-principles.md): o corpo da tabela (`motion.tbody`) faz um único
fade de conjunto (`opacity 0→1`, `DURATION.base`) a cada mudança de página, busca,
filtro ou ordenação — chave composta por esses quatro valores. Nenhum stagger por
linha, conforme a regra explícita do documento para listas densas revisitadas várias
vezes ao dia.

**Rota `/dev/tables`** (`pages/dev/DevTablesPage.tsx`): protegida, fora do `Sidebar`
(mesmo padrão de `/dev`). Dado 100% sintético gerado por um PRNG determinístico
(`pages/dev/fixtures/tableFixtures.ts`, mulberry32 com seed fixa — mesma massa de dado
a cada reload, sem `Math.random()` nem chamada de rede), 4.000 registros de um formato
inventado (`RegistroDemo`: nome/categoria/status/valor/data), nenhuma entidade real.
Demonstra: tabela vazia isolada, tabela carregando isolada, tabela em estado de erro
com retry (alternável por um botão de simulação), e a tabela completa com busca,
dois filtros (status e categoria), colunas ordenáveis, seleção, visibilidade de
coluna, ações por linha (Ver/Editar/Arquivar/Restaurar/Remover — as duas últimas
exercitando `hidden` condicional e tom `danger`), ações em lote (arquivar e remover
selecionados, a segunda exigindo confirmação via `ConfirmAction`), e um
`TableSkeleton` isolado fora do fluxo do `DataTable`. `/dev` (Etapa F3) ganhou uma
linha apontando para este novo laboratório.

## 2. Decisões tomadas sem pausar — e por quê

- **Formato do dado de demonstração.** A instrução era explícita ("Nenhuma regra de
  negócio. Nenhuma entidade específica. Tudo genérico.") mas exigia colunas de tipos
  variados para exercitar cada recurso pedido (busca em texto, filtro em enum,
  ordenação em número/data). `RegistroDemo` foi inventado só para isso — nome
  (texto), categoria (enum de 5 valores), status (enum de 3, com `Badge` colorido),
  valor (número, alinhado à direita, `formatMoney`) e data (`formatDate`). Nenhum
  campo tem significado financeiro real.
- **PRNG determinístico em vez de `Math.random()`.** Dado aleatório de verdade mudaria
  a cada reload da página, dificultando verificar visualmente "a paginação bate, a
  ordenação bate" de forma repetível. Um seed fixo resolve isso sem custo.
- **Estado de "arquivado" simulado em memória.** As ações "Arquivar"/"Restaurar" da
  demonstração precisavam de algum efeito visível para provar que `hidden` por linha e
  o fade de `motion.tbody` funcionam de verdade — um `Set<number>` local em
  `DevTablesPage` (não em `DataTable`) resolve isso sem inventar um "estado de
  domínio" que não existe.
- **`TableCell` com dois `return` em vez de um `Tag` dinâmico.** `<Tag {...props} />`
  com `Tag = header ? "th" : "td"` colide com a união de tipos de atributo JSX do
  TypeScript (`TdHTMLAttributes` vs. atributos de `<th>`); dois `return`s explícitos
  evitam a colisão sem precisar de `as any`.
- **Import não utilizado removido de `DataTable.tsx`.** A primeira versão importava
  `TableBody` mas nunca o usava (o corpo real é um `motion.tbody` direto, para poder
  aplicar a animação de fade); removido por limpeza assim que percebido — não mudou
  comportamento, `tsc -b` já passava mesmo com o import ocioso.

## 3. Validação realizada

- **`tsc -b`** (build incremental do projeto inteiro) — limpo, sem erros, verificado
  após cada lote de componentes novos e novamente no fechamento da etapa.
- **`vite build`** — limpo (`2420 módulos transformados`, bundle de produção gerado;
  mesmo aviso já conhecido de chunk >500KB da Etapa F3, agora ~532KB minificado —
  esperado, mais código no mesmo bundle ainda sem code-splitting, não um erro novo).
- **Consistência do mount**: dois arquivos (`AppRoutes.tsx`, `DevPage.tsx`) tiveram
  edições feitas via ferramenta de edição que o `bash`/`tsc` do lado do sandbox
  reportou como incompletas ou desatualizadas logo em seguida (erro de sintaxe JSX
  incoerente com o conteúdo real do arquivo, confirmado correto por leitura direta).
  Mesmo problema de instabilidade do mount já visto na Etapa F3 — corrigido reescrevendo
  os dois arquivos inteiros via heredoc no `bash`, com verificação de bytes/NUL, antes
  de rodar o `tsc -b` que finalmente ficou limpo.
- **Validação visual no navegador**: pendente de confirmação do usuário — recomendado
  `npm run dev:full` na raiz do projeto, abrir `http://localhost:5173/dev/tables` e
  exercitar busca, filtros, ordenação, paginação, seleção, ações por linha e em lote
  (incluindo o diálogo de confirmação). Esta revisão cobre tudo que é verificável sem
  olhos humanos (tipos, build); o critério de pronto pedido pelo usuário também exige
  essa confirmação visual antes de encerrar a etapa por completo.

## 4. Riscos conhecidos / dívida técnica sinalizada, não corrigida agora

- **Bundle de produção sem code-splitting** (~532KB minificado) — mesmo aviso já
  sinalizado na revisão da Etapa F3, cresceu junto com o sistema de tabelas. Ainda não
  urgente para um app de usuário único; candidato a `React.lazy` quando o app crescer
  mais.
- **Paginação/ordenação/filtro 100% client-side.** Decisão já aprovada em
  `docs/analise-arquitetural-frontend.md`, seção 13, antes desta etapa começar — o
  backend não expõe parâmetros de listagem para isso, e o `limit=100` default é
  suficiente para um usuário único. Se o volume real de dado crescer muito além disso
  no futuro, essa decisão precisará ser revisitada (mudaria contrato de API, fora do
  escopo desta etapa).
- **`ConfirmAction` não testado com leitor de tela real** — segue `role="alertdialog"`,
  foco inicial no botão Cancelar e restauração de foco ao fechar (mecânica copiada do
  `Select.tsx` já existente), mas validação de acessibilidade real (não só a mecânica
  de foco) ainda depende de teste manual com tecnologia assistiva, não feito nesta
  etapa.

## 5. Conclusão

Etapa F4 implementada seguindo `docs/analise-arquitetural-frontend.md` (seção 13) e
`docs/motion-principles.md`, sem nenhuma entidade real, regra de negócio ou alteração
de contrato de API — puramente infraestrutura de apresentação, pronta para ser
consumida por qualquer CRUD futuro sem refatoração (só preencher `ColumnDef`/
`FilterDef`/`RowAction`/`BulkAction`). Build e typecheck limpos. Falta apenas a
confirmação visual do usuário no navegador, em `/dev/tables`, para considerar a etapa
inteiramente encerrada.
