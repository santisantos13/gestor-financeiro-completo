# Análise Arquitetural — CRUD de Transferências (Frontend)

Documento de arquitetura, sem código. Segue o mesmo processo de toda entidade
anterior (Conta, Categoria, Tag, Cartão, Fatura, Transação): entender o
backend real primeiro, propor a experiência depois, esperar aprovação antes
de escrever qualquer linha de código.

## 0. O que é uma Transferência (backend real)

Lido diretamente de `backend/app/models/transferencia.py`,
`schemas/transferencia.py`, `services/transferencia_service.py`,
`repositories/transferencia_repository.py` e `api/routes/transferencia.py`.

Uma `Transferencia` move dinheiro entre duas Contas do MESMO usuário. É uma
entidade **deliberadamente separada de Transação** — não é receita nem
despesa, o patrimônio total do usuário não muda, o dinheiro só troca de
lugar. Por isso **nunca gera Transacao nenhuma**: é ela mesma a fonte da
verdade do próprio efeito financeiro.

Campos (`TransferenciaRead`): `id`, `conta_origem_id`, `conta_destino_id`,
`valor` (Decimal como string), `data`, `descricao` (opcional), `ativo`
(bool).

Regras de negócio (`TransferenciaService`):

- `conta_origem_id != conta_destino_id` (também é `CheckConstraint` no
  banco — o service valida antes para devolver `BusinessRuleError` em vez de
  um `IntegrityError` cru).
- Origem e destino precisam existir, pertencer ao usuário autenticado e
  estar **ativas** — mesmo tratamento 404 para "não existe" e "é de outro
  usuário" (anti-enumeração), `BusinessRuleError` se a conta existe mas está
  inativa.
- `valor` precisa ser `> 0` (`Field(gt=0)` no schema).
- Sem validação de saldo suficiente — a conta pode ficar negativa depois da
  transferência (mesmo modelo de Conta em geral, que não impõe saldo
  mínimo).

**Sem `TransferenciaUpdate` — decisão explícita do backend.** Todos os
campos estruturais (`conta_origem_id`, `conta_destino_id`, `valor`, `data`)
são imutáveis após a criação, porque editar qualquer um exigiria refazer o
cálculo de saldo das contas envolvidas. A única transição de estado é
`POST /transferencias/{id}/cancelar`.

