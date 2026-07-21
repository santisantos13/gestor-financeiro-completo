# Análise arquitetural — Frontend

Análise completa antes de qualquer código, mesmo rigor das análises do backend. **Backend
encerrado**: nenhum endpoint, contrato ou regra de negócio é alterado por esta etapa — o
frontend consome a API exatamente como ela existe hoje (785+ testes, 15 routers, ver
`README.md`).

**Revisão 2** deste documento — incorpora os ajustes aprovados pelo usuário sobre a proposta
original (React Query, React Hook Form + Zod, estrutura definitiva de `components/`, e um
roteiro que intercala infraestrutura visual/formulário/tabela antes das telas de negócio). A
Revisão 1 (histórico abaixo, seção 0, mantido) segue válida; esta revisão só substitui as
seções 2, 3, 5, 9, 10, 11, 12, 13 e 14.

## 0. Levantamento do estado atual (inalterado da Revisão 1)

`frontend/` era, até a Etapa F1 começar, só o scaffolding da Etapa 1 do projeto (React 18 +
TypeScript 5 + Vite 5 + Tailwind 3), sem roteamento, HTTP, estado ou formulário instalados.

Contratos relevantes confirmados por leitura direta do backend:

- **Auth não usa cookie.** `TokenResponse` (`access_token`, `refresh_token`,
  `token_type="bearer"`, `expira_em_segundos`) vem como corpo JSON — o frontend guarda e
  reenvia os tokens; não há sessão de servidor.
- **`TokenResponse` não inclui dados do usuário** — precisa de `GET /auth/me` separado
  (`UsuarioRead`: `id`, `nome`, `email`, `papel`, `ativo`, `criado_em`).
- **`POST /auth/registrar` não loga automaticamente** — só `UsuarioRead` (201), sem tokens.
- **Access token de 15 min, refresh token de 30 dias com rotation** (cada uso de
  `/auth/refresh` invalida o token usado e devolve um novo).
- **`/auth/logout` exige `refresh_token` no corpo**; `/auth/logout-todas` não precisa de corpo.
- **CORS já libera `http://localhost:5173`** por padrão — sem proxy necessário no Vite.
- **Sem variável de URL base no backend** — API sobe em `http://localhost:8000`; frontend
  precisa da própria `VITE_API_URL`.
- **422 tem DUAS formas de `detail`, mesmo status.** Handlers do projeto
  (`BusinessRuleError`/`ConflictError`/etc., em `app/main.py`) devolvem `{"detail":
  "<string>"}`; erro de validação de schema Pydantic (handler *padrão* do FastAPI) devolve
  `{"detail": [{"loc": [...], "msg": "...", "type": "..."}, ...]}` — uma lista. O cliente
  HTTP normaliza isso num só lugar.
- **Todo valor monetário/decimal chega como string** (`"1234.56"`) — nunca `number`, nunca
  recalculado no frontend.
- **Enums são strings** — valores exatos espelhados 1:1 em TypeScript.
- **`Alerta` não tem router nem schema no backend ainda** — sem tela até o backend
  implementar essa entidade.

## 1. Princípio geral: duas camadas reais (inalterado)

O frontend não tem regra de negócio — toda validação/cálculo/agregação já aconteceu no
backend. Duas camadas reais continuam valendo:

1. **Acesso a dado** (`api/` + `services/` + `types/` + `schemas/`) — sabe *como* falar com a
   API e *o formato* esperado. Zero decisão de UI, zero regra de negócio.
2. **Apresentação** (`hooks/` + `components/` + `pages/` + `layouts/`) — sabe *o que mostrar
   e quando*. Consome a camada 1.

O que muda nesta revisão é **quem implementa a mecânica de estado dentro da camada de
apresentação**: em vez de hooks genéricos escritos à mão (`useApiResource`/`useApiMutation`
da Revisão 1), essa responsabilidade passa para **React Query** — mas o princípio (nenhum
`service`/`component` de UI decide regra de negócio) não muda em nada.

## 2. Stack e dependências (revisado)

