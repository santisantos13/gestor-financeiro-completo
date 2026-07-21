# Revisão técnica — CRUD de Tag (Etapa F8, frontend)

Implementação completa a partir de `docs/analise-arquitetural-tag-frontend.md` (aprovada
antes de qualquer código). Terceira entidade de CRUD real do frontend, depois de Conta
(F6) e Categoria (F7) — e a primeira etapa inteiramente de composição: nenhum componente
novo do Form System, nenhuma extensão de `DataTable`/`FormDialog`, nenhuma peça
compartilhada tocada.

## 1. O que foi entregue

**Camada de dados** — mesmo molde de Categoria/Conta: `types/tag.ts` (`TagRead`/
`TagCreate`/`TagUpdate`, espelhando `app/schemas/tag.py` 1:1 — sem nenhum campo computado
equivalente a `e_do_sistema`, toda Tag pertence a um usuário), `schemas/tag.ts` (Zod de
formato apenas — só `nome` e `cor`, o schema mais curto do projeto até agora),
`services/tagService.ts`, `queryKeys.tags` e `hooks/useTagQueries.ts`
(`useTags`/`useTag`/`useCriarTag`/`useAtualizarTag`/`useDesativarTag`). Invalidação toca
só `tags.*` — nenhum endpoint de `/central-financeira/*` agrega Tag.

**Componentes de domínio** (`components/domain/tag/`): `TagBadge.tsx` (nome + cor, análogo
a `CategoryBadge` mas **sem ícone** — o model `Tag` não tem essa coluna; onde
`CategoryBadge` é um quadrado com ícone dentro, `TagBadge` é um "pill" `rounded-full` com o
nome dentro, reaproveitando `corDeContraste` de `lib/color.ts` como terceiro consumidor,
depois de `InstitutionBadge` e `CategoryBadge`), `tagTableColumns.tsx` (duas colunas só —
"Nome" e "Status" — a tabela mais enxuta do projeto, decisão honesta e não uma lacuna:
Tag não tem `tipo` nem qualquer outro campo enumerável, então não há `FilterDef` nem coluna
extra a desenhar) e `TagFormDialog.tsx` (mesmo padrão de `ContaFormDialog`/
`CategoriaFormDialog`: um único modal para criar/ver/editar via `somenteLeitura` + estado
`editando` — mas sem a complexidade extra de Categoria, já que Tag não tem segunda camada
de permissão).

**Página `/tags`** (`pages/tags/TagsPage.tsx`): mesma composição de `ContasPage.tsx`/
`CategoriasPage.tsx` — `DataTable` + `TagFormDialog` + `ConfirmAction`, switch "mostrar
inativas", ações de linha `Ver`/`Editar`/`Desativar`/`Reativar` condicionadas só a `ativo`
(sem a condição extra de `e_do_sistema` que Categoria precisa). Rota adicionada a
`AppRoutes.tsx` e item novo em `components/layout/navItems.ts` (compartilhado por
`Sidebar` e `MobileNav` desde a etapa de Refinamento de UI — os dois ganharam o item
"Tags" automaticamente, nenhuma mudança própria em nenhum dos dois componentes).

## 2. Por que esta etapa não precisou de nenhuma decisão de infraestrutura

Diferente da F7 (que parou para decidir `IconField`/`ColorField` antes de escrever
qualquer código), a análise arquitetural desta etapa já havia confirmado, por leitura
direta do backend, que Tag não introduz nenhum campo sem precedente: `nome` é `TextField`
puro, `cor` é exatamente o `ColorField` construído na F7 — a própria revisão técnica da
F7 já registrava esse reaproveitamento como decisão deliberada ("Tag (próxima entidade da
fila, também tem `cor`) reaproveita `ColorField` sem nenhuma adaptação"). Confirmado na
prática: zero linha de `ColorField.tsx` ou `lib/color.ts` precisou mudar.

## 3. Achado de implementação: 409 (nome duplicado) já era coberto desde a F1

`TagService.criar`/`atualizar` usam `ConflictError` (→ HTTP 409) para nome duplicado —
primeiro uso desse status num CRUD de entidade (Conta e Categoria não têm restrição de
unicidade de nome). A análise já havia identificado que isso não era infraestrutura nova:
`ApiError`/`getErrorMessage`/`getFieldErrors` (`utils/errors.ts`) tratam qualquer status de
forma genérica desde a F1, e o próprio `RegistrarPage.tsx` já usa exatamente esse caminho
para o 409 de e-mail duplicado. Confirmado na implementação: `TagFormDialog.onSubmit`
segue o mesmo `try/catch` de `CategoriaFormDialog` (`getFieldErrors` + loop de
`form.setError` + `toast.error(getErrorMessage(error))`) sem nenhuma ramificação especial
para 409 — o `detail` do backend é uma string solta (não um `ValidationErrorItem[]` com
`loc`), então `getFieldErrors` devolve `null` e a mensagem vira toast, nunca um destaque de
campo. Validado via smoke test (seção 5).

