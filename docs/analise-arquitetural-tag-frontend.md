# Análise arquitetural — Tag (Etapa F8, frontend)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Mesma convenção
usada em todo o projeto: esta análise é lida e aprovada antes da primeira linha de código.
Escopo: CRUD completo de `Tag` no frontend (`/tags`), terceira entidade da sequência
F6-em-diante (Conta → Categoria → **Tag** → Cartão → ...), reaproveitando integralmente o
Design System (F2), o Sistema de Formulários (F5) e o Sistema de Tabelas (F4) já prontos —
e, desta vez, também o próprio `ColorField` (`ui/`) criado na F7 especificamente pensando
nesta etapa.

**Backend encerrado, mesmo princípio de sempre**: nenhum endpoint, contrato ou regra de
negócio é alterado por esta etapa. Tudo abaixo foi conferido por leitura direta do código
real (`app/models/tag.py`, `app/schemas/tag.py`, `app/services/tag_service.py`,
`app/repositories/tag_repository.py`, `app/api/routes/tag.py`), não de documentação.

## 0. Nenhuma decisão de infraestrutura pendente

Diferente da F7 (que precisou parar e perguntar sobre `IconField`/`ColorField`), `Tag` não
introduz nenhum campo sem precedente no Form System: `nome` é `TextField` puro, `cor` é
exatamente o mesmo `ColorField` já construído na F7 — mesmo regex de validação
(`_PADRAO_COR_HEX = ^#[0-9A-Fa-f]{6}$`, idêntico byte a byte ao de `Categoria`), sem
nenhum campo `icone` (o model `Tag` não tem essa coluna). A revisão técnica da F7 já
registrava essa previsão explicitamente: "os dois [`IconField`/`ColorField`] nascem em
`components/ui/`... porque Tag (próxima entidade da fila, também tem `cor`) reaproveita
`ColorField` sem nenhuma adaptação". Confirmado: zero mudança necessária em `ColorField`,
`lib/color.ts` ou qualquer outra peça compartilhada. Nada para pausar aqui.

## 1. Objetivo desta etapa

Construir `pages/tags/TagsPage.tsx` com CRUD completo (criar, listar, ver, editar,
desativar, reativar), consumindo `/tags/*` via a mesma camada de dados já estabelecida
para Conta/Categoria (`types/`, `schemas/`, `services/`, `hooks/useTagQueries.ts`).
Diferente das duas etapas anteriores, nenhum componente de campo novo é necessário — o
trabalho desta etapa é inteiramente composição de peças já existentes.

Fora de escopo (mesmo princípio de sempre): nenhuma regra de negócio nova, nenhuma
alteração de contrato, nenhum `TagSelect` (multi-seleção) — não existe nenhuma tela de
Transação ainda para consumi-lo de verdade (seção 4).

## 2. Contrato real do backend

### 2.1 Modelo

`Tag` é a entidade mais simples do CRUD até agora: sem hierarquia, sem conceito de "tag do
sistema" (toda tag pertence a um `usuario_id`, nunca `NULL` — diferente de `Categoria`),
sem `tipo`. Campos: `nome` (1-60, único por usuário via
`UniqueConstraint(usuario_id, nome)`), `cor` (hex `#RRGGBB`, opcional), `ativo` (soft
delete). `TagRead` não tem nenhum campo computado equivalente a `e_do_sistema` — é sempre
binário: a tag é do usuário logado, ou o backend devolve 404 (seção 2.2).

Não há `types/enums.ts` a estender: `Tag` não introduz nenhum enum novo.

### 2.2 Regras de negócio (todas no backend, nenhuma duplicada no frontend)

- **Posse**: `_buscar_da_propriedade_do_usuario` (`TagService`) — tag inexistente ou de
  outro usuário retorna 404 (`NotFoundError`), mesmo raciocínio anti-enumeração já usado em
  Conta/Categoria/Auth. Não há segunda camada de permissão (como o 403 de
  sistema-somente-leitura de Categoria) — `Tag` só tem essa única checagem.