| Pacote | Categoria | Motivo |
|---|---|---|
| `react-router-dom` | roteamento | exigido pelo usuário |
| `@tanstack/react-query` | infraestrutura de comunicação com a API | cache, loading, refetch, invalidação, deduplicação — nenhuma página recria esse estado manualmente |
| `@tanstack/react-query-devtools` (dev only) | DX | inspeção de cache/queries em desenvolvimento, não entra no bundle de produção |
| `react-hook-form` | formulários | dezenas de formulários no sistema (13+ entidades) — registro/estado de formulário sem código repetido |
| `zod` + `@hookform/resolvers` | validação de formato/obrigatoriedade no formulário | só UX (formato, campo obrigatório, min/max) — a regra de negócio continua 100% no backend; o schema Zod nunca reimplementa uma regra que já existe como `BusinessRuleError` |

`fetch` nativo continua sendo o transporte (sem axios — zero ganho real aqui, e
`@tanstack/react-query` já cobre a parte que mais justificaria uma lib de HTTP mais
sofisticada). Sem Redux/Zustand/Context para dado de entidade — React Query é a única
infraestrutura de estado de servidor do projeto.

**Divisão de responsabilidade entre as duas bibliotecas, para não haver zona cinzenta:**
React Query cuida de tudo que é *dado vindo do servidor* (leitura e escrita via API). React
Hook Form cuida de tudo que é *estado local de um formulário antes do submit* (o que o
usuário está digitando, quais campos têm erro de formato). O ponto de contato entre os dois
é sempre o mesmo: `onSubmit` do formulário (RHF, já validado pelo Zod) chama uma mutation do
React Query, que fala com a API e invalida as queries afetadas.

## 3. Estrutura de pastas (revisado)

```
frontend/src/
├── main.tsx
├── App.tsx                        # QueryClientProvider > AuthProvider > ToastProvider > BrowserRouter > AppRoutes
├── index.css
├── api/
│   ├── httpClient.ts              # fetch + URL base + headers + refresh-on-401 (mutex) + normalização de erro
│   ├── tokenStore.ts              # getAccessToken/setAccessToken - módulo não-React, única ponte para o AuthContext
│   └── queryKeys.ts               # todas as chaves de query centralizadas (evita string solta/typo em invalidação)
├── types/                         # espelham Read/Create/Update do backend 1:1
│   ├── api.ts
│   ├── enums.ts
│   ├── auth.ts
│   └── <entidade>.ts              # criado na etapa daquela entidade
├── schemas/                       # validação Zod de FORMATO/obrigatoriedade (não regra de negócio)
│   ├── auth.ts
│   └── <entidade>.ts              # criado na etapa daquela entidade
├── services/                      # 1 arquivo por entidade - só chamadas tipadas à API
│   ├── authService.ts
│   └── <entidade>Service.ts
├── contexts/
│   ├── AuthContext.tsx            # usuário atual + status - por dentro, usa React Query
│   └── ToastContext.tsx           # notificações globais
├── hooks/
│   ├── useAuth.ts                 # atalho para AuthContext
│   ├── useToast.ts                # atalho para ToastContext
│   └── use<Entidade>Queries.ts    # wrappers de useQuery/useMutation por entidade, criado na etapa daquela entidade
├── components/
│   ├── ui/                        # genérico, sem noção de domínio nem de layout de página
│   ├── layout/                    # peças de layout reutilizáveis (Sidebar, Header, PageContainer) - usadas DENTRO de layouts/
│   └── domain/                    # componentes que conhecem uma entidade (ex. domain/conta/AccountSelect.tsx)
├── layouts/
│   ├── AppLayout.tsx              # casca de rota autenticada - compõe peças de components/layout/
│   └── AuthLayout.tsx             # casca de rota pública (login/registro)
├── pages/
│   ├── auth/{LoginPage,RegistrarPage}.tsx
│   └── <entidade>/...             # criada na etapa daquela entidade
├── routes/
│   ├── AppRoutes.tsx
│   └── ProtectedRoute.tsx
└── utils/
    ├── format.ts
    └── errors.ts
```

**Sobre `components/layout/` vs. `layouts/` (raiz de `src/`):** são coisas diferentes de
propósito. `layouts/` (topo) contém as duas cascas de rota inteiras (`AppLayout`,
`AuthLayout`), montadas diretamente pelo `react-router-dom`. `components/layout/` contém as
peças menores que uma casca compõe (barra lateral, cabeçalho, container de página) — a
distinção existe porque essas peças podem, no futuro, ser reaproveitadas fora de uma casca
de rota inteira (ex. um cabeçalho dentro de um modal). Nesta etapa (F1), `components/layout/`
começa vazio (pasta criada, sem conteúdo ainda) porque `AppLayout`/`AuthLayout` são simples o
bastante para não precisar quebrar em peças — quando o Design System (Etapa F2) desenhar a
navegação de verdade, as peças nascem lá.

