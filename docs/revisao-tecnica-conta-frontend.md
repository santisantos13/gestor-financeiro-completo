# Revisão técnica — CRUD de Conta no frontend (Etapa F6)

Revisão final da etapa, mesmo padrão de toda revisão técnica anterior do projeto
(backend, F1-F5 do frontend). Escopo: primeira entidade real com CRUD completo no
frontend, compondo integralmente o Sistema de Tabelas (F4) e o Sistema de Formulários
(F5) — nenhum componente novo de infraestrutura, nenhuma alteração de backend, nenhuma
regra de negócio replicada no cliente.

## 0. Documentação de referência ausente

O pedido explícito era reler `docs/analise-arquitetural-conta.md` e
`docs/revisao-tecnica-conta.md` antes de começar. Nenhum dos dois existe: Conta foi a
primeira entidade implementada no backend, antes da convenção de um par de docs por
entidade começar (o mesmo vale para Categoria, Tag, Cartão e Fatura — têm
`revisao-tecnica-*.md` mas não `analise-arquitetural-*.md`). Em vez de bloquear ou
inventar conteúdo para esses arquivos, o contrato real foi lido direto do código-fonte
do backend — a mesma prática já estabelecida no projeto de tratar o backend como fonte
de verdade acima de qualquer doc:

- `app/models/conta.py` — `TipoConta` (`CORRENTE`/`POUPANCA`/`CARTEIRA`/`INVESTIMENTO`),
  `saldo_inicial` como coluna, `saldo_atual` **não é coluna**.
- `app/schemas/conta.py` — `ContaCreate` (`nome` 1-120, `tipo` default `CORRENTE`,
  `saldo_inicial` default 0, `instituicao` opcional ≤120), `ContaUpdate` (tudo
  `Optional`), `ContaRead` (inclui `saldo_atual` e `ativo`).
- `app/api/routes/conta.py` — `POST/GET/GET{id}/PATCH/DELETE /contas`, `GET` aceita
  `apenas_ativas` (default `true`).
- `app/services/conta_service.py` — `_com_saldo()` calcula `saldo_atual` a cada leitura
  (soma de `Transacao`/`Transferencia` ligadas à conta, nunca armazenado);
  `_buscar_da_propriedade_do_usuario()` devolve o mesmo `NotFoundError` para "não existe"
  e "pertence a outro usuário" (mitigação BOLA, mesmo padrão de `AuthService`).

Conclusão relevante para o frontend: `DELETE /contas/{id}` é sempre soft delete
(`ativo = False`, nunca remove a linha, preserva histórico de `Transacao`) e não existe
endpoint de "reativar" — é o mesmo `PATCH` usado para qualquer outro campo, com
`{"ativo": true}`.

## 1. O que foi entregue

**Camada de dados** (`types/conta.ts`, `schemas/conta.ts`, `services/contaService.ts`,
`api/queryKeys.ts`, `hooks/useContaQueries.ts`): espelham 1:1 o contrato lido acima.
`ContaRead` foi extraído para `types/conta.ts` e `types/centralFinanceira.ts` passou a
reexportá-lo em vez de manter uma definição duplicada — fechando uma dívida técnica já
sinalizada na revisão da F3 (`docs/revisao-tecnica-dashboard.md`, seção 5). Cinco hooks
React Query (`useContas`, `useConta`, `useCriarConta`, `useAtualizarConta`,
`useDesativarConta`); toda mutation invalida `queryKeys.contas.all` mais só as três
chaves do Dashboard que realmente dependem de Conta (`dashboard.contas`,
`dashboard.saldoConsolidado`, `dashboard.indicadores`) — nunca um prefixo `dashboard`
inteiro, para não causar refetch de seções que não mudaram.

**Componentes de domínio** (`components/domain/conta/`): `contaTableColumns.tsx` define
as colunas (nome, tipo com label traduzido, instituição, saldo atual alinhado à
direita/`formatMoney`, status via `Badge`) e um filtro por tipo, consumidos pelo
`DataTable` genérico da F4 sem nenhuma modificação nele. `ContaFormDialog.tsx` é um
único `FormDialog` (F5) que serve os três modos — criar, editar e visualizar — em vez de
três componentes separados: em modo leitura todo `*Field` recebe `disabled` (já suportado
nativamente por `TextField`/`SelectField`/`CurrencyField` desde a F5) e o rodapé troca
"Salvar alterações"/"Criar conta" por um botão "Editar" que alterna o modo sem fechar o
modal.