- **Nome único por usuário** (`UniqueConstraint(usuario_id, nome)`, validado
  primeiro no Service via `buscar_por_nome`): colisão com uma tag **ativa** → `ConflictError`
  → HTTP 409. Este é o primeiro uso de 409 num CRUD de entidade neste projeto (as etapas
  anteriores, Conta e Categoria, não têm nenhuma restrição de unicidade de nome) — mas
  **não é infraestrutura nova para o frontend**: `ConflictError` → 409 já é tratado
  genericamente desde a Etapa F1 (`app/main.py`, `conflict_handler`; o mesmo código já
  aparece na F1 para e-mail duplicado em `RegistrarPage.tsx`, tratado ali só com
  `<ErrorMessage error={formError} />` — nenhum destaque de campo específico, porque o
  `detail` do backend é uma `string` solta, não um `ValidationErrorItem[]` com `loc`; ver
  seção 3). O mesmo padrão (`getErrorMessage` + `toast.error`) já cobre o caso de Tag sem
  nenhuma modificação.
- **Colisão com nome de tag desativada → reativação implícita, não erro** (`TagService.criar`):
  se o nome colide com uma tag do mesmo usuário que está **desativada**, o backend não
  cria uma linha nova nem rejeita — ele reativa a existente (`ativo = True`) e
  **sobrescreve `cor` com o valor enviado no payload** (documentado explicitamente no
  código do backend como decisão deliberada: semântica de criação, não de "restaurar como
  estava"). Do ponto de vista do frontend, isso é transparente: o formulário de criação
  chama `POST /tags` normalmente, recebe 201 com a `TagRead` (reativada), mostra o toast de
  sucesso padrão ("Tag \"X\" criada.") — nenhuma lógica condicional a escrever aqui, é só
  uma nuance de comportamento do backend que vale documentar para não ser motivo de
  confusão numa validação manual (uma tag "recriada" com o mesmo nome de uma apagada antes
  não é um bug se a cor mudar).
- **Update com colisão de nome** (`TagService.atualizar`): mesma checagem de unicidade, mas
  aqui SEM a reativação automática — se o novo nome colide com qualquer outra tag (ativa ou
  desativada) que não seja ela mesma, é 409 direto. Frontend não distingue os dois casos
  (criação vs. edição) na tratativa de erro — os dois já caem em
  `getErrorMessage`/`toast.error` da mesma forma.
- **Desativação sem checagem de uso** (`TagService.desativar`): diferente de Categoria (que
  bloqueia desativar um pai com subcategoria ativa), desativar uma Tag nunca falha por
  regra de negócio — o vínculo N-N com `Transacao` (tabela `transacao_tag`) não é afetado
  por soft delete; transações que já usam a tag continuam vinculadas, a tag só some das
  listas de novas seleções. Isso significa que o fluxo de "Desativar" em `TagsPage` nunca
  precisa lidar com um 422 de "em uso" — mais simples que Categoria, mais parecido com
  Conta (mas Conta também não tem essa checagem hoje, `TODO` conhecido de outras etapas).

### 2.3 Repository — uma busca específica

`listar_do_usuario(usuario_id, apenas_ativas, skip, limit)` — mesmo formato de
`ContaRepository`/`CategoriaRepository`, já coberto por `GET /tags?apenas_ativas`.
`buscar_por_nome(usuario_id, nome)` é uso interno do Service (unicidade + reativação),
nunca exposto por rota — o frontend não precisa (nem tem como) verificar
unicidade antes de submeter; deixa o 409 acontecer e mostra a mensagem pronta.

### 2.4 Router — mesmo formato de Conta/Categoria

`POST /tags`, `GET /tags?apenas_ativas&skip&limit`, `GET /tags/{id}`, `PATCH /tags/{id}`,
`DELETE /tags/{id}` → 204 (soft delete, nunca remove a linha). Nenhuma rota aceita
`usuario_id` do cliente.

## 3. Pré-requisitos confirmados (o que já existe, por leitura direta)

- **Camada de dados**: `httpClient`, `queryKeys`, `getErrorMessage`/`getFieldErrors`
  (`utils/errors.ts`) já tratam `ApiError` de qualquer status, incluindo 409 — confirmado
  lendo `types/api.ts` (`ApiError.detail: string | ValidationErrorItem[]`) e o uso real já
  existente em `RegistrarPage.tsx` para o 409 de e-mail duplicado. `hooks/useCategoriaQueries.ts`
  é o molde exato a replicar (mais simples até, porque `useTagQueries.ts` não precisa
  invalidar nada do Dashboard — mesma conclusão já vista em Categoria).
- **Form System (F5+F7)**: `TextField` cobre `nome`; `ColorField` (F7) cobre `cor` sem
  nenhuma adaptação; `SwitchField`/`RadioGroupField` não são necessários (não há campo
  `tipo` nem `icone` em Tag). Nenhum campo novo do Form System nesta etapa.
- **Sistema de Tabelas (F4)**: `DataTable` cobre listagem/busca/paginação; `ColumnDef.render`
  custom (já usado por `InstitutionBadge`/`CategoryBadge`) cobre o badge de cor da tag;
  `RowAction.hidden` cobre esconder "Desativar" quando `!ativo` e "Reativar" quando `ativo`
  — mesmo mecanismo já usado em Conta/Categoria, sem a complexidade extra de
  `e_do_sistema` (Tag não tem essa dimensão).
- **`ConfirmAction`**: mesmo componente de Conta/Categoria, para o fluxo de desativação.
- **Sistema de Toast**: `useToast()` já usado identicamente em `ContaFormDialog`/
  `CategoriaFormDialog` — nenhuma mudança.
- **`corDeContraste` (`lib/color.ts`)**: já extraída de `lib/institutions.ts` na F7
  exatamente prevendo este reaproveitamento ("compartilhada agora por `InstitutionBadge` e
  o novo `CategoryBadge`, sem duplicação") — `TagBadge` (seção 8) é o terceiro consumidor,
  zero mudança na função.
- **`TagsInput` (`components/ui/TagsInput.tsx`) NÃO é a mesma coisa que a entidade `Tag`**
  — vale registrar explicitamente para não confundir durante a implementação.
  `TagsInput` é um campo de formulário genérico de texto livre (`string[]`, sem busca,
  sem entidade por trás — usado por qualquer formulário futuro que precise de uma lista de
  palavras-chave digitadas à mão) já documentado desde a F5 como preparação para uma versão
  "inteligente" futura. Essa versão inteligente é exatamente o `TagSelect` previsto em
  `docs/analise-arquitetural-frontend.md` (seção 12) e `docs/design-system.md` (seção 15)
  — combobox de multi-seleção que busca as `Tag`s reais do usuário via React Query. Não
  nasce nesta etapa (seção 4), mas quando nascer, é provável que componha sobre
  `SearchSelect` (mesma base de `CategorySelect`) e não sobre `TagsInput`.

## 4. Tag ↔ outras entidades — hoje, só schema, nenhuma tela

`Transacao.tag_ids` (validado por `TransacaoService._validar_tags`: existência + posse,
sem checagem de `ativo` — uma transação antiga pode continuar referenciando uma tag
desativada, coerente com a regra de "soft delete não quebra vínculo existente" da seção
2.2) é a única relação de Tag com outra entidade. `Transacao` não tem CRUD no frontend
ainda (ordem: Conta → Categoria → **Tag** → Cartão → Fatura → Transação → ...). `TagSelect`
não é construído nesta etapa pelo mesmo motivo que `AccountSelect`/`CardSelect` não foram
construídos na F6/nesta etapa: são componentes previstos para quando a entidade que os
consome de verdade (Transação) for implementada — `CategorySelect` só foi uma exceção
porque a própria Categoria precisava dele para `categoria_pai_id` (autorreferência); Tag
não tem nenhum campo que referencie outra Tag, então não há justificativa para
antecipá-lo aqui.

## 5. Estrutura de arquivos novos

```
types/tag.ts                          # TagRead/TagCreate/TagUpdate
schemas/tag.ts                        # zod, formato/obrigatoriedade (não regra de negócio)
services/tagService.ts                # 1 função por endpoint, zero decisão
hooks/useTagQueries.ts                # useTags/useTag/useCriarTag/useAtualizarTag/useDesativarTag
components/domain/tag/TagBadge.tsx           # nome + cor, análogo a CategoryBadge (sem ícone)
components/domain/tag/tagTableColumns.tsx
components/domain/tag/TagFormDialog.tsx      # mesmo padrão de ContaFormDialog/CategoriaFormDialog
pages/tags/TagsPage.tsx
```

`api/queryKeys.ts` ganha a seção `tags` (mesmo formato de `categorias`); `routes/AppRoutes.tsx`
e `components/layout/Sidebar.tsx` (e `navItems.ts`, criado na etapa de Refinamento de UI)
ganham `/tags`, mesmo padrão de `/contas`/`/categorias`. `MobileNav` não precisa de nenhuma
mudança própria — ela lê de `navItems.ts`, então ganha o item automaticamente.

## 6. Camada de dados — mesmo molde de Categoria, mais simples

`schemas/tag.ts`: `nome` (`min(1).max(60)`) e `cor` (mesmo `.refine(eCorHexValida)` de
`schemas/categoria.ts`, reaproveitando a função — não duplicá-la). Sem `categoria_pai_id`,
sem `icone`, sem `tipo` — o schema de formulário de Tag é o mais curto de todos até agora,
só dois campos. `tagFormValuesParaPayload` segue o mesmo formato de
`categoriaFormValuesParaPayload` para `cor` (string vazia → `null`).

`hooks/useTagQueries.ts` invalida só `queryKeys.tags.all` — mesmo raciocínio de Categoria:
nenhum dos 11 endpoints de `/central-financeira/*` agrega Tag, e nenhum card/indicador do
Dashboard depende dela hoje.

## 7. Diferenças em relação a Categoria — por que esta etapa é mais simples

Categoria introduziu duas complexidades que Tag não tem:

- **Sem hierarquia**: nenhum `CategorySelect`-equivalente, nenhuma coluna "pai", nenhuma
  ordenação hierárquica (a correção feita na etapa de Refinamento de UI —
  `ordenarCategoriasPorHierarquia` — não se aplica aqui; a listagem de Tag é plana, ordenada
  por nome como já vem do backend, `order_by(Tag.nome)`).
- **Sem duas camadas de permissão**: nenhuma tag "do sistema", nenhum 403, nenhum
  `RowAction.hidden` condicionado a mais de um booleano. `TagFormDialog` não precisa da
  lógica extra que `CategoriaFormDialog` tem para forçar somente-leitura quando
  `e_do_sistema` — é uma versão mais enxuta de `ContaFormDialog` (que também não tem
  segunda camada de permissão).

O único conceito genuinamente novo em relação às duas etapas anteriores é o 409/reativação
implícita (seção 2.2), e mesmo esse já é coberto por infraestrutura existente desde a F1.

## 8. `TagBadge` — componente de domínio novo

Análogo a `CategoryBadge`, mas mais simples por não ter ícone. Onde `CategoryBadge`
renderiza um quadrado colorido (`rounded-md`) com um ícone dentro, `TagBadge` renderiza um
**pill** (`rounded-full`, coerente com a entrada "Badge/Tag" do Design System, seção 14:
"`--radius-full`, `--text-micro`") com o nome da tag dentro, fundo = `tag.cor` (ou
`--color-surface-3` se `cor` for `null`, mesmo fallback neutro de `CategoryBadge`/
`InstitutionBadge`) e texto = `corDeContraste(tag.cor)`. Não há resolvedor de ícone
(`resolveIconInfo`) a chamar — `cor` é o único campo visual da entidade.

```ts
interface TagBadgeProps {
  nome: string;
  cor: string | null;
  className?: string;
}
```

Usado em `tagTableColumns.tsx` (coluna "Nome") e no preview ao vivo de `TagFormDialog`
(mesmo padrão de `CategoriaPreview`/`InstituicaoPreview`: um subcomponente isolado com
`useWatch` escopado, para só ele re-renderizar a cada mudança de `nome`/`cor`).

## 9. Página `/tags` — UX completa

Estrutura idêntica a `ContasPage.tsx`/`CategoriasPage.tsx`: header com título/descrição +
botão "Nova tag", switch "Mostrar inativas", `DataTable` (busca, **sem filtro** — não há
campo enumerável em Tag que justifique um `FilterDef`, mesmo raciocínio que já conteve a
tentação de inventar filtro sem valor em `contaTableColumns.tsx`), `TagFormDialog`,
`ConfirmAction` de desativação. Estados de loading/erro/vazio são os mesmos do `DataTable`
(`LoadingTable`/`EmptyTable` internos) — nenhuma tela nova de estado a desenhar.
`emptyIcon` usa `Tag` (`lucide-react`) — mesmo ícone já usado como fallback neutro em
`lib/icons.ts` e como ícone de item do Sidebar/`MobileNav` para a própria rota `/tags`.

**Colunas** (`tagTableColumns.tsx`): só duas — "Nome" (`TagBadge`, `sortable`) e "Status"
(`Badge` ativo/inativa, `sortable`) — a tabela mais enxuta do projeto até agora, porque a
entidade só tem `nome`/`cor`/`ativo`. Nenhuma coluna precisa de `hideOnMobile`: com só duas
colunas, o card mobile já é naturalmente compacto (diferente de Conta/Categoria, que têm
3-4 colunas e precisam esconder uma no card).

## 10. Regras de negócio que o frontend explicitamente NÃO duplica

- Posse (404 anti-enumeração).
- Unicidade de nome por usuário, incluindo a reativação implícita ao colidir com uma tag
  desativada (409/comportamento de `criar`, seção 2.2) — o frontend nunca verifica
  unicidade antes de enviar, nunca decide se é criação ou reativação.
- Ausência de checagem de "em uso" na desativação — o frontend não verifica se alguma
  transação usa a tag antes de desativar (o backend não verifica, então o frontend também
  não simula essa checagem).

## 11. Motion aplicado — nada novo

`TagFormDialog` e `TagBadge` reaproveitam exatamente os padrões já estabelecidos: abertura/
fechamento de modal (`FormDialog`, `lib/motion.ts`), hover de tabela (`TableRow`), fade da
`motion.tbody` do `DataTable` (já corrigido na etapa de Refinamento de UI para não remontar
a cada tecla de busca — Tag herda essa correção de graça, por ser o mesmo componente).
Nenhum timing novo a desenhar.

## 12. Rota `/dev` — nenhuma atualização necessária

Diferente da F7 (que precisou de uma seção nova em `/dev/forms` para `IconField`/
`ColorField`, componentes genéricos sem entidade), Tag não introduz nenhum componente de
`ui/` novo — `TagBadge` é um componente de domínio (`components/domain/tag/`), e a
convenção já registrada na "Nota" de `/dev/forms`/`/dev` (a partir da F7) é que componentes
de domínio que buscam dado real via React Query são exercitados na própria página da
entidade, não duplicados com dado falso em `/dev`. `/tags` cumpre esse papel sozinha.

## 13. Fora de escopo desta etapa

Nenhuma tela de Transação (só ela consumiria `TagSelect` de fato). Nenhum `TagSelect`
multi-seleção. Nenhuma mudança em `ColorField`, `lib/color.ts`, `DataTable`, `FormDialog`,
ou qualquer outra infraestrutura compartilhada — esta etapa é 100% composição.

## 14. Critério de pronto

`tsc -b` e `vite build` limpos; `TagsPage` funcional (criar/ver/editar/desativar/reativar)
validado manualmente contra uma instância descartável do backend (mesmo protocolo de smoke
test usado nas Etapas F6/F7, incluindo o caso de criar uma tag com nome igual ao de uma
tag desativada — confirmando a reativação implícita com sobrescrita de `cor`, e o 409 puro
quando o nome colide com uma tag ativa); README e `docs/revisao-tecnica-tag-frontend.md`
atualizados ao final.

## 15. Próximos passos

1. `types/tag.ts`, `schemas/tag.ts`, `services/tagService.ts`, `queryKeys.tags`.
2. `hooks/useTagQueries.ts`.
3. `TagBadge`, `tagTableColumns.tsx`, `TagFormDialog.tsx`.
4. `TagsPage.tsx` + rota `/tags` + item em `navItems.ts` (Sidebar e MobileNav ganham o item
   automaticamente).
5. Validação final: smoke test real (incluindo o caso de reativação implícita), `tsc -b`,
   `vite build`, README, `docs/revisao-tecnica-tag-frontend.md`.

## 16. Revisão crítica de UX da entidade Tag

Análise prospectiva (a tela ainda não existe) sobre como o CRUD de Tag deve se comportar,
avaliando os mesmos pontos já pedidos para a revisão de UI anterior — para que a
implementação já nasça alinhada, em vez de precisar de outra rodada de refinamento depois.

**Fluxo de criação**: `TagFormDialog` em modo criação — `TextField` "Nome" (autofoco,
mesmo comportamento padrão de `FormDialog`) + `ColorField` "Cor" (opcional) + preview ao
vivo (`TagBadge`, seção 8). Único ponto de atenção real: se o usuário digitar um nome que
colide com uma tag desativada seguido, o resultado (sucesso, tag reativada com a cor nova)
é indistinguível na UI de uma criação "normal" — e é assim que deve ser (o backend já
decidiu que é semanticamente uma criação do ponto de vista do usuário). Nenhuma mensagem
especial é necessária para esse caso; inventar uma ("Tag reativada!" em vez de "Tag
criada!") exigiria o frontend saber algo que a API não expõe (a `TagRead` de retorno não
diz se foi um insert ou uma reativação) — não vale o custo.

**Edição**: mesmo padrão de `ContaFormDialog`/`CategoriaFormDialog` — um único dialog,
`somenteLeitura` alterna entre visualização e edição via botão "Editar". Sem a
complexidade extra de Categoria (nenhum campo fica travado por ser "do sistema").

**Exclusão (desativação)**: `ConfirmAction`, mesmo texto padrão adaptado ("Desativar
\"X\"?", descrição explicando que transações antigas mantêm o vínculo). Sem confirmação
extra por "em uso" (não existe essa checagem, seção 2.2) — mais direto que Categoria, onde
uma tentativa de desativar pode voltar com 422.

**Listagem, filtros e busca**: `DataTable` com `searchable` (busca por nome, client-side,
já genérico) e **sem** `FilterDef` — não haveria filtro com valor real (não há `tipo` nem
qualquer outro campo enumerável). O switch "Mostrar inativas" continua sendo o único
controle de escopo da lista, mesmo padrão de Conta/Categoria.

**Feedback visual**: toast de sucesso/erro em toda mutation (padrão já estabelecido),
`TagBadge` como preview ao vivo durante a digitação, `Badge` de status (ativa/inativa) na
tabela. Nenhum feedback novo a inventar.

**Hierarquia das informações**: como a entidade só tem `nome`/`cor`/`ativo`, não há
hierarquia de informação a desenhar (diferente de Categoria, que precisou da correção de
indentação/conector visual na etapa de Refinamento de UI). A tabela de duas colunas já é a
representação mais direta possível — adicionar qualquer coisa a mais (uma coluna de
"quantidade de transações", por exemplo) seria inventar funcionalidade fora do escopo desta
etapa (o backend não expõe essa contagem hoje).

**Estados vazios**: `EmptyTable`/`EmptyState`, mesmo componente, `emptyIcon={Tag}`. Ao
contrário de Categoria (onde o vazio é teoricamente impossível por causa das categorias de
sistema semeadas), o vazio de Tag é o estado real e esperado de um usuário novo — a
mensagem padrão ("Nenhuma tag ainda" / "Crie sua primeira tag...") é o primeiro contato
real desse componente com o caso que ele foi desenhado para cobrir.

**Animações**: nenhuma nova, tudo herdado (seção 11) — incluindo, de graça, a correção de
performance percebida da busca (fade da tabela não dispara mais a cada tecla).

**Consistência com `/categorias`**: estrutural (header, switch, `DataTable`, dialog,
`ConfirmAction`) é idêntica de propósito — é o padrão do projeto, não uma coincidência.
A única divergência visual esperada é a ausência da coluna "categoria pai"-equivalente e
do filtro por tipo, porque a entidade genuinamente não tem esses conceitos — não é
inconsistência, é a estrutura genérica se adaptando a uma entidade mais simples, exatamente
como projetada.

**Aproveitamento do espaço da tela**: com só duas colunas, a tabela em telas largas (`lg`+)
terá bastante espaço horizontal ocioso comparada a Conta (4 colunas) ou Categoria (4
colunas). Isso é aceitável e não deve ser "resolvido" inventando uma coluna sem dado real
por trás — é uma consequência honesta da entidade ser simples. Se no futuro a contagem de
transações por tag for exposta pelo backend (fora de escopo hoje), uma coluna "Uso" seria
um candidato natural para preencher esse espaço com informação real.

**Comportamento mobile**: card do `DataTable` já compacto por natureza (duas colunas);
nenhuma coluna precisa de `hideOnMobile`. Navegação mobile (`MobileNav`) ganha o item
"Tags" automaticamente por vir de `navItems.ts` — nenhum trabalho extra desta etapa.

**Performance e possíveis otimizações**: nenhuma otimização nova necessária — Tag herda
integralmente as correções já feitas na etapa de Refinamento de UI (`placeholderData:
keepPreviousData` deve ser replicado em `useTags`, mesmo raciocínio de `useContas`/
`useCategorias`, para o toggle "Mostrar inativas" não piscar skeleton; a correção da `key`
do `motion.tbody` já está no componente compartilhado, nada a fazer por entidade). Único
ponto a vigiar na implementação (não uma mudança de arquitetura, só atenção de
implementação): garantir que `useTagQueries.ts` inclua `placeholderData: keepPreviousData`
desde o primeiro commit, já que a Categoria/Conta só ganharam isso numa etapa de correção
posterior — não faz sentido introduzir a mesma lacuna de novo sabendo que ela já foi
identificada.