**Sem `DELETE` físico.** `ativo` é soft delete (mesmo padrão de
Conta/Cartão/Tag): `cancelar()` marca `ativo=False`, a linha nunca é
apagada — preserva histórico e some do cálculo de saldo e da listagem
padrão (`apenas_ativas=True` por default em `GET /transferencias`).
Cancelar uma transferência já cancelada é `BusinessRuleError` ("Esta
transferência já está cancelada.").

Endpoints expostos (`api/routes/transferencia.py`):

| Método | Rota | Uso |
|---|---|---|
| `POST` | `/transferencias` | criar |
| `GET` | `/transferencias` | listar (`apenas_ativas`, `skip`, `limit`) |
| `GET` | `/transferencias/{id}` | obter uma |
| `POST` | `/transferencias/{id}/cancelar` | cancelar (soft) |

Não existe `PATCH`/`PUT`, não existe `DELETE`. Isso simplifica bastante o
frontend: **não há "editar transferência"** — só criar e cancelar.

## 1. Como o saldo é afetado

`ContaRepository.somar_transferencias(conta_id)` soma transferências
**ativas** envolvendo a conta: valor recebido (conta é destino) soma, valor
enviado (conta é origem) subtrai. `ContaService._com_saldo()` combina isso
com `somar_transacoes_pagas()`:

```
saldo_atual = saldo_inicial + liquido_transacoes_pagas + liquido_transferencias
```

Duas fontes independentes, sem sobreposição — nenhum ajuste manual de saldo
é necessário no frontend; o saldo de qualquer Conta (`ContaRead.saldo_atual`,
já usado por `useContas`/`AccountSelect`/`ContasCard`) **já reflete
transferências automaticamente** assim que a mutation invalidar a query
certa. Cancelar uma transferência também reflete automaticamente (a soma só
olha `ativo=True`).

## 2. Integração com Dashboard / Central Financeira — GAP real encontrado

Investiguei todos os 11 endpoints de `/central-financeira/*`
(`central_financeira_service.py` por inteiro) e o enum
`TipoEntidadeReferenciavel` (`models/enums.py`, usado por Alerta/Anexo e pela
Agenda Financeira do Dashboard):

```python
class TipoEntidadeReferenciavel(str, enum.Enum):
    CONTA = "CONTA"
    CARTAO = "CARTAO"
    FATURA = "FATURA"
    TRANSACAO = "TRANSACAO"
    PARCELAMENTO = "PARCELAMENTO"
    FINANCIAMENTO = "FINANCIAMENTO"
    EMPRESTIMO = "EMPRESTIMO"
    CONTA_RECORRENTE = "CONTA_RECORRENTE"
    META = "META"
```

**Não existe um valor `TRANSFERENCIA`.** A Agenda Financeira do Dashboard
(`AgendaFinanceiraCard`, que já uso no frontend) só deriva eventos de
Transação (com sub-origens Financiamento/Empréstimo/Parcelamento/Conta
Recorrente) e de Fatura — nenhum dos 11 endpoints de Central Financeira
menciona Transferencia em nenhum lugar. Isso não é um bug: é só um recorte
que nunca incluiu essa entidade porque ela ainda não tinha CRUD no
frontend.

Consequência prática: o Dashboard **já** reflete o efeito de uma
transferência (o saldo de cada Conta muda), mas não existe hoje nenhuma
"linha do tempo" nativa do backend listando transferências recentes ao lado
de transações/faturas. Duas opções, ambas sem tocar no backend:

- **(a)** Deixar como está — o usuário vê o efeito (saldo mudou) mas não a
  causa, a menos que entre em `/transferencias` ou na tela da própria Conta.
- **(b)** O frontend busca `GET /transferencias` (endpoint que já existe) e
  monta sua própria seção "Transferências recentes" numa página de detalhe
  de Conta, ou mescla client-side com a Agenda Financeira do Dashboard.

Não vejo necessidade de pedir mudança no backend (o enum growth ali é
simples, mas mudaria contrato de Alerta/Anexo/Agenda sem necessidade real
agora) — a opção (b), se aprovada, é 100% frontend, reaproveitando o
`transferenciaService.listar()` que esta etapa já cria. **Decisão pendente
de aprovação — seção 8.**

## 3. Integração com Contas

`ContaRepository.existe_vinculo()` (usado só pela exclusão definitiva,
`docs/analise-arquitetural-exclusao.md`) já trata Transferencia como vínculo
bloqueante: uma Conta com qualquer Transferencia associada (mesmo cancelada)
não pode ser excluída definitivamente — só desativada. Isso já está
implementado no backend, nenhuma mudança necessária; só preciso que a
mensagem de erro 422 que o frontend já mostra (`ConfirmAction` de exclusão
de Conta) continue passando por `utils/errors.ts` normalmente — o texto do
backend já menciona "transações, transferências ou cartões vinculados".

Além disso, criar uma transferência exige que **ambas** as contas estejam
ativas — o formulário deve usar `AccountSelect` com `apenasAtivas` (mesmo
componente já usado por Transação/Cartão), tanto para origem quanto
destino, para nunca oferecer uma conta inativa como opção.

## 4. Camada de dados (mesmo molde de Transação)

Segue exatamente o padrão estabelecido por `types/`, `schemas/`,
`services/`, `hooks/use<Entidade>Queries.ts` e `api/queryKeys.ts` (ver
`docs/analise-arquitetural-frontend.md`, seções 5 e 9).

**`types/transferencia.ts`** (novo) — espelha os schemas Pydantic 1:1:

```ts
export interface TransferenciaRead {
  id: number;
  conta_origem_id: number;
  conta_destino_id: number;
  valor: string;
  data: string;
  descricao: string | null;
  ativo: boolean;
}

export interface TransferenciaCreate {
  conta_origem_id: number;
  conta_destino_id: number;
  valor: string;
  data: string;
  descricao?: string | null;
}

/** GET /transferencias — apenas os dois parâmetros reais que o backend
 * aceita além de paginação; sem filtro server-side por conta (diferente de
 * Transação, que filtra por conta_id/cartao_id/tipo/etc de verdade). */
export interface TransferenciaFiltros {
  apenas_ativas?: boolean;
  skip?: number;
  limit?: number;
}
```

Sem `TransferenciaUpdate` — não existe, mesmo raciocínio de
`schemas/transferencia.py` no backend (nada para espelhar).

**`services/transferenciaService.ts`** (novo) — funções finas, um por
endpoint:

```ts
export const transferenciaService = {
  listar: (filtros: TransferenciaFiltros = {}) =>
    httpClient.get<TransferenciaRead[]>("/transferencias", { ...filtros }),
  obter: (id: number) => httpClient.get<TransferenciaRead>(`/transferencias/${id}`),
  criar: (dados: TransferenciaCreate) => httpClient.post<TransferenciaRead>("/transferencias", dados),
  cancelar: (id: number) => httpClient.post<TransferenciaRead>(`/transferencias/${id}/cancelar`),
};
```

**`api/queryKeys.ts`** — nova seção `transferencias`, mesmo molde de
`contas`/`cartoes` (`apenasAtivas` como único parâmetro relevante de
listagem, já que não há filtro server-side rico como em Transação):

```ts
transferencias: {
  all: ["transferencias"] as const,
  list: (apenasAtivas: boolean) => ["transferencias", "list", apenasAtivas] as const,
  detail: (id: number) => ["transferencias", "detail", id] as const,
},
```

**`hooks/useTransferenciaQueries.ts`** (novo) — mesmo molde de
`useTransacaoQueries.ts`, com uma diferença importante na invalidação: uma
transferência afeta **duas** contas (origem e destino), não uma. A função
`invalidarTransferencias` recebe os dois ids e invalida ambos os
`queryKeys.contas.detail`, mais tudo que já é invalidado por qualquer
mudança de saldo (mesma lista de `invalidarTransacoes`: `contas.all`,
`dashboard.saldoConsolidado`, `dashboard.contas`, `dashboard.indicadores`,
prefixos de `resumo`/`visao-mensal`/`agenda`):

```ts
export function invalidarTransferencias(
  queryClient: QueryClient,
  contaOrigemId?: number | null,
  contaDestinoId?: number | null,
) {
  queryClient.invalidateQueries({ queryKey: queryKeys.transferencias.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.contas.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.saldoConsolidado });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.contas });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "resumo"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard", "visao-mensal"] });
  if (contaOrigemId != null) queryClient.invalidateQueries({ queryKey: queryKeys.contas.detail(contaOrigemId) });
  if (contaDestinoId != null) queryClient.invalidateQueries({ queryKey: queryKeys.contas.detail(contaDestinoId) });
}

export function useTransferencias(apenasAtivas = true) { /* useQuery */ }
export function useCriarTransferencia() { /* useMutation, lê conta_origem_id/conta_destino_id da resposta */ }
export function useCancelarTransferencia(contaOrigemId?, contaDestinoId?) { /* useMutation */ }
```

`invalidateQueries({ queryKey: queryKeys.contas.all })` já casa por prefixo
com qualquer `list`/`detail` de Conta (mesmo raciocínio já documentado em
`useTransacaoQueries.ts`), então tecnicamente os dois `contas.detail`
individuais são redundantes com `contas.all` — mantidos mesmo assim pela
mesma razão que Transação mantém `contas.detail(contaId)` ao lado de
`dashboard.contas`: invalidação explícita e legível bate mais barato que
economizar uma linha.

## 5. Schema de formulário (RHF + Zod)

**`schemas/transferencia.ts`** (novo) — só formato/obrigatoriedade, mesma
regra do projeto inteiro (regra de negócio real fica 100% no backend/422):

```ts
export const transferenciaFormSchema = z
  .object({
    conta_origem_id: z.string().min(1, "Selecione a conta de origem."),
    conta_destino_id: z.string().min(1, "Selecione a conta de destino."),
    valor: z.string().min(1, "Informe o valor."),
    data: z.string().min(1, "Informe a data."),
    descricao: z.string().max(200, "Use no máximo 200 caracteres.").optional(),
  })
  .refine((v) => v.conta_origem_id === "" || v.conta_origem_id !== v.conta_destino_id, {
    message: "A conta de destino precisa ser diferente da origem.",
    path: ["conta_destino_id"],
  });
```

Essa validação de "origem ≠ destino" no client é só uma antecipação de UX
(feedback imediato antes de bater no backend) — a validação real e
definitiva continua sendo `TransferenciaService._validar_estrutura` no
servidor, mesmo princípio já usado em todo `schemas/*.ts` do projeto
(`docs/analise-arquitetural-frontend.md`, seção 5).

## 6. Componentes reutilizáveis — nada novo é genérico o bastante para faltar

Levantamento do que já existe e cobre 100% das necessidades estruturais:

| Peça | Já existe em | Reuso |
|---|---|---|
| `AccountSelect` | `domain/conta/AccountSelect.tsx` | usado 2x no formulário (origem e destino) |
| `CurrencyField` | `ui/CurrencyField.tsx` | campo `valor` |
| `DateField` | `ui/DateField.tsx` | campo `data` |
| `TextField` | `ui/TextField.tsx` | campo `descricao` (opcional) |
| `FormDialog` | `ui/FormDialog.tsx` | modal de criação |
| `ConfirmAction` | `ui/ConfirmAction.tsx` | confirmação de cancelamento (`tone="danger"`, mesmo padrão de exclusão) |
| `DataTable` | `ui/DataTable.tsx` | listagem em `/transferencias` |
| `AtivoBadge` | `ui/AtivoBadge.tsx` | coluna de status (ativa/cancelada) |
| `InstitutionBadge` | `ui/InstitutionBadge.tsx` | identificar banco de cada conta na tabela |
| `PeriodoSeletor` | `domain/dashboard/PeriodoSeletor.tsx` | opcional, se a página filtrar por período (ver seção 9) |

Nenhum select "inteligente" novo é necessário — `AccountSelect` já existe e
já é escopado ao usuário autenticado. A única customização é impedir que a
mesma conta seja escolhida nos dois campos, que é validação de formulário
(seção 5), não um componente novo.

## 7. A experiência: transferência como movimento, não como formulário

Esse é o pedido central desta etapa — "uma transferência deve parecer um
movimento de dinheiro entre contas, não apenas um formulário". Proposta,
usando só o vocabulário já aprovado em `docs/motion-principles.md`
(nenhuma animação nova é inventada fora dele):

### 7.1 O formulário em si — duas contas + uma seta entre elas

Em vez de dois `AccountSelect` empilhados verticalmente (como
"Origem"/"Cartão" em Transação), o layout mostra os dois lado a lado com um
indicador visual de fluxo entre eles:

```
┌─────────────────┐        ┌─────────────────┐
│  De              │  ──►   │  Para            │
│  [AccountSelect] │        │  [AccountSelect] │
└─────────────────┘        └─────────────────┘
```

A seta (`ArrowRight` do `lucide-react`, já usado em `ProximoPassoCard`) fica
entre os dois cards. Quando origem e destino já foram escolhidos, a seta
ganha uma pequena animação de translação horizontal em loop suave (`x: [0,
4, 0]`, `repeat: Infinity`, duração `DURATION.slow`/`ease-in-out`) — sugere
"dinheiro fluindo" sem ser um efeito chamativo (nada de partículas ou
confete; motion-principles.md, seção 5.11, reserva efeitos "hero" para no
máximo 1-2 elementos por vez, e aqui é exatamente 1).

Um botão pequeno de "inverter" (`ArrowLeftRight`) entre os dois selects
troca origem↔destino sem precisar reabrir os dois dropdowns — atalho de UX
barato, comportamento 100% client-side (só troca os dois valores do
formulário).

### 7.2 Preview da movimentação (antes de confirmar)

Abaixo do valor/data, um pequeno resumo textual-visual, montado
client-side a partir do que já está preenchido (nenhuma chamada nova ao
backend):

```
[Nome da conta origem]  −R$ 300,00  ──►  +R$ 300,00  [Nome da conta destino]
```

Usa as mesmas cores semânticas já estabelecidas (`text-negative` para o
valor saindo, `text-positive` para o valor entrando) — o mesmo par de
tokens que `transacaoTableColumns.tsx` já usa para Receita/Despesa, então
não introduz nenhum significado de cor novo (design-system.md, seção 6.4:
cor sempre com significado fixo). Esse preview só aparece quando origem,
destino e valor já são válidos — antes disso, um placeholder neutro
("Selecione as duas contas para ver o preview").

### 7.3 Confirmação elegante (sucesso)

Ao salvar com sucesso, em vez de só um toast genérico, o toast de sucesso
reaproveita o mesmo texto do preview ("R$ 300,00 de [Conta A] para [Conta
B]") — informação que o usuário já validou, reafirmada. Nenhum componente
novo: `useToast().success()` já aceita uma string livre, só muda o
conteúdo da mensagem.

### 7.4 Indicadores de origem/destino na listagem

Na tabela `/transferencias` (`buildTransferenciaTableColumns`), uma única
coluna "Movimentação" (em vez de duas colunas separadas "Origem"/"Destino")
reaproveita o mesmo layout seta-no-meio da seção 7.1, mas estático (sem
animação — motion-principles.md é claro que listas densas não recebem
efeitos "hero" por linha):

```
[InstitutionBadge] Conta A   →   [InstitutionBadge] Conta B
```

Cada `InstitutionBadge` já existe (`ui/InstitutionBadge.tsx`) e já resolve
o nome/instituição de qualquer Conta — mesmo componente que
`transacaoTableColumns.tsx` usa na coluna "Origem".

### 7.5 Timeline das movimentações

O pedido menciona "timeline das movimentações" — interpreto como a própria
listagem em `/transferencias`, ordenada por data desc (já é o
`ORDER BY data DESC, id DESC` que `TransferenciaRepository.listar_do_usuario`
aplica no backend — nenhuma ordenação adicional necessária no client). Não
proponho um componente de timeline visual novo (linha vertical com
marcadores etc.) — o `DataTable` já é o padrão estabelecido para "histórico
de lançamentos" em todo o projeto (é exatamente o que `/transacoes` já é).
Introduzir um segundo padrão visual só para Transferência quebraria a
consistência que as etapas anteriores construíram, sem ganho real de
clareza. Se, depois de ver a tabela funcionando, você (usuário) sentir que
falta uma visão mais "história contada" (como a página de detalhe de
Cartão fez para faturas), isso pode virar uma etapa de refinamento
separada — não antecipo isso agora (YAGNI).

## 8. Decisões que dependem da sua aprovação

Antes de qualquer código, preciso da sua decisão explícita sobre os pontos
abaixo:

1. **Gap da Agenda Financeira (seção 2).** Deixar como está (transferências
   não aparecem na timeline de eventos do Dashboard, só o efeito no saldo é
   visível) ou construir uma seção "Transferências recentes" separada
   (frontend-only, busca `GET /transferencias` direto, sem mudar o
   backend)? Recomendo deixar como está nesta etapa e revisar depois que o
   CRUD básico estiver no ar — mas é sua chamada.
2. **Localização da tela.** Proponho uma nova rota `/transferencias` no
   `Sidebar`/`AppRoutes` (mesmo nível de `/transacoes`), com `DataTable` +
   botão "Nova transferência" abrindo o `FormDialog`. Alternativa seria
   colocar transferências como uma aba dentro de `/contas` (já que a
   entidade é sempre relativa a duas contas) — recomendo a rota própria,
   consistente com o padrão "uma entidade, uma página" já usado por
   Transação/Cartão/Categoria/Tag.
3. **Filtro por período.** Transação usa `PeriodoSeletor` porque tem volume
   alto e o backend filtra `data_inicio`/`data_fim` de verdade. Transferência
   provavelmente tem volume bem menor (é uma ação ocasional, não um
   lançamento diário) — proponho listagem simples sem filtro de período
   inicialmente (só busca textual do `DataTable` sobre a lista carregada),
   adicionando período depois só se o volume real justificar. Confirma?
4. **Ação "cancelar" vs. "excluir".** O backend só oferece cancelar (soft),
   nunca excluir de verdade — diferente de Transação, que tem `DELETE`
   físico. O rótulo/ícone da ação na tabela deve deixar isso claro
   ("Cancelar transferência", não "Excluir") para não sugerir uma ação que
   não existe. Confirma o texto/tom (`ConfirmAction` com `tone="danger"`,
   mesmo peso visual de uma exclusão, já que desfaz um movimento de
   dinheiro real)?
5. **Transferências canceladas na listagem.** Por padrão (`apenas_ativas`),
   a lista mostra só as ativas — mesmo comportamento de toda entidade com
   soft delete. Proponho um toggle "Mostrar canceladas" (mesmo padrão que
   outras entidades já usam para "mostrar inativas"), exibindo-as com
   `AtivoBadge`/estilo esmaecido, sem ação de cancelar disponível de novo.
   Confirma?
6. **Animação da seta em loop (seção 7.1).** Confirma que uma animação
   contínua e sutil (translação de poucos pixels, em loop, só no
   formulário aberto) está dentro do espírito de "elegante, sem exagero"
   pedido — ou prefere a seta estática, só com uma transição de entrada
   (`fadeIn`) e sem loop?

## 9. Resumo das decisões arquiteturais já tomadas (sem necessidade de aprovação)

- Nenhuma mudança no backend. Todos os 4 endpoints existentes já cobrem o
  CRUD completo que o backend deliberadamente oferece (criar, listar,
  obter, cancelar — sem editar, sem excluir físico).
- Camada de dados segue 1:1 o molde de Transação/Cartão: `types/`,
  `schemas/`, `services/`, `hooks/use<Entidade>Queries.ts`, seção nova em
  `api/queryKeys.ts`. Nenhuma abstração nova de infraestrutura.
- Nenhum select "inteligente" novo — `AccountSelect` (já existente) é
  reaproveitado duas vezes no mesmo formulário.
- `ConfirmAction` (já existente) cobre a confirmação de cancelamento —
  nenhum componente de confirmação novo.
- `DataTable` (já existente) é o padrão de listagem — nenhum componente de
  "timeline" visual novo introduzido nesta etapa (seção 7.5).
- Toda a "sensação de movimento" (seção 7) é alcançada compondo primitivas
  já existentes (`ArrowRight`/`ArrowLeftRight` do `lucide-react`, tokens de
  cor `positive`/`negative` já semânticos, springs/durations já
  catalogados em `lib/motion.ts`) — nenhum token, spring ou duração nova é
  proposto; motion-principles.md continua sendo a fonte única da verdade
  de timing.
- Sem testes automatizados de frontend nesta etapa — mesma posição já
  registrada para todas as entidades anteriores
  (`docs/analise-arquitetural-frontend.md`, seção 15).

## 10. O que NÃO está incluído nesta etapa

- Editar uma transferência já criada (o backend não permite).
- Excluir uma transferência definitivamente (o backend não permite —
  só cancelar).
- Transferência entre contas de usuários diferentes (o backend não
  permite — mesmo usuário nos dois lados, sempre).
- Qualquer nova rota ou campo no backend (enum `TipoEntidadeReferenciavel`
  ganhando `TRANSFERENCIA`, Alerta/Anexo passando a referenciar
  Transferencia, etc.) — fora de escopo a menos que você aprove
  explicitamente investigar isso à parte.
