# Análise arquitetural — Categoria (Etapa F7, frontend)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Mesma convenção
usada em todo o projeto (`docs/analise-arquitetural-dashboard.md`, `docs/analise-arquitetural-frontend.md`):
esta análise é lida e aprovada antes da primeira linha de código. Escopo: CRUD completo de
`Categoria` no frontend (`/categorias`), segunda entidade da sequência F6-em-diante (Conta →
**Categoria** → Tag → Cartão → ...), reaproveitando integralmente o Design System (F2), o
Sistema de Formulários (F5) e o Sistema de Tabelas (F4) já prontos.

**Backend encerrado, mesmo princípio de sempre**: nenhum endpoint, contrato ou regra de
negócio é alterado por esta etapa. Tudo abaixo foi conferido por leitura direta do código real
(`app/models/categoria.py`, `app/schemas/categoria.py`, `app/services/categoria_service.py`,
`app/repositories/categoria_repository.py`, `app/api/routes/categoria.py`), não de documentação.

## 0. Decisão tomada com o usuário antes de prosseguir

`Categoria` tem dois campos sem nenhum precedente no Form System atual: `cor` (hex opcional)
e `icone` (string livre até 40 caracteres, **sem nenhuma convenção imposta pelo backend** —
não há seed, não há pattern de validação além do tamanho). Nenhum dos catorze `*Field`
existentes (`TextField`/`SelectField`/`SearchSelect`/`TagsInput`/etc., seção 3 abaixo) cobre
"escolher uma cor" ou "escolher um ícone". Como o backend não define a convenção de `icone`,
essa é uma decisão que só o frontend pode tomar — parei e perguntei antes de escrever a
análise. Resposta registrada:

- **`icone` → `IconField` novo**, com um registry curado de nomes `lucide-react` (mesmo
  princípio de registry único já usado em `lib/institutions.ts` — "sem switch gigante
  espalhado pelo projeto"). O valor salvo é sempre o nome do ícone (string), nunca o
  componente. Ver seção 9.
- **`cor` → `ColorField` novo**, com swatch + input hex + paleta de sugestão alinhada aos
  tokens do Design System. Ver seção 9.

Os dois nascem em `components/ui/` (não em `components/domain/categoria/`) porque `Tag`
(próxima entidade da fila, também tem `cor`) reaproveita `ColorField` sem nenhuma adaptação —
mesmo raciocínio que já colocou `SearchSelect` em `ui/` na Etapa F5, prevendo os selects de
domínio futuros.

## 1. Objetivo desta etapa

Construir `pages/categorias/CategoriasPage.tsx` com CRUD completo (criar, listar, ver, editar,
desativar, reativar), consumindo `/categorias/*` via a mesma camada de dados já estabelecida
para Conta (`types/`, `schemas/`, `services/`, `hooks/useCategoriaQueries.ts`). Junto: os dois
componentes de campo novos (`IconField`, `ColorField`), o primeiro select de domínio real
(`CategorySelect`, já previsto desde a F1 em `docs/analise-arquitetural-frontend.md`, seção
12) e a extensão de `/dev`/`/dev/forms` para demonstrar as três peças novas.

Fora de escopo (mesmo princípio de sempre): nenhuma regra de negócio nova, nenhuma alteração
de contrato, nenhum uso de `CategorySelect` fora do laboratório `/dev` — não existe nenhuma
tela de Transação ainda para consumi-lo de verdade (seção 4).

## 2. Contrato real do backend

### 2.1 Modelo

`Categoria` é autorreferenciada (`categoria_pai_id → categorias.id`, `ondelete=CASCADE`) e tem
dois "donos" possíveis: `usuario_id IS NULL` = categoria do sistema (semeada, visível a todos,
somente leitura); `usuario_id = <id>` = categoria própria do usuário (edição livre). Campos:
`nome` (1-80), `tipo` (`TipoCategoria`, default `AMBOS`), `cor` (hex `#RRGGBB`, opcional),
`icone` (string ≤40, opcional, sem convenção — seção 0), `categoria_pai_id` (opcional),
`ativo` (soft delete). `CategoriaRead` expõe um campo computado, `e_do_sistema: bool`
(`usuario_id is None`) — é a única informação que o frontend precisa para decidir
somente-leitura, nunca comparando `usuario_id` contra o usuário logado manualmente.

```
export type TipoCategoria = "RECEITA" | "DESPESA" | "AMBOS";
```
(já existe em `types/enums.ts`, espelhado 1:1 do backend — nada a fazer aqui, só reusar.)

### 2.2 Regras de negócio (todas no backend, nenhuma duplicada no frontend)

- **Visibilidade** (`CategoriaRepository.listar_visiveis_do_usuario` / `CategoriaService._buscar_visivel`):
  sistema OU própria — nunca a privada de outro usuário. Categoria inexistente ou privada de
  outro usuário retorna 404 (`NotFoundError`) de propósito, anti-enumeração — mesmo padrão de
  Conta/Auth. O frontend nunca tenta adivinhar "esse ID é de outra pessoa"; só trata 404 como
  "não encontrada", igual a qualquer outra entidade.
- **Editabilidade ≠ visibilidade** — achado novo que Conta não tinha: uma categoria de sistema
  é *visível* (aparece na listagem, pode ser usada como `categoria_pai_id` ou em
  `Transacao.categoria_id` futuramente) mas **não é editável por ninguém**. `PATCH`/`DELETE`
  numa categoria de sistema levanta `AcessoNegadoError("Categorias do sistema são somente
  leitura.")` → HTTP 403 (`main.py`, `acesso_negado_handler`). É uma camada de permissão
  distinta de "não encontrada" (404) — o frontend precisa das duas: esconder as ações de
  editar/desativar quando `categoria.e_do_sistema` (UX proativa) *e* deixar o 403 genérico
  virar toast se o usuário chegar lá de outro jeito (defesa em profundidade, mesmo padrão do
  botão "Reativar" escondido quando `conta.ativo` já é `true`).
- **Hierarquia**: pai precisa existir e ser visível ao usuário (mesma regra de visibilidade
  acima); autorreferência rejeitada; ciclos detectados subindo a cadeia de ancestrais
  (`_cria_ciclo`) — todos `BusinessRuleError` → 422, mensagem pronta do backend. O frontend
  **não recalcula ciclo** — só filtra visualmente as opções óbvias do `CategorySelect` de pai
  (a própria categoria e seus descendentes diretos, calculado a partir da lista já carregada em
  memória) para não oferecer uma opção fadada a erro; qualquer ciclo mais indireto que passar
  disso é pego pelo backend e vira toast, exatamente como qualquer outro 422 do sistema.
- **Impedir desativação com subcategoria ativa** (`_impedir_desativacao_com_subcategoria_ativa`,
  compartilhado por `PATCH {ativo:false}` e `DELETE`): `BusinessRuleError` → 422. Frontend não
  verifica isso antes de chamar a API — deixa o backend decidir e mostra a mensagem pronta via
  `getErrorMessage`/toast, mesmo fluxo já usado em `ContasPage.confirmarDesativacao`.
- **`tipo` incompatível com o uso**: validado apenas quando algo referencia a categoria (ex.:
  `TransacaoService._validar_categoria`, fora do escopo desta etapa) — o CRUD de Categoria em
  si não tem essa checagem na criação/edição da categoria, só no momento de *uso*.

### 2.3 Repository — duas buscas específicas, sem equivalente em Conta

`listar_visiveis_do_usuario(usuario_id, apenas_ativas, skip, limit)` — mesmo formato de
`ContaRepository.listar_do_usuario`, nada novo para o frontend consumir (`GET /categorias`
já expõe isso via querystring `apenas_ativas`). `existe_subcategoria_ativa(categoria_id)` — uso
interno do `CategoriaService`, nunca exposto por rota; o frontend não tem (nem precisa ter)
acesso direto a essa informação antes de tentar desativar.

### 2.4 Router — mesmo formato de Conta

`POST /categorias`, `GET /categorias?apenas_ativas&skip&limit`, `GET /categorias/{id}`,
`PATCH /categorias/{id}`, `DELETE /categorias/{id}` → 204 (soft delete, nunca remove a linha —
igual Conta). Nenhuma rota aceita `usuario_id` do cliente.

## 3. Pré-requisitos confirmados (o que já existe, por leitura direta)

- **Camada de dados**: `httpClient`, `queryKeys`, `getErrorMessage`/`getFieldErrors`
  (`utils/errors.ts`) já tratam qualquer `ApiError` (403/404/409/422) de forma genérica —
  nada novo necessário para os dois códigos de erro exclusivos de Categoria (403 de
  sistema-somente-leitura, 422 de ciclo/subcategoria ativa). `hooks/useContaQueries.ts` é o
  molde exato a replicar (`useCategorias`/`useCategoria`/`useCriarCategoria`/
  `useAtualizarCategoria`/`useDesativarCategoria`).
- **Form System (F5)**: `Form`/`FormDialog`/`FormSection`/`TextField`/`SelectField`/
  `SearchSelect`/`RadioGroupField`/`SwitchField` cobrem `nome`, `tipo` e o toggle de
  ativo/inativo sem nada novo. Só `cor`/`icone` (seção 0) não têm campo pronto.
- **Sistema de Tabelas (F4)**: `DataTable` já suporta `ColumnDef.render` custom (usado por
  `InstitutionBadge`/`Badge` em `contaTableColumns.tsx`) e `ColumnDef.hideOnMobile` — cobre a
  coluna de "categoria pai" e o badge de cor/ícone sem nenhuma extensão do componente.
  `RowAction.hidden` (já usado para Desativar/Reativar em `ContasPage`) cobre esconder
  Editar/Desativar quando `e_do_sistema`.
- **`ConfirmAction`**: mesmo componente de Conta, para o fluxo de desativação.
- **`Badge`**: `tone="accent"` hoje é renderizado com a cor de acento do tema (seção 6.3 de
  `index.css`) — sem relação com a cor *própria* de uma categoria. O badge de categoria (nome +
  cor + ícone) é um componente de domínio novo (`CategoryBadge`, análogo a `InstitutionBadge`),
  não uma reutilização de `Badge`.
- **`lib/institutions.ts` como precedente direto**: a mesma forma (registry único, função
  resolvedora, `corDeContraste` para texto legível sobre a cor) é reaplicada para o registry de
  ícones (seção 9) — infraestrutura de "cor definida pelo usuário precisa de texto/ícone
  legível em cima" já resolvida uma vez, não reinventada.

## 4. Categoria ↔ outras entidades — hoje, só schema, nenhuma tela

`Transacao.categoria_id` (validado por `TransacaoService._validar_categoria`: visibilidade +
`ativo` + `tipo` compatível) e `categoria_id` também aparece nos contratos de `Financiamento`/
`Emprestimo` (`central_financeira_service.py`). Nenhuma dessas entidades tem CRUD no frontend
ainda (a ordem é Conta → Categoria → Tag → Cartão → Fatura → Transação → ...). `CategorySelect`
(seção 7) nasce agora porque é reutilizável e sem custo, mas só é *consumido de verdade* na
Etapa de Transação — aqui ele só aparece no laboratório `/dev/forms`, igual `SearchSelect` já
aparece hoje sem nenhuma entidade real por trás.

## 5. Estrutura de arquivos novos

```
types/categoria.ts                          # CategoriaRead/CategoriaCreate/CategoriaUpdate
schemas/categoria.ts                         # zod, formato/obrigatoriedade (não regra de negócio)
services/categoriaService.ts                 # 1 função por endpoint, zero decisão
hooks/useCategoriaQueries.ts                 # useCategorias/useCategoria/useCriar.../useAtualizar.../useDesativar...
lib/icons.ts                                 # registry curado de ícones (seção 9)
components/ui/IconField.tsx                  # novo campo do Form System
components/ui/ColorField.tsx                 # novo campo do Form System
components/domain/categoria/CategoryBadge.tsx        # nome + cor + ícone, análogo a InstitutionBadge
components/domain/categoria/CategorySelect.tsx       # select "inteligente", busca via useCategorias
components/domain/categoria/categoriaTableColumns.tsx
components/domain/categoria/CategoriaFormDialog.tsx  # mesmo padrão de ContaFormDialog (criar/ver/editar num só)
pages/categorias/CategoriasPage.tsx
```

`api/queryKeys.ts` ganha a seção `categorias` (mesmo formato de `contas`); `routes/AppRoutes.tsx`
e `components/layout/Sidebar.tsx` ganham `/categorias`, mesmo padrão de `/contas`.

## 6. Camada de dados — mesmo molde de Conta, duas diferenças

`schemas/categoria.ts` precisa de um único ajuste em relação a `schemas/conta.ts`: o campo
`categoria_pai_id` é `number | null` de verdade no formulário (não tem o problema de
`instituicao: string` que motivou a conversão manual em `contaFormValuesParaPayload` — um
`SearchSelect`/`CategorySelect` já lida nativamente com `null` via RHF, diferente de um
`<input>` de texto puro). `cor`/`icone` são opcionais, sem `.min()`.

`hooks/useCategoriaQueries.ts` invalida só `queryKeys.categorias.all` — diferente de
`useContaQueries.ts`, que também invalida três chaves do Dashboard porque `ContaCard`/
`saldoConsolidado`/`indicadores` dependem de Conta. Categoria não tem nenhum card ou indicador
próprio no Dashboard hoje (conferido em `docs/analise-arquitetural-dashboard.md`, seção 3 — os
11 endpoints de `/central-financeira/*` não incluem nenhum agregador de Categoria), então não
há nada adicional para invalidar.

## 7. Modelagem da hierarquia no frontend

Nenhum componente de árvore/tree é criado — decisão deliberada, não uma lacuna. `DataTable` é
inerentemente flat; construir um componente de árvore novo para uma hierarquia que hoje tem
profundidade tipicamente rasa (1-2 níveis, sem exemplo de uso real ainda) seria especulativo
demais para esta etapa. Duas peças resolvem a hierarquia sem um tree component:

- **Tabela**: coluna adicional "Categoria pai" (`hideOnMobile`, texto simples resolvido via
  lookup em memória na lista já carregada — sem chamada extra à API); ordenável por nome como
  qualquer outra coluna.
- **`CategorySelect`** (usado tanto no formulário de Categoria, para `categoria_pai_id`, quanto
  futuramente em Transação): opções com label prefixado pela cadeia de ancestrais (ex.:
  `"Moradia > Aluguel"`), calculado uma vez a partir da lista carregada — mesma técnica de
  `label` computado já usada em `DevFormsPage.tsx` (`Time de ${c.label}`). No formulário de
  edição, a própria categoria e todos os seus descendentes são excluídos das opções (seção
  2.2) — filtro client-side de UX, nunca a fonte de verdade da regra.

Se a hierarquia crescer para múltiplos níveis com uso real intenso (visualização em árvore
navegável, drag-and-drop de reordenação), isso é uma etapa própria, futura, e não bloqueia
este CRUD.

## 8. Permissões: sistema vs. próprias

`CategoriaFormDialog` (mesmo padrão de `ContaFormDialog`: um único componente para criar/ver/
editar via `somenteLeitura` + estado interno `editando`) recebe uma regra adicional:
`somenteLeitura` é forçado a `true` sempre que `categoria?.e_do_sistema`, independentemente do
modo com que o dialog foi aberto — impossível entrar em modo de edição numa categoria de
sistema pela UI, mesmo que o botão "Editar" de alguma forma apareça. Um aviso textual
("Categoria do sistema — somente leitura") substitui as ações de salvar quando esse for o
caso, mesmo lugar visual onde `ContaFormDialog` mostra o rodapé de ações.

Na tabela: `RowAction` "Editar" e "Desativar" ganham `hidden: (categoria) => categoria.e_do_sistema`
— única linha nova de lógica em `CategoriasPage.tsx`, mesmo mecanismo já usado para esconder
Reativar quando `ativo`. "Ver" continua sempre visível (sistema é visível, só não editável).

## 9. Componentes novos do Form System — `IconField` e `ColorField`

### 9.1 `lib/icons.ts` — registry curado

Mesmo formato de `lib/institutions.ts`: um array de `{ id: string, label: string, Icon:
LucideIcon }`, ~30 ícones cobrindo categorias financeiras comuns (moradia, transporte,
alimentação, saúde, lazer, educação, compras, assinaturas, viagem, presente, investimento,
etc. — curadoria final na implementação, não nesta análise). `resolveIcon(nome: string |
null | undefined): LucideIcon` faz o lookup por `id`; nome desconhecido ou ausente cai num
ícone neutro (`Tag`, do próprio `lucide-react`) — mesmo fallback neutro que `InstitutionBadge`
usa (`Landmark`) para instituição não reconhecida. **Nenhum switch/case** — um único objeto de
lookup, reaproveitável por qualquer campo `icone` futuro (Tag não tem `icone`, mas se alguma
entidade futura ganhar, o registry já está pronto).

### 9.2 `IconField`

Segue a mesma estrutura de qualquer outro `*Field` do Form System (`FormField` por baixo,
`Controller` do RHF, mesmo padrão de erro/label/description de `TextField`). Visualmente: um
botão que abre um popover com grid de ícones (mesma mecânica de popover client-side já usada
em `Select`/`SearchSelect` — clique fora fecha, Esc fecha, sem nova dependência). Salva o `id`
do ícone escolhido como string.

### 9.3 `ColorField`

Mesma estrutura de campo. Swatch quadrado (mostra a cor atual, ou neutro se vazio) + `<input>`
de texto para o hex + uma paleta pequena de sugestões (cores dos tokens `--color-chart-*` do
Design System, seção 6.6 de `index.css` — reaproveita paleta já existente em vez de inventar
uma nova). Validação de formato (`#RRGGBB`) fica no schema Zod do formulário, mesmo lugar onde
qualquer outra validação de formato já vive.

### 9.4 `CategoryBadge`

Componente de domínio (não do Form System) que combina `resolveIcon` + a cor salva da
categoria para renderizar um badge consistente em tabela e em qualquer preview futuro —
mesmo papel que `InstitutionBadge` cumpre para Conta. Usa `corDeContraste` (já existe em
`lib/institutions.ts`, mas é uma função pura sem nada específico de instituição — deveria na
implementação real ser movida para um lugar neutro como `lib/color.ts` e importada por ambos,
em vez de duplicada; sinalizado aqui para não esquecer no código).

## 10. Página `/categorias` — UX completa

Estrutura idêntica a `ContasPage.tsx`: header com título/descrição + botão "Nova categoria",
switch "Mostrar inativas", `DataTable` (busca, filtro por `tipo`, ações de linha condicionadas
a `e_do_sistema`/`ativo`), `CategoriaFormDialog`, `ConfirmAction` de desativação. Estados de
loading/erro/vazio são os mesmos do `DataTable` (`LoadingTable`/`EmptyTable` internos, já
usados por Conta) — nenhuma tela nova de estado a desenhar. `emptyIcon` usa `Tag`
(`lucide-react`), consistente com o ícone neutro de fallback da seção 9.1.

Diferença de Conta: como categorias de sistema sempre existem (semeadas), o estado vazio real
(zero categorias visíveis) é teoricamente impossível em produção — mas o componente continua
tratando isso graciosamente (mesma UX de qualquer `EmptyTable`), útil em ambiente de
desenvolvimento/teste sem seed.

Mobile: colunas `hideOnMobile` (Categoria pai, Tipo) seguem a mesma convenção já usada em
`contaTableColumns.tsx` para `instituicao`.

## 11. Regras de negócio que o frontend explicitamente NÃO duplica

- Visibilidade sistema-vs-próprio-vs-privado-de-outro (404 anti-enumeração).
- Editabilidade de categoria de sistema (403) — frontend só *antecipa* na UI, nunca decide.
- Detecção de ciclo na hierarquia — frontend só filtra opções óbvias, nunca recalcula a regra.
- Bloqueio de desativação com subcategoria ativa.
- Compatibilidade `categoria.tipo` × tipo de uso (fora de escopo: só importa quando outra
  entidade referencia a categoria, nenhuma delas tem CRUD ainda).

## 12. Motion aplicado — nada novo

`CategoriaFormDialog`, `IconField`/`ColorField` (popovers) e `CategoryBadge` reaproveitam
exatamente os padrões já estabelecidos: abertura/fechamento de modal e popover
(`motion-principles.md`, já usado por `FormDialog`/`Select`/`SearchSelect`), hover de tabela
(`TableRow`, Etapa de Refinamento Visual), sem nenhuma animação nova a desenhar.

## 13. Rota `/dev` — atualização

`/dev/forms` ganha uma seção demonstrando `IconField`/`ColorField`/`CategorySelect` isolados
(mesmo formato das seções existentes de `RadioGroupField`/`SearchSelect`) — o
`RadioGroupField` "Cor" hoje usado no diálogo de exemplo de `/dev/forms` (`{ value: "accent",
label: "Azul acinzentado (padrão)" }`, `"Verde"`, `"Âmbar"`) é um bom candidato a ser
substituído pelo `ColorField` de verdade nessa mesma seção, já que ele existia como um
placeholder até este ponto.

## 14. Fora de escopo desta etapa

Nenhuma tela de Transação (só ela consome `CategorySelect` de fato). Nenhuma visualização em
árvore navegável da hierarquia. Nenhum limite de profundidade de hierarquia imposto pelo
frontend (o backend não impõe nenhum — só rejeita ciclo). Nenhuma migração do `RadioGroupField`
de cor genérico usado em outros laboratórios `/dev` que não o de Categoria.

## 15. Critério de pronto

`tsc -b` e `vite build` limpos; `CategoriasPage` funcional (criar/ver/editar/desativar/
reativar) validado manualmente contra uma instância descartável do backend (mesmo protocolo de
smoke test usado na Etapa F6); `IconField`/`ColorField` cobrem os dois campos sem convenção
prévia do backend; ações de sistema escondidas corretamente na UI; README e
`docs/revisao-tecnica-categoria-frontend.md` atualizados ao final.

## 16. Próximos passos

1. `types/categoria.ts`, `schemas/categoria.ts`, `services/categoriaService.ts`, `queryKeys.categorias`.
2. `hooks/useCategoriaQueries.ts`.
3. `lib/icons.ts` + `IconField` + `ColorField` (componentes de `ui/`, sem dependência de Categoria).
4. `CategoryBadge`, `CategorySelect`, `categoriaTableColumns.tsx`, `CategoriaFormDialog`.
5. `CategoriasPage.tsx` + rota `/categorias` + item no Sidebar.
6. Seções novas em `/dev/forms`.
7. Validação final: smoke test real, `tsc -b`, `vite build`, README, `docs/revisao-tecnica-categoria-frontend.md`.