**Sobre `components/domain/`:** é onde moram componentes que sabem o nome de uma entidade do
backend mas ainda são reutilizáveis entre páginas — o exemplo mais claro pedido pelo usuário
é os selects "inteligentes" da Etapa F3 (`CategorySelect`, `AccountSelect`, `CardSelect`,
`TagSelect`): cada um busca sua própria lista via React Query e se comporta como um `<select>`
comum por fora. Nesta etapa (F1), fica vazio (só a pasta) — não há componente de domínio
ainda, porque autenticação não é uma "entidade" no sentido do backend.

## 4. `api/httpClient.ts` (inalterado da Revisão 1)

Único módulo que sabe `fetch`/URL base/headers. Injeta `Authorization: Bearer <token>` lendo
de `tokenStore` (não de Context — `httpClient` é chamado de dentro de `queryFn`/`mutationFn`
do React Query, que roda fora da árvore de componentes). Normaliza toda resposta não-2xx num
`ApiError{status, detail: string | ValidationErrorItem[]}`. Renova automaticamente em 401 (com
mutex para não disparar múltiplos refreshes simultâneos) e repete a requisição original uma
vez; se o refresh também falhar, chama `onSessionExpired` (registrado pelo `AuthContext`).

## 5. `services/` e `schemas/` (revisado)

`services/` continua igual à Revisão 1 (funções finas e tipadas, só chamam `httpClient`,
nenhuma decisão). O que muda é **quem as chama**: agora são sempre a `queryFn`/`mutationFn`
de um hook do React Query (seção 11), nunca chamadas direto de um componente.

`schemas/` é nova nesta revisão: um arquivo por entidade com o(s) schema(s) Zod usados pelo
`react-hook-form` daquela entidade (via `zodResolver`). Regra dura: um schema Zod só valida
**formato e obrigatoriedade** (`z.string().min(1)`, `z.number().positive()`,
`z.string().regex(...)` para um CPF, etc.) — nunca uma regra que dependa de estado do
servidor (ex. "categoria pertence ao usuário", "cartão está ativo") — essas continuam
existindo só como `BusinessRuleError` no backend, e o formulário simplesmente mostra o erro
422 que vier de lá. O tipo inferido pelo schema (`z.infer<typeof contaCreateSchema>`) é
conferido estruturalmente contra o `ContaCreate` de `types/conta.ts` — os dois não podem
divergir sem o TypeScript reclamar.

## 6. `types/` (inalterado da Revisão 1)

## 7. Fluxo de autenticação (revisado apenas na mecânica interna)

O fluxo em si (boot → login → registro-encadeia-login → logout → guarda de rota) continua
exatamente como a Revisão 1 descreveu. O que muda é a implementação dentro de
`AuthContext`:

- **Boot**: efeito único no mount lê `refresh_token` do `localStorage`; se existir, chama
  `authService.refresh()` imperativamente (não é uma "query" no sentido de dado
  re-buscável, é um passo de inicialização que roda uma vez) e grava o resultado em
  `tokenStore` + `localStorage`. Ao terminar (sucesso ou falha), marca `hasBootstrapped`.
- **Usuário atual**: `useQuery({ queryKey: queryKeys.auth.me, queryFn: authService.me, enabled: hasBootstrapped && tokenStore.getAccessToken() != null, retry: false })` — o próprio React Query cuida de loading/erro dessa consulta; `status` do contexto é derivado de `hasBootstrapped` + o estado da query (`loading` enquanto não bootou ou a query está carregando, `unauthenticated` se não há token ou a query falhou, `authenticated` se a query tem dado).
- **Login/Registro/Logout**: `useMutation` do React Query. `onSuccess` do login grava tokens
  em `tokenStore`/`localStorage` e invalida `queryKeys.auth.me` (React Query rebusca
  sozinho). `onSuccess`/sempre do logout limpa tokens e chama `queryClient.clear()` — não só
  a query de `me`, mas **todo** o cache: evita dado de um usuário vazar para a sessão do
  próximo login no mesmo navegador (ex. troca de usuário sem fechar a aba).
