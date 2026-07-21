# Revisão técnica — CRUD de Categoria (Etapa F7, frontend)

Implementação completa a partir de `docs/analise-arquitetural-categoria-frontend.md`
(aprovada antes de qualquer código). Segunda entidade de CRUD real do frontend, depois de
Conta (F6) — mesmo nível de reaproveitamento de infraestrutura (Design System, Sistema de
Formulários, Sistema de Tabelas, React Query), com duas peças genuinamente novas que a
análise arquitetural já havia identificado e que o usuário decidiu antes da implementação
começar.

## 1. O que foi entregue

**Camada de dados** — mesmo molde de Conta: `types/categoria.ts` (`CategoriaRead`/
`CategoriaCreate`/`CategoriaUpdate`, espelhando `app/schemas/categoria.py` 1:1, incluindo
o campo computado `e_do_sistema`), `schemas/categoria.ts` (Zod de formato apenas;
`categoria_pai_id`/`cor`/`icone` ficam `string` no formulário — nunca `null` — convertidos
no payload por `categoriaFormValuesParaPayload`, mesmo raciocínio de `instituicao` em
`schemas/conta.ts`), `services/categoriaService.ts`, `queryKeys.categorias` e
`hooks/useCategoriaQueries.ts` (`useCategorias`/`useCategoria`/`useCriarCategoria`/
`useAtualizarCategoria`/`useDesativarCategoria`). Diferente de Conta, a invalidação toca
só `categorias.*` — nenhum endpoint de `/central-financeira/*` agrega Categoria hoje.

**Dois campos novos do Form System** (`components/ui/`, decisão tomada com o usuário antes
de escrever código — seção 2 abaixo): `IconField.tsx` e `ColorField.tsx`, mais
`lib/icons.ts` (registry curado de 32 ícones `lucide-react`) e `lib/color.ts` (extraído de
`lib/institutions.ts` — `corDeContraste` e a paleta de sugestão `PALETA_SUGESTAO` agora
vivem aqui, sem conhecimento de instituição nem de categoria).

**Componentes de domínio** (`components/domain/categoria/`): `CategoryBadge.tsx` (nome +
cor + ícone, análogo a `InstitutionBadge` mas sem resolvedor — `cor`/`icone` já são campos
estruturados da entidade, não texto livre a normalizar), `CategorySelect.tsx` (primeiro
select "inteligente" de domínio do projeto, previsto desde a Etapa F1 — busca via
`useCategorias`, rotula cada opção com a cadeia de ancestrais, exclui a própria categoria
e seus descendentes quando `excludeId` é passado), `categoriaTableColumns.tsx` (função
`buildCategoriaTableColumns(categorias)` — não um array estático como em Conta, porque a
coluna "Categoria pai" precisa de um `Map<id, nome>` fechado sobre a lista inteira já
carregada) e `CategoriaFormDialog.tsx` (mesmo padrão de `ContaFormDialog`: um único modal
para criar/ver/editar via `somenteLeitura` + estado `editando`, com a regra adicional de
forçar somente-leitura quando `categoria.e_do_sistema`).

**Página `/categorias`** (`pages/categorias/CategoriasPage.tsx`): mesma composição de
`ContasPage.tsx` — `DataTable` + `CategoriaFormDialog` + `ConfirmAction`, switch "mostrar
inativas", ações de linha condicionadas (`Editar`/`Desativar` escondidas para categoria de
sistema via `RowAction.hidden`). Rota adicionada a `AppRoutes.tsx` e item novo no
`Sidebar` (`Tag`, terceiro item).

**`/dev/forms`**: nova seção demonstrando `IconField`/`ColorField` dentro do exemplo de
`FormDialog` já existente (substituiu o `RadioGroupField` de cor que era um placeholder).
`CategorySelect` não ganhou seção em `/dev/forms` nem em `/dev` — decisão deliberada
(seção 3 abaixo).

## 2. Decisão tomada com o usuário antes de escrever código

A análise arquitetural identificou que `cor` (hex opcional) e `icone` (string livre até 40
caracteres, **sem nenhuma convenção imposta pelo backend** — sem seed, sem pattern) não
tinham nenhum campo equivalente no Form System (quatorze `*Field` existentes, nenhum de
seleção de cor ou ícone). Como a convenção de `icone` só poderia nascer no frontend, parei
e perguntei antes de prosseguir. Resposta: `IconField` com registry curado (não texto
livre, não emoji) e `ColorField` com swatch + hex + paleta — os dois como componentes
novos e genéricos do Form System, não específicos de Categoria, para a Tag (próxima
entidade da fila, também tem `cor`) reaproveitar sem alteração.

## 3. Decisões tomadas sem pausar (dentro do escopo já aprovado)

- **`categoria_pai_id` como `string` no formulário, não `number | null`.** A análise
  arquitetural original previa `number | null` diretamente; na implementação, ficou claro
  que isso quebraria `SearchSelect`/`CategorySelect` (que comparam `option.value === field.value`,
  ambos sempre `string`). Resolvido com o mesmo padrão já usado para `instituicao` em Conta:
  string vazia no formulário, convertida para `number | null` só no payload
  (`categoriaFormValuesParaPayload`). Não é uma divergência de arquitetura, é o mesmo
  princípio já aprovado (schema de formulário nunca carrega o tipo final da API) aplicado
  a um campo numérico em vez de string.