## 4. Nuance de negócio documentada: reativação implícita ao criar

Se o nome digitado na criação colidir com uma tag **desativada** do mesmo usuário, o
backend reativa a existente (`ativo = true`) e **sobrescreve `cor`** com o valor enviado,
em vez de rejeitar ou criar uma linha nova. Do lado do frontend isso é inteiramente
transparente: `POST /tags` devolve 201 normalmente, o toast de sucesso é o mesmo ("Tag
\"X\" criada.") — nenhuma lógica condicional foi escrita para distinguir "criação de
verdade" de "reativação disfarçada de criação", porque a própria API não expõe essa
distinção e o backend já documenta essa como uma decisão semântica deliberada. Se colidir
com uma tag **ativa**, é 409 puro (seção 3).

## 5. Validação realizada

- `tsc -b` limpo (após duas rodadas de correção da instabilidade do mount FUSE — seção 6).
- `vite build` limpo via workaround de diretório temporário: 2488 módulos, bundle
  principal ~644 KB (mesmo aviso de tamanho de chunk pré-existente, não uma regressão desta
  etapa).
- **Smoke test real contra um backend descartável isolado** (SQLite temporário em `/tmp`,
  nunca o `financas.db` do usuário; `SECRET_KEY` só de teste; `alembic upgrade head` rodado
  do zero): registro de usuário, login, criação de tag "viagem" com cor, tentativa de criar
  outra tag "viagem" (409 confirmado, `"Já existe uma tag com este nome."`), desativação
  (`DELETE` → 204), listagem com `apenas_ativas=true` refletindo a ausência da tag
  desativada e `apenas_ativas=false` mostrando-a, criação de uma tag "viagem" nova
  (reativação implícita confirmada: mesmo `id`, `ativo: true`, `cor` sobrescrita com o
  valor novo — seção 4), nova desativação seguida de reativação explícita via `PATCH
  {ativo: true}` (confirmado preservando a `cor` da reativação anterior, diferente da
  reativação implícita via `POST`). Todas as regras de negócio documentadas na análise
  arquitetural se comportaram exatamente como esperado.

## 6. Instabilidade recorrente do mount (FUSE) — mesma causa já documentada

Como em todas as etapas anteriores, escritas via `Edit`/`Write` neste ciclo mostraram
conteúdo correto pela ferramenta `Read` mas erro de sintaxe (`TS1010`, `TS17008`, `TS1005`)
pelo lado do `bash` em `api/queryKeys.ts`, `components/layout/navItems.ts` e
`routes/AppRoutes.tsx`. Mesma correção de sempre: reescrita completa via heredoc +
verificação de bytes/NUL, usando o conteúdo confirmado pelo `Read` como fonte da verdade —
`tsc -b` limpo na rodada seguinte. Os arquivos novos desta etapa (`types/tag.ts` até
`TagsPage.tsx`) não precisaram dessa correção, só os arquivos compartilhados que já
existiam e foram editados.

## 7. Riscos conhecidos / decisões deixadas em aberto

- **`TagSelect` (multi-seleção) não foi construído** — mesma decisão já tomada para
  `AccountSelect`/`CardSelect` na F6: só nasce quando a entidade que o consome de verdade
  (Transação, via `tag_ids`) for implementada. `CategorySelect` foi uma exceção porque a
  própria Categoria precisava dele (`categoria_pai_id`, autorreferência) — Tag não tem
  nenhum campo equivalente.
- **Nenhuma contagem de "uso" por tag é exibida** — o backend não expõe quantas transações
  usam cada tag hoje; se isso mudar no futuro, uma coluna "Uso" seria um candidato natural
  para ocupar o espaço horizontal ocioso da tabela de duas colunas (identificado na revisão
  de UX da análise arquitetural, seção 16).
- **Ícone do item de navegação**: `Tags` (plural) foi escolhido deliberadamente em vez de
  `Tag` (singular) para não colidir visualmente com o item "Categorias", que já usa `Tag`
  como ícone (e também como fallback neutro em `lib/icons.ts`) — pequeno desvio do que a
  análise arquitetural havia sugerido (`emptyIcon` também usa `Tags`, pelo mesmo motivo),
  documentado aqui por transparência.

## 8. Conclusão

Etapa F8 concluída seguindo exatamente a análise arquitetural aprovada, sem nenhuma
decisão de infraestrutura pendente e sem nenhuma pausa para pergunta — a entidade mais
simples do CRUD até agora resultou na implementação mais direta: zero componente novo do
Form System, um único componente de domínio novo (`TagBadge`), e reaproveitamento integral
de `DataTable`, `FormDialog`, `ConfirmAction`, Toast, `ColorField` e `corDeContraste`.
Validado ponta a ponta contra um backend real descartável, incluindo a nuance de
reativação implícita por colisão de nome, com todo o comportamento batendo exatamente com
o documentado na análise.