**Página `/contas`** (`pages/contas/ContasPage.tsx`): compõe `DataTable` +
`ContaFormDialog` + `ConfirmAction` (este último reaproveitado da F4 tal como está, sem
alteração) — nenhum componente de layout novo. Um `Switch` "Mostrar contas inativas"
alterna o parâmetro `apenas_ativas` da listagem. Ações por linha: Ver, Editar,
Desativar (com `ConfirmAction`, tom `danger`, oculta se já inativa) e Reativar (`PATCH
{ativo: true}`, oculta se já ativa).

**Navegação**: rota `/contas` adicionada a `AppRoutes.tsx` e item "Contas" adicionado ao
`Sidebar` — primeira entrada de navegação real além do Dashboard (`NAV_ITEMS` cresce de
um para dois itens). `/dev` ganhou uma nota explicando por que `components/domain/conta/`
não é duplicado lá com dado falso (mesmo raciocínio já usado para `domain/dashboard/`):
já é exercitado com dado real, contra o backend real, em `/contas`.

## 2. Decisões tomadas sem pausar — e por quê

- **`instituicao` como `string` (nunca `string | null`) no valor do formulário.** A
  primeira versão de `schemas/conta.ts` usava um `.transform()` do Zod para converter
  string vazia em `null` diretamente no schema, copiando o padrão já usado em
  `schemas/auth.ts`. Isso quebra: `useForm<ContaFormValues>` (`ContaFormValues` inferido
  via `z.infer`) passaria a ter `instituicao: string | null`, e como o campo é um
  `<input>` nativo controlado por `register()`, o React atribuiria `null` à propriedade
  `.value` do DOM — que o JavaScript coage silenciosamente para a string literal
  `"null"`, corrompendo a tela sem erro nenhum. Corrigido removendo o `.transform()` do
  schema (mantendo `instituicao: string` sempre no formulário) e criando
  `contaFormValuesParaPayload()`, que faz a conversão `""` → `null` só na hora de montar
  o payload da API, fora do sistema de tipos do formulário. Consequência: a asserção
  `satisfies z.ZodType<ContaCreate>` (usada com sucesso em `schemas/auth.ts`) foi
  removida daqui de propósito — o tipo do formulário e o tipo do payload da API agora
  divergem intencionalmente nesse único campo.
- **Um `ContaFormDialog` para criar/editar/visualizar em vez de três componentes.** A
  etapa pede explicitamente "visualizar conta" como funcionalidade própria, distinta de
  editar, mas o Design System só define dois tipos de modal (`FormDialog` e
  `DeleteDialog`/`ConfirmAction`) — nenhum "modal de detalhe" genérico. Criar um terceiro
  primitivo de modal só para exibição somaria uma peça de infraestrutura nova
  (duplicando toda a mecânica de portal/foco/scroll-lock/backdrop já implementada duas
  vezes) para um caso que o próprio `Form`/`*Field` já resolve com `disabled`. A
  alternativa escolhida — mesmo `FormDialog`, campos desabilitados, rodapé alternando
  "Editar"/"Salvar" — reaproveita 100% da infraestrutura da F5 sem inventar nada novo,
  em linha direta com a instrução "não criar componentes específicos sem necessidade".
- **`RowAction` sem confirmação embutida, ao contrário de `BulkAction`.** `types/table.ts`
  (F4) só dá `requireConfirmation`/`confirmTitle`/`confirmDescription` a `BulkAction`, não
  a `RowAction` — decisão já tomada e validada na F4, fora do escopo desta etapa alterar.
  A confirmação de "Desativar" foi então implementada na própria `ContasPage` (estado
  local `contaParaDesativar` + `ConfirmAction` renderizado ao lado do `DataTable`), sem
  tocar em `types/table.ts` nem em `RowActions.tsx`.
  - **Reativação sem confirmação.** Reverter `ativo` para `true` não é uma ação
  destrutiva (o histórico da conta nunca é perdido em nenhum dos dois sentidos) — pedir
  confirmação aqui seria atrito sem benefício, então o botão "Reativar" chama a mutation
  diretamente.
- **`emptyIcon` sem `emptyTitle`/`emptyDescription` customizados no `DataTable` de
  `/contas`.** `DataTable` (F4) usa o mesmo par título/descrição tanto para "nenhum dado
  ainda" quanto para "busca/filtro sem resultado" quando esses props são passados
  explicitamente — passá-los fixos faria uma busca sem resultado mostrar "nenhuma conta
  cadastrada ainda", que é enganoso. Optado por deixar o fallback genérico do próprio
  `DataTable` ("Nenhum registro ainda" / "Nada encontrado"), que já diferencia os dois
  casos corretamente, e customizar só o ícone (`Wallet`).

## 3. Validação realizada

- **`tsc -b`** — limpo, verificado após cada arquivo novo/editado e novamente no
  fechamento da etapa.