- **`CategorySelect` fora de `/dev`/`/dev/forms`.** A análise previa uma seção de
  demonstração para os três componentes novos (`IconField`/`ColorField`/`CategorySelect`).
  Na implementação, isso conflitava com uma convenção já estabelecida e documentada no
  próprio `/dev` (seção "Nota"): componentes de domínio que buscam dado real via React
  Query (como `ContaFormDialog`) não são duplicados com dado falso em `/dev` — são
  exercitados de verdade na própria página da entidade. `CategorySelect` é exatamente esse
  caso (chama `useCategorias`, que bate no backend de verdade), diferente de
  `IconField`/`ColorField` (`ui/`, sem conhecimento de nenhuma entidade, sem chamada à
  API) — esses dois ganharam a seção em `/dev/forms` como planejado; `CategorySelect` é
  exercitado em `/categorias`. Nota deixada tanto em `/dev/forms` quanto na "Nota" de
  `/dev` explicando a diferença.
- **`corDeContraste` movida para `lib/color.ts`.** A análise já sinalizava isso como
  pendência ("deveria na implementação real ser movida para um lugar neutro"). Feito:
  `lib/institutions.ts` agora importa e reexporta de `lib/color.ts` (zero breaking change
  para `InstitutionBadge`), `CategoryBadge` importa direto da nova fonte.

## 4. Validação realizada

- `tsc -b` limpo (múltiplas rodadas, incluindo depois de cada correção de instabilidade do
  mount FUSE — seção 5).
- `vite build` limpo via workaround de diretório temporário (`rsync` + `npm install` +
  `npm run build`, necessário porque `node_modules` montado não tem o binário nativo
  `@rollup/rollup-linux-x64-gnu`): 2479 módulos, bundle principal ~633 KB (aviso de
  tamanho de chunk pré-existente, não uma regressão desta etapa).
- **Smoke test real contra um backend descartável isolado** (SQLite temporário em
  `/tmp`, nunca o `financas.db` do usuário; `SECRET_KEY` só de teste; `alembic upgrade
  head` rodado do zero): registro de usuário, login, uma categoria de sistema inserida
  diretamente via SQL (`usuario_id = NULL`, já que não há seed de categorias de sistema no
  backend) para validar o caminho de somente-leitura, `PATCH` nela confirmando 403
  (`"Categorias do sistema são somente leitura."`), criação de categoria própria com
  `cor`/`icone`, criação de subcategoria (`categoria_pai_id`), tentativa de desativar o
  pai com subcategoria ativa confirmando 422, tentativa de autorreferência
  (`categoria_pai_id` apontando para si mesma) confirmando 422, desativação e reativação
  bem-sucedidas (`DELETE` → 204, `PATCH {ativo:true}` → 200), e o filtro `apenas_ativas`
  refletindo corretamente em ambos os casos. Todas as regras de negócio documentadas na
  análise arquitetural (seção 2.2) se comportaram exatamente como esperado — nenhuma
  surpresa, nenhum ajuste de contrato necessário.

## 5. Instabilidade recorrente do mount (FUSE) — mesma causa já documentada

Como em etapas anteriores, várias escritas via `Edit`/heredoc neste ciclo mostraram
conteúdo correto pela ferramenta `Read` mas byte count/erro `TS1127`/`TS17008` divergente
pelo lado do `bash` (`queryKeys.ts`, `Sidebar.tsx`, `institutions.ts`, `AppRoutes.tsx`,
`DevFormsPage.tsx`, `DevPage.tsx`). Mesma correção de sempre: reescrita completa via
heredoc + verificação de bytes/NUL, usando o conteúdo confirmado pelo `Read` como fonte da
verdade. Uma dessas reescritas reintroduziu por engano a versão arriscada do regex de
diacríticos (`/[̀-ͯ]/g`, caracteres Unicode literais em vez do escape `̀-ͯ`) em
`institutions.ts` — corrigida imediatamente via substituição de string direcionada (mesmo
incidente e mesma correção já registrados na revisão técnica da etapa de Refinamento
Visual, desta vez pego antes de prosseguir).

## 6. Riscos conhecidos / decisões deixadas em aberto

- **Nenhum seed de categorias de sistema existe no backend hoje.** O smoke test precisou
  inserir uma linha manualmente via SQL para exercitar o caminho de somente-leitura — em
  uso real, a lista de categorias visíveis para um usuário novo estará vazia até ele criar
  as próprias (ou até um seed ser adicionado ao backend, fora do escopo desta etapa).
  `EmptyTable`/`EmptyState` cobrem esse caso graciosamente.
- **`TODO(categoria-em-uso)` do backend continua em aberto** (não verifica se a categoria
  está referenciada por `Transacao`/`Financiamento`/etc. antes de desativar) — aceitável
  hoje porque nenhuma dessas entidades tem CRUD no frontend ainda; reavaliar quando
  Transação for implementada.
- **`icone` é uma convenção só do frontend.** Se outro cliente (ou uma segunda versão do
  frontend) escrever nesse campo sem seguir o registry de `lib/icons.ts`, o valor cai no
  fallback neutro (`Tag`) — comportamento tolerante por design, nunca quebra a
  renderização, mas vale ter em mente ao criar qualquer tooling adicional que grave
  `Categoria.icone`.

## 7. Conclusão

Etapa F7 concluída seguindo exatamente a análise arquitetural aprovada, com uma
formalização de tipo (`categoria_pai_id` como string) e uma decisão de escopo de
demonstração (`CategorySelect` fora de `/dev`) resolvidas durante a implementação por
aplicação direta de convenções já estabelecidas no projeto — nenhuma delas alterou
contrato, regra de negócio ou a decisão de `IconField`/`ColorField` combinada com o
usuário antes de começar. Validado ponta a ponta contra um backend real descartável, com
todas as regras de permissão e hierarquia se comportando como documentado.