- **`onSessionExpired`** (chamado pelo `httpClient` quando o refresh em 401 falha): mesma
  limpeza do logout (tokens + `queryClient.clear()`), sem chamar o endpoint `/auth/logout`
  (a sessão já morreu no servidor).

## 8. Tratamento global de erros (inalterado da Revisão 1)

A tabela de status→tratamento da Revisão 1 continua valendo integralmente. O que muda é só o
canal: onde antes um hook manual guardava `error` em `useState`, agora é o `error` que o
próprio React Query expõe (`useQuery`/`useMutation`), já tipado como `ApiError`.

## 9. Loading e estado de servidor (revisado — React Query substitui os hooks genéricos)

Não existe mais `useApiResource`/`useApiMutation` escritos à mão. Em vez disso, cada
entidade ganha um `hooks/use<Entidade>Queries.ts` (a partir da Etapa daquela entidade) com
essa forma:

```ts
// hooks/useContaQueries.ts
export function useContasQuery(apenasAtivas = true) {
  return useQuery({
    queryKey: queryKeys.contas.list(apenasAtivas),
    queryFn: () => contaService.listar(apenasAtivas),
  });
}

export function useCriarContaMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: contaService.criar,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.contas.all }),
  });
}
```

Página consome assim, sem `useState` de loading/erro nenhum:

```ts
const { data: contas, isLoading, error, refetch } = useContasQuery();
const criarConta = useCriarContaMutation();
// criarConta.mutate(dados), criarConta.isPending, criarConta.error
```

Convenção de UI não muda da Revisão 1: `isLoading`/`isPending` → `Spinner`; `error` →
`ErrorMessage` com ação de retry (`refetch` para query, reenviar o formulário para mutation);
lista vazia sem erro → `EmptyState`. `queryKeys.ts` (seção 3) é o único lugar que escreve a
string da chave — hooks e invalidações sempre importam de lá, nunca escrevem `["contas"]`
literal inline.

**`staleTime`/retry padrão do `QueryClient`:** configurado uma vez em `App.tsx`. Erros 4xx
(o `ApiError.status` já vem tipado do `httpClient`) não são re-tentados automaticamente (não
adianta tentar de novo uma requisição malformada ou não autorizada) — só falha de rede/5xx
tenta novamente, no máximo uma vez. `staleTime` default de 30s (app de usuário único, sem
necessidade de tempo real; evita rebuscar a mesma lista repetidamente ao trocar de aba
rapidamente entre páginas).

## 10. Componentes: `ui/`, `layout/`, `domain/` (revisado)

Estrutura definitiva criada desde a Etapa F1 (pastas existem mesmo vazias), populada de
forma incremental:

- **`components/ui/`** — sem noção de domínio nem de layout de página inteira. Nesta etapa
  (F1): `Spinner`, `Button`, `Input` (o mínimo para as telas de login/registro existirem). A
  Etapa F2 (Design System) expande esse conjunto para o vocabulário completo do sistema —
  não antes, e só com o que for de fato usado (nenhum componente "especulativo").
- **`components/layout/`** — peças de casca reutilizáveis (ver seção 3). Vazio na F1.
- **`components/domain/`** — componentes cientes de uma entidade específica, mas ainda
  reutilizáveis entre páginas dessa entidade (ex. `CategorySelect`). Vazio na F1 (autenticação
  não é uma entidade de domínio no sentido do backend).

## 11. `hooks/` e `contexts/` (revisado)

- **`contexts/AuthContext.tsx`** — por dentro, usa `useQuery`/`useMutation` do React Query
  (seção 7) em vez de `useState` manual. Continua sendo o único escritor de `tokenStore`.
- **`contexts/ToastContext.tsx`** — inalterado (fila simples, sem lib externa).
- **`hooks/useAuth.ts`** / **`hooks/useToast.ts`** — inalterados, atalhos para os contexts.
- **`hooks/use<Entidade>Queries.ts`** — substitui o antigo hook genérico da Revisão 1; um
  arquivo por entidade, criado na etapa daquela entidade, sempre no formato da seção 9.

## 12. Sistema de formulários (novo — Etapa F3)