- **`vite build`** (via workaround de build fora do mount, `npm install` +
  `npm run build` em `/tmp/frontend-build-check`) — limpo, `2460` módulos transformados;
  mesmo aviso de chunk >500KB já conhecido das etapas anteriores (~590KB minificado
  agora), não é um erro novo desta etapa.
- **Smoke test real contra o backend**, exigido explicitamente pela etapa ("todo o fluxo
  funcionando de ponta a ponta utilizando o backend real"). Como este ambiente não tem
  acesso a um navegador para clicar na UI, a verificação foi feita no nível HTTP,
  reproduzindo exatamente as chamadas que `contaService.ts`/`ContaFormDialog.tsx` fazem,
  contra uma instância descartável do backend real (venv + `alembic upgrade head` numa
  cópia isolada do código-fonte, banco SQLite temporário — nunca o `financas.db` real do
  usuário): registro de usuário, login, `POST /contas` com instituição preenchida,
  `POST /contas` com instituição vazia (confere que o mapeamento `"" → null` do
  `contaFormValuesParaPayload` bate com o que a API aceita), `GET /contas` (listagem),
  `PATCH /contas/{id}` (edição parcial), `POST /contas` com `nome` vazio (confere que o
  formato do erro 422 bate com o que `getFieldErrors`/`form.setError` esperam),
  `DELETE /contas/{id}` (soft delete — `204`, conta some da listagem `apenas_ativas=true`
  mas continua em `apenas_ativas=false` com `ativo: false`), `PATCH {ativo: true}`
  (reativação) e `GET /central-financeira/contas` (o mesmo endpoint que `ContasCard` do
  Dashboard consome) antes/depois de cada mutação, confirmando que a agregação reflete
  a mudança. Todas as respostas bateram exatamente com os tipos de `types/conta.ts` e
  com o comportamento assumido por `useContaQueries.ts`.
- **Validação visual no navegador**: pendente de confirmação do usuário — este ambiente
  não tem acesso a um navegador conectado à instância real de desenvolvimento do
  usuário (`npm run dev:full` roda na máquina dele, não neste sandbox). Recomendado
  abrir `http://localhost:5173/contas` e exercitar criar, ver, editar, desativar,
  reativar, buscar, filtrar por tipo e conferir que o Dashboard (`/`) atualiza o saldo
  consolidado e os indicadores automaticamente após qualquer mutação.

## 4. Riscos conhecidos / dívida técnica sinalizada, não corrigida agora

- **Sem paginação real por parte do backend** — `GET /contas` não aceita `skip`/`limit`
  vindos da tabela (o backend tem esses parâmetros no schema mas o frontend não os usa
  ainda); a paginação vista em `/contas` é inteiramente client-side, sobre a lista
  completa retornada — aceitável para o volume de contas de um usuário único, mesma
  decisão já tomada e documentada na F4 (`docs/analise-arquitetural-frontend.md`, seção
  13).
- **Confirmação de "Desativar" implementada na página, não num componente
  reutilizável.** Se uma segunda entidade (Categoria, Cartão etc.) precisar do mesmo
  padrão "ação de linha destrutiva + `ConfirmAction`", vale considerar extrair um hook
  pequeno (`useConfirmRowAction` ou similar) em vez de repetir o mesmo par de
  `useState`/JSX em cada página — não extraído agora por não haver um segundo
  consumidor ainda (mesmo critério de "não abstrair sem dois casos reais" seguido em
  toda a F5).
- **Bundle de produção sem code-splitting** (~590KB minificado) — mesmo aviso crescente
  desde a F3, ainda não urgente para um app de usuário único.

## 5. Conclusão

Etapa F6 implementada seguindo `docs/analise-arquitetural-frontend.md`,
`docs/design-system.md` e `docs/motion-principles.md`, sem nenhuma alteração de backend
ou de contrato de API e sem nenhuma regra de negócio duplicada no cliente — o schema Zod
valida só formato/obrigatoriedade, e qualquer 422 real do backend é a fonte definitiva de
verdade, mapeada campo a campo na tela. Toda a interface foi construída compondo
integralmente os sistemas de Tabela (F4) e Formulário (F5): nenhum componente de
infraestrutura novo nasceu nesta etapa, só três arquivos de domínio
(`contaTableColumns.tsx`, `ContaFormDialog.tsx`, `ContasPage.tsx`) mais a camada de dados
correspondente. Build e typecheck limpos; smoke test HTTP direto contra uma instância
real e isolada do backend cobriu criar, listar, editar, validação de erro, desativar,
reativar e a atualização da agregação usada pelo Dashboard. Falta apenas a confirmação
visual do usuário no navegador, em `/contas`, para considerar a etapa inteiramente
encerrada.