Camada reutilizável construída sobre React Hook Form + Zod + os primitivos do Design System
(F2). Todos vivem em `components/ui/` (são genéricos — não conhecem qual entidade os usa),
exceto os selects "inteligentes" que são `components/domain/` (buscam sua própria lista via
React Query):

| Componente | Pasta | Responsabilidade |
|---|---|---|
| `FormField` | `ui/` | label + slot de input + `ValidationMessage` — todo campo de formulário do sistema passa por aqui |
| `ValidationMessage` | `ui/` | mensagem de erro de um campo (RHF `formState.errors`) ou do formulário inteiro (422 do backend) |
| `MoneyInput` | `ui/` | campo RHF-integrado (via `Controller`) para os campos `Decimal`-como-string do backend (`valor`, `saldo_inicial`, etc.) — nunca converte para `number` internamente, só formata a exibição |
| `CurrencyInput` | `ui/` | o input de máscara monetária "puro" (sem RHF) que `MoneyInput` usa por baixo — existe separado porque é reutilizável fora de formulário (ex. um filtro de valor mínimo numa tabela, Etapa F4) |
| `DateInput` | `ui/` | campo RHF-integrado para os campos `date` do backend (ISO string) |
| `LoadingButton` | `ui/` | `Button` que mostra spinner e desabilita durante `mutation.isPending` |
| `FormDialog` | `ui/` | modal padrão para criar/editar (a maioria dos formulários do sistema abre num modal, não numa página cheia) |
| `DeleteDialog` | `ui/` | confirmação padrão de exclusão/cancelamento, usada por toda entidade com ação destrutiva |
| `CategorySelect` | `domain/categoria/` | select de categoria, busca via `useCategoriasQuery` |
| `AccountSelect` | `domain/conta/` | select de conta, busca via `useContasQuery` |
| `CardSelect` | `domain/cartao/` | select de cartão, busca via `useCartoesQuery` |
| `TagSelect` | `domain/tag/` | select de tag (multi-seleção), busca via `useTagsQuery` |

Cada entidade, a partir da F6, ganha seu formulário de Create/Update compondo essas peças +
seu próprio `schemas/<entidade>.ts` — sem reescrever `<input>`/`<label>`/mensagem de erro do
zero em cada tela.

## 13. Sistema de tabelas (novo — Etapa F4)

Infraestrutura reutilizável sobre `components/ui/`:

- **`DataTable`** — tabela genérica (colunas tipadas via generics, `data: T[]`), sem saber o
  que é uma "Conta" ou uma "Transação" — quem sabe são as definições de coluna passadas pela
  página/`components/domain`.
- **Filtros, paginação, ordenação** — **client-side**, sobre o array já carregado pela query.
  Decisão deliberada: o backend não expõe parâmetro de ordenação em nenhum endpoint de
  listagem, e o `limit` padrão (100) já cobre o volume realista de um usuário único — não há
  ganho em inventar paginação/ordenação server-side que o backend não suporta (mudaria
  contrato, fora de escopo). Se algum dia o volume de dados justificar o contrário, isso é
  uma decisão nova, não uma antecipação de agora.
- **`EmptyState`/`LoadingState`** — mesmos princípios da seção 9, mas como peças do
  `DataTable` (quando `data.length === 0` ou `isLoading`), reaproveitando `components/ui/EmptyState`
  e `components/ui/Spinner` já existentes desde a F1/F2 — não são componentes novos, são o
  `DataTable` sabendo usá-los.

## 14. Decisões explícitas (revisado)

As decisões "a" e "c" da Revisão 1 foram **revertidas** pelo feedback do usuário (agora HÁ
lib de formulário e HÁ cache/estado de servidor via React Query) — removidas desta lista. As
demais continuam valendo:

- **`refresh_token` em `localStorage`, `access_token` só em memória** (via `tokenStore`) —
  inalterado, mesmo trade-off já registrado (backend não expõe cookie `httpOnly`, fora de
  escopo mudar).
- **Registro encadeia login automaticamente** — inalterado, decisão de UX reversível.
- **`.env`/`VITE_API_URL`** novo no frontend — inalterado.
- **Nova (desta revisão): paginação/ordenação/filtro de tabela são client-side** — ver seção 13.
- **Nova (desta revisão): `MoneyInput` vs. `CurrencyInput` são componentes distintos** —
  `CurrencyInput` é o input de máscara puro (reutilizável fora de formulário),
  `MoneyInput` é o wrapper RHF (`Controller` + `FormField` + `CurrencyInput`) usado dentro de
  formulários. Interpretação minha da lista pedida pelo usuário (que listou os dois nomes
  sem detalhar a diferença) — sinalizado explicitamente para confirmação quando a Etapa F3
  começar; fácil de colapsar em um só componente se preferível.

## 15. Fora de escopo (revisado)

- Qualquer tela de CRUD de entidade — agora vem depois de F1→F2 (Design System)→F3
  (Formulários)→F4 (Tabelas)→F5 (Dashboard), não logo após F1.
- Tela de `Alerta` — backend ainda não implementou essa entidade.
- Dark mode, i18n, PWA/offline, CI — YAGNI até virar pedido real. **Atualização:** dark
  mode (com toggle claro/escuro) virou pedido real na Etapa de Refinamento Visual
  (pós-F6) e foi implementado — ver `docs/revisao-tecnica-branding-e-microinteracoes.md`.
  i18n/PWA/offline/CI continuam fora de escopo.
- ESLint/Prettier — mesma posição da Revisão 1, não bloqueia.
- **Testes automatizados de frontend** — mesma posição da Revisão 1 (fora de escopo por
  ora). Sinalizado aqui de novo porque o projeto tem uma regra geral de cobertura de teste
  completa em toda mudança (aplicada rigorosamente no backend); como a Revisão 1 já listava
  isso como fora de escopo e a aprovação do usuário não mencionou testes entre os ajustes,
  entendo que continua deferido — mas registro explicitamente para não passar despercebido,
  não por assumir silenciosamente.

## 16. Roteiro de implementação (revisado)

**F1 — Fundação** (em andamento): `react-router-dom` + `@tanstack/react-query` +
`react-hook-form`/`zod`/`@hookform/resolvers` instalados; `api/`, `types/{api,enums,auth}`,
`schemas/auth`, `services/authService`; `AuthContext`/`ToastContext` sobre React Query;
estrutura definitiva de `components/{ui,layout,domain}` criada (só `ui/` populada com o
mínimo: `Spinner`, `Button`, `Input`); `layouts/{AppLayout,AuthLayout}` mínimos;
`pages/auth/{LoginPage,RegistrarPage}` com RHF+Zod; `routes/{AppRoutes,ProtectedRoute}`; uma
página protegida placeholder (não é o Dashboard real ainda) só para provar o guard. Critério
de pronto: registrar, logar, F5 mantém sessão, logout, 401 simulado desloga.

**F2 — Design System**: infraestrutura visual reutilizável em `components/ui/` (o conjunto
completo realmente usado pelo sistema — Button, Input, Select, Modal, Spinner, ErrorMessage,
EmptyState, ConfirmDialog, Badge, Card, etc.) e as primeiras peças de `components/layout/`
(Sidebar, Header, PageContainer) para a navegação real do `AppLayout`. Sem tela de negócio
ainda.

**F3 — Sistema de formulários**: `FormField`, `ValidationMessage`, `MoneyInput`,
`CurrencyInput`, `DateInput`, `LoadingButton`, `FormDialog`, `DeleteDialog` em `ui/`;
`CategorySelect`/`AccountSelect`/`CardSelect`/`TagSelect` em `domain/` (primeiros
`hooks/use<Entidade>Queries.ts` reais, para essas 4 entidades de apoio).

**F4 — Sistema de tabelas**: `DataTable` + filtro/paginação/ordenação client-side +
`EmptyState`/`LoadingState` reaproveitados.

**F5 — Dashboard**: `pages/dashboard/DashboardPage.tsx` consumindo os 11 endpoints de
`/central-financeira/*` — primeira tela com dado financeiro real.

**F6 em diante — CRUD por entidade**, uma de cada vez, mesma ordem do backend: Conta →
Categoria → Tag → Cartão → Fatura → Transação → Parcelamento → Transferência → Conta
Recorrente → Financiamento → Empréstimo → Meta → Anexo. Cada etapa usa o Design System (F2),
Formulários (F3) e Tabelas (F4) já prontos — não reconstrói nada disso por entidade.

Nada além da Etapa F1 será implementado sem aprovação explícita entre etapas (mesmo processo
do backend).
