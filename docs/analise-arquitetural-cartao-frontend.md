# Análise arquitetural — CRUD de Cartão (Etapa F9, frontend)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Quarta entidade de
CRUD real do frontend, depois de Conta (F6), Categoria (F7) e Tag (F8). Baseado em leitura
direta do backend (`app/models/cartao.py`, `schemas/cartao.py`, `repositories/cartao_repository.py`,
`services/cartao_service.py`, `api/routes/cartao.py`), `docs/analise-arquitetural-frontend.md`,
`docs/design-system.md`, `docs/motion-principles.md` e da implementação atual do frontend
(Conta como referência mais próxima, `lib/institutions.ts`/`InstitutionBadge`, `ProgressBar`,
`MetricCard`, `CategorySelect`, sistema de tabelas e formulários completos).

## 0. Checagem de arquitetura de projeto

Uma peça de infraestrutura planejada desde a Etapa F1 e ainda não construída — `AccountSelect`
— passa a ser necessária nesta etapa (seção 7). **Isto não é uma surpresa arquitetural**: já
está documentado como decisão pendente-de-gatilho em três lugares diferentes, todos lidos
nesta análise:

- `docs/analise-arquitetural-frontend.md`, seção 12: `AccountSelect` listado em
  `domain/conta/AccountSelect.tsx` desde a arquitetura original do frontend.
- `docs/design-system.md`, seção 14: "Select / Combobox... Base para
  `CategorySelect`/`AccountSelect`/`CardSelect`/`TagSelect`"; seção 15: mesmo grupo,
  "Combobox com ícone/cor por item quando aplicável".
- `docs/revisao-tecnica-tag-frontend.md`, seção 7: "`TagSelect`... mesma decisão já tomada
  para `AccountSelect`/`CardSelect` na F6: só nasce quando a entidade que o consome de
  verdade for implementada." Cartão É essa entidade — `conta_pagamento_id` exige escolher
  uma Conta existente do próprio usuário.

Ou seja: construir `AccountSelect` agora não é uma mudança de arquitetura, é a arquitetura já
aprovada sendo executada no ponto exato em que foi planejada para nascer. Segue exatamente o
padrão já usado por `CategorySelect` (primeiro select "inteligente" do projeto, construído na
F7 quando Categoria precisou de autorreferência) — nenhum componente genérico novo, nenhuma
mudança em `SearchSelect`/`Select`/`FormField`. Fora isso, nenhuma outra pendência de
arquitetura de projeto foi encontrada; todas as demais decisões desta análise são composição
local à página `/cartoes`, no mesmo espírito de Categoria (hierarquia visual) e Tag
(`TagBadge`) em etapas anteriores.

## 1. Objetivo

CRUD completo de Cartão: criar, listar, ver, editar, desativar/reativar — consistente em
qualidade e reaproveitamento de infraestrutura com Conta/Categoria/Tag, mais uma revisão
crítica de UX específica do domínio (cartão de crédito tem uma dimensão visual e quantitativa
— bandeira, banco, limite — que as três entidades anteriores não têm).

## 2. Contrato do backend (fonte de verdade)

- **Model** (`app/models/cartao.py`): `id`, `usuario_id`, `conta_pagamento_id` (FK para
  `contas.id` — de onde o dinheiro sai ao pagar a fatura), `nome` (único por usuário),
  `instituicao` (string livre, mesmo campo de Conta), `bandeira` (enum fechado, 7 valores),
  `ultimos_quatro_digitos` (string de 4 dígitos — **nunca o número completo**, nem
  coletado nem armazenado em nenhum lugar do sistema), `limite` (decimal), `dia_fechamento`/
  `dia_vencimento` (inteiros 1-31), `ativo`.
- **`CartaoRead.limite_disponivel`**: campo calculado, nunca uma coluna — mesmo princípio de
  `ContaRead.saldo_atual`. `CartaoService._com_limite_disponivel` soma os gastos que ainda
  consomem limite (`CartaoRepository.somar_gastos_nao_pagos`: despesas do cartão sem fatura
  associada OU cuja fatura não está `PAGA`) e subtrai de `limite`. **Pode ficar negativo**
  (cartão estourado) — de propósito, nunca "clampado" em zero; o frontend deve mostrar esse
  estouro, não escondê-lo.
- **`Bandeira`** (`app/models/enums.py`): `VISA`, `MASTERCARD`, `ELO`, `AMERICAN_EXPRESS`,
  `HIPERCARD`, `DINERS_CLUB`, `OUTRA` — já espelhado 1:1 em `frontend/src/types/enums.ts`
  (nenhuma mudança necessária ali).
- **Reativação implícita ao criar** (`CartaoService.criar`): se o nome colidir com um cartão
  **desativado** do mesmo usuário, reativa em vez de rejeitar, sobrescrevendo todos os campos
  com o payload novo — mesmo padrão exato de `TagService.criar`/`CategoriaService.criar`, já
  tratado de forma inteiramente genérica pelo frontend (o 201 de `POST` não distingue "criação
  de verdade" de "reativação disfarçada"; nenhum código condicional necessário).
- **Renomear não reativa/mescla** (`CartaoService.atualizar`): colisão de nome ao editar é
  sempre 409 puro — mesma decisão de Tag/Categoria.
- **`conta_pagamento_id` validado contra o usuário** (`_validar_conta_do_usuario`): 404 (não
  409/422) se a conta não existe ou é de outro usuário — mesmo padrão anti-enumeração
  (BOLA) já usado em `CategoriaService._resolver_pai`. O frontend não precisa validar isso
  de novo: `AccountSelect` só lista as contas do próprio usuário (a query já é escopada por
  `usuario_atual`), então a UI naturalmente não oferece IDs de outro usuário — a validação do
  backend é defesa em profundidade, não a única linha de defesa, mas o frontend não duplica a
  regra, só reduz a chance de tentar um ID inválido.
- **Desativar não têm efeito cascata em Fatura/Transação** — soft delete simples (`ativo =
  False`), histórico preservado, mesmo padrão de Conta/Categoria/Tag.
- **`GET /cartoes` já ordenado por `nome`** (`CartaoRepository.listar_do_usuario`) — mesmo
  padrão de Conta/Categoria/Tag, o frontend não precisa ordenar de novo (mas o usuário pode
  reordenar via `DataTable.sortable`, client-side, como em qualquer outra entidade).

## 3. Pré-requisitos confirmados (infraestrutura 100% reutilizável sem alteração)

Confirmado por leitura direta do código, não assumido:

- **React Query** (`useCartaoQueries.ts`, mesmo molde de `useContaQueries.ts`/
  `useTagQueries.ts`, com `placeholderData: keepPreviousData` desde o primeiro commit).
- **Sistema de Formulários** (`FormDialog`, `Form`, `TextField`, `CurrencyField`,
  `NumberField`, `SelectField`) — nenhum campo de Cartão exige um componente novo do Form
  System em si (só dois componentes novos de **domínio**, seções 7 e 8, que compõem por
  cima de `SearchSelect`/`SelectField` já existentes).
- **Sistema de Tabelas** (`DataTable`, `ColumnDef`, `FilterDef`, busca, paginação,
  ordenação, `hideOnMobile`, card mobile) — usado exatamente como em Conta/Categoria/Tag.
- **`ProgressBar`** (`components/ui/ProgressBar.tsx`) — já existe, já é genérico (0-100,
  spring `gentle`, `docs/design-system.md` seção 14), construído para "progresso de
  formulário (ex. Meta)" mas sem nenhuma dependência de Meta — é exatamente o componente
  para "progresso do limite" pedido na revisão de UX. Zero mudança necessária.
- **`MetricCard`** (usado hoje só por `IndicadoresStrip` no Dashboard) — reaproveitável para
  os "indicadores rápidos" da página `/cartoes` (seção 10). Primeira vez que `MetricCard` é
  usado fora do Dashboard, mas é um componente puramente apresentacional (label + valor),
  sem nenhum acoplamento ao Dashboard — reaproveitamento direto, não uma mudança nele.
  Confirmado lendo `IndicadoresStrip.tsx`.
- **`InstitutionBadge`/`lib/institutions.ts`** — Cartão tem `instituicao` (mesmo campo livre
  de Conta); zero mudança, reaproveitamento direto (já é multi-entidade por design, ver
  comentário do próprio arquivo: "usado por Conta, Cartão e os cards do Dashboard").
- **Toast, `ConfirmAction`, `Skeleton`/`LoadingCard`, `EmptyState` (via `DataTable`), Motion
  (`lib/motion.ts`), padrões de responsividade/acessibilidade** — mesmo reaproveitamento
  integral de sempre, nenhuma mudança.

## 4. Cartão ↔ outras entidades

- **Conta** (`conta_pagamento_id`, obrigatório): de onde a fatura é paga. Requer
  `AccountSelect` (seção 7).
- **Fatura/Transação/Parcelamento/ContaRecorrente**: têm FK para `cartao_id`, mas nenhuma
  dessas entidades tem CRUD no frontend ainda — fora de escopo desta etapa (mesma fronteira já
  aplicada em Conta/Categoria/Tag: a entidade nasce sozinha, o que a consome vem depois).
  `CardSelect` (`domain/cartao/CardSelect.tsx`, já citado no design-system) fica para quando
  Transação for implementada — mesmo tratamento que `TagSelect`/`AccountSelect` já receberam
  antes de terem uma entidade consumidora real.
- **Central Financeira**: `/central-financeira/cartoes` já lista cartões com
  `limite_disponivel`, `dia_fechamento`/`dia_vencimento` (consumido hoje só por
  `CartoesCard.tsx` no Dashboard) e `/central-financeira/indicadores` já expõe
  `cartoes_ativos`. Mutações de Cartão devem invalidar `queryKeys.dashboard.cartoes` e
  `queryKeys.dashboard.indicadores` — mesmo padrão exato que `useContaQueries.ts` já aplica
  para `dashboard.contas`/`dashboard.saldoConsolidado`/`dashboard.indicadores`.

## 5. Estrutura de arquivos nova

```
frontend/src/
  types/cartao.ts                          # CartaoRead / CartaoCreate / CartaoUpdate
  schemas/cartao.ts                        # Zod (formato/obrigatoriedade, espelha CartaoCreate)
  services/cartaoService.ts                # listar/obter/criar/atualizar/desativar
  hooks/useCartaoQueries.ts                # useCartoes/useCartao/useCriarCartao/useAtualizarCartao/useDesativarCartao
  lib/bandeiras.ts                         # NOVO — registry de Bandeira (label/cor/sigla), mesmo espírito de lib/institutions.ts
  components/ui/BandeiraBadge.tsx          # NOVO — consome lib/bandeiras.ts, mesmo papel de InstitutionBadge
  components/domain/conta/AccountSelect.tsx # NOVO — já previsto na arquitetura (seção 0)
  components/domain/cartao/
    CartaoVisual.tsx                       # NOVO — "cartão visual" (seção 9)
    cartaoTableColumns.tsx
    CartaoFormDialog.tsx
  pages/cartoes/CartoesPage.tsx
```

`AccountSelect` fica em `domain/conta/` (não `domain/cartao/`) porque é sobre Conta, não
sobre Cartão — mesma convenção já usada (o componente mora perto da entidade que ele
representa, não perto de quem o consome; `CategorySelect` mora em `domain/categoria/` e já é
consumido de fora daquele diretório). `BandeiraBadge` fica em `ui/` (não `domain/cartao/`)
pelo mesmo raciocínio que `InstitutionBadge` está em `ui/`: não é específico de Cartão, é uma
peça de apresentação genérica para "um enum fechado com cor de marca conhecida" — o
precedente de `InstitutionBadge` já é usado por mais de uma entidade (Conta e Cartão), então
`BandeiraBadge` nasce no mesmo nível por consistência, mesmo só tendo um consumidor hoje.

## 6. Camada de dados

`types/cartao.ts` espelha `CartaoCreate`/`CartaoUpdate`/`CartaoRead` 1:1 (`limite` e
`limite_disponivel` como `string` no tipo TS, mesmo tratamento de `Decimal` já usado em
`ContaRead.saldo_atual`/`TagRead` não se aplica, mas sim ao padrão de
`FinanciamentoRead`/valores monetários — string decimal, nunca `number` bruto, para não
perder precisão).

`hooks/useCartaoQueries.ts` — mesmo molde de `useContaQueries.ts`:

```ts
function useInvalidateCartoes() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.cartoes.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.cartoes });
    queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.indicadores });
  };
}
```

`queryKeys.cartoes` (novo bloco em `api/queryKeys.ts`, mesmo formato de `queryKeys.contas`):
`all`, `list(apenasAtivas)`, `detail(id)`. `useCartoes` já nasce com `placeholderData:
keepPreviousData` (mesmo tratamento que Tag recebeu desde o primeiro commit, não como
correção posterior).

## 7. `AccountSelect` — primeiro select de domínio fora de Categoria

Segue exatamente o molde de `CategorySelect.tsx` (leitura completa feita nesta análise):
busca sua própria lista via `useContas(apenasAtivas)`, se comporta como `SearchSelect` por
fora, nenhum estado próprio de rede.

```tsx
export interface AccountSelectProps {
  name: string;
  label: string;
  optional?: boolean;
  description?: string;
  placeholder?: string;
  disabled?: boolean;
  apenasAtivas?: boolean;
}

export function AccountSelect({ name, label, ..., apenasAtivas = true }: AccountSelectProps) {
  const { data: contas, isLoading } = useContas(apenasAtivas);
  const options = useMemo(
    () => (contas ?? []).map((c) => ({ value: String(c.id), label: c.nome })),
    [contas],
  );
  return <SearchSelect name={name} label={label} options={options} loading={isLoading} ... />;
}
```

Mais simples que `CategorySelect` (sem hierarquia, sem cadeia de ancestrais, sem exclusão de
descendentes) — a única diferença de UX vale a pena registrar: `docs/design-system.md`, seção
15, sugere "ícone/cor por item quando aplicável (ex. `CardSelect` mostra a bandeira do
cartão)". Para `AccountSelect`, o equivalente natural seria mostrar `InstitutionBadge` por
opção (a conta já tem `instituicao`). **Decisão**: manter a primeira versão só com o nome da
conta (texto puro), sem badge por item dentro do dropdown — o Design System usa "quando
aplicável", não "sempre"; `SearchSelect` já não foi construído com um slot de ícone por opção
(confirmado lendo `Select.tsx`/`SearchSelect.tsx`: `SelectOption` é só `{ value, label }`).
Adicionar um slot de ícone por opção seria uma mudança na infraestrutura genérica de Select
para o benefício de uma única entidade — exatamente o tipo de mudança que vale mais a pena
avaliar em conjunto quando `CardSelect` (bandeira) e outros selects visuais futuros
existirem, não decidida isoladamente aqui. Registrado como melhoria futura (seção 17), não
implementada nesta etapa.

## 8. `lib/bandeiras.ts` + `BandeiraBadge` — identificação da bandeira

Mesma decisão de direitos de marca já tomada para `lib/institutions.ts` (documentada lá,
seção 2 de `docs/revisao-tecnica-branding-e-microinteracoes.md`): nenhum SVG de logo real de
bandeira é embutido. Em vez disso, monograma sobre a cor de marca pública real — mesmo
padrão visual, mais simples de implementar porque `Bandeira` é um **enum fechado** (7
valores), não texto livre — não precisa de `normalizar()`/aliases/fallback "desconhecida",
só um mapa direto:

```ts
export interface BandeiraInfo { label: string; cor: string; sigla: string; }

export const BANDEIRAS: Record<Bandeira, BandeiraInfo> = {
  VISA: { label: "Visa", cor: "#1A1F71", sigla: "VI" },
  MASTERCARD: { label: "Mastercard", cor: "#EB001B", sigla: "MC" },
  ELO: { label: "Elo", cor: "#000000", sigla: "EL" },
  AMERICAN_EXPRESS: { label: "American Express", cor: "#2E77BC", sigla: "AE" },
  HIPERCARD: { label: "Hipercard", cor: "#B3131B", sigla: "HC" },
  DINERS_CLUB: { label: "Diners Club", cor: "#004A97", sigla: "DC" },
  OUTRA: { label: "Outra", cor: "#3F3F46", sigla: "—" },
};
```

`BandeiraBadge.tsx` consome esse mapa exatamente como `InstitutionBadge` consome
`resolveInstitution` — mesmas classes de tamanho (`sm`/`md`/`lg`), mesmo `corDeContraste`
(`lib/color.ts`) para o texto do monograma. `OUTRA` usa a mesma cor neutra
(`#3F3F46`) já usada como fallback em `institutions.ts` — consistência deliberada entre os
dois registries.

## 9. Visual do cartão — `CartaoVisual`

Esta é a peça nova mais visível pedida na revisão de UX ("visual dos cartões", "identificação
visual do banco", "identificação da bandeira", "limite utilizado/disponível", "progresso do
limite"). Decisão de composição (não de arquitetura de projeto — escopo só de Cartão):

- **A listagem continua sendo `DataTable`** — mesma infraestrutura de busca/filtro/paginação/
  ordenação/estado vazio/responsividade de toda entidade anterior, nenhuma duplicação. Não
  vira uma página de grid de cards do zero (isso sim seria uma mudança de padrão de página
  digna de discussão à parte — não é o que esta análise propõe).
- **A coluna "Cartão" (substituindo "Nome") usa `render` para desenhar o visual rico**, mesmo
  mecanismo que Categoria já usa para hierarquia (indentação + conector) e Tag usa para
  `TagBadge` — nenhuma mudança em `DataTable`/`ColumnDef` necessária, é só mais um `render`
  customizado:
  - `InstitutionBadge` (banco) + `BandeiraBadge` (bandeira) lado a lado.
  - Nome do cartão + `•••• {ultimos_quatro_digitos}` (mesmo formato que `CartoesCard.tsx` do
    Dashboard já usa — "•••• 1234" — reaproveitado, não inventado agora).
  - Uma `ProgressBar` compacta logo abaixo, com `limite_utilizado / limite` (cálculo
    puramente de apresentação: `limite_utilizado = limite - limite_disponivel`, nunca
    armazenado nem enviado ao backend — mesmo espírito de `ordenarCategoriasPorHierarquia`,
    uma função pura derivada no frontend).
  - Cor da barra reage à proximidade do limite: tokens `--color-accent` (uso normal),
    `--color-warning` (≥80%), `--color-negative` (≥100%, estourado) — únicas cores
    semânticas já existentes no Design System, nenhuma cor nova. Mesma filosofia de "cor
    sempre com significado fixo" (design-system.md, seção 6.4).
- **No card mobile do `DataTable`** (abaixo de `md`, mecanismo já existente desde o
  Refinamento de UI), a coluna "Cartão" com esse `render` rico já vira naturalmente o
  elemento mais proeminente do card — é exatamente o "visual de cartão físico" que a revisão
  de UX pede, sem precisar de um componente de layout mobile separado. **Nenhuma mudança em
  `DataTable.tsx` necessária** — o comportamento de "cada `ColumnDef` vira uma linha do card"
  já existe, só o conteúdo desta coluna específica é mais rico que os `render`s anteriores.
- **Reaproveitado também no formulário** (`CartaoFormDialog`), como preview ao vivo — mesmo
  padrão de `InstituicaoPreview`/`TagPreview` já usado em `ContaFormDialog`/`TagFormDialog`
  (`useWatch` escopado, só o preview re-renderiza a cada tecla, não o formulário inteiro).

`CartaoVisual` é deliberadamente **um componente de apresentação puro** (recebe
`nome`/`instituicao`/`bandeira`/`ultimosQuatroDigitos`/`limite`/`limiteDisponivel` como
props), não acoplado a `CartaoRead` — reaproveitável tanto na coluna da tabela quanto no
preview do formulário (que nem sempre tem um `CartaoRead` completo, ex. criação) sem
conversão de tipo estranha.

## 10. Indicadores rápidos da página

Reaproveitamento de `MetricCard` (seção 3), computados **no cliente** a partir da própria
lista já carregada por `useCartoes()` — sem endpoint novo, sem requisição extra (mesma
filosofia de `ordenarCategoriasPorHierarquia`: dado que já veio da API, só reprocessado na
UI):

```ts
const limiteTotal = cartoes.reduce((soma, c) => soma + Number(c.limite), 0);
const disponivelTotal = cartoes.reduce((soma, c) => soma + Number(c.limite_disponivel), 0);
const utilizadoTotal = limiteTotal - disponivelTotal;
```

Faixa de `MetricCard` no topo da página (mesmo componente, mesmo grid responsivo de
`IndicadoresStrip`): "Limite total", "Utilizado", "Disponível", "Cartões ativos" (este último
já vem pronto de `useIndicadoresGeraisQuery` — mas para não acoplar `/cartoes` a uma query do
Dashboard, calculado localmente como `cartoes.length` também é aceitável e mais simples;
decisão final registrada como "usar `cartoes.length` da própria listagem", evitando uma
segunda fonte de verdade para o mesmo número).

**Primeira página de CRUD de entidade a ganhar uma faixa de indicadores** (Conta/Categoria/
Tag não têm) — justificado pela natureza quantitativa específica de Cartão (limite é um
recurso finito e compartilhado entre cartões, vale a pena ver o total agregado; Conta não tem
um equivalente natural — soma de saldos de contas de tipos diferentes, corrente+investimento
por exemplo, já é feita no Dashboard via `saldoConsolidado`, não faria sentido duplicar
aqui). Não é um padrão novo forçado em todas as páginas futuras — cada entidade decide se
indicadores agregados fazem sentido para ela (Meta, quando implementada, é uma candidata
natural pelo mesmo motivo).

## 11. Página `/cartoes` — UX

- **Busca** (`DataTable.searchable`): por nome, instituição e `ultimos_quatro_digitos` — mesmo
  mecanismo client-side já usado por Conta (`searchPlaceholder="Buscar por nome ou
  instituição..."`), estendido para incluir os últimos 4 dígitos como termo pesquisável
  (útil: "qual cartão termina em 4521?").
- **Filtro por bandeira** (`FilterDef`, mesmo padrão do filtro `tipo` de Conta): usa
  `BANDEIRAS` (seção 8) para os labels das opções.
- **Ordenação**: nome (default, já vem ordenado do backend), limite, limite disponível —
  `sortable: true` nas colunas relevantes, `DataTable` já cuida do resto.
- **Ações de linha**: Ver/Editar/Desativar/Reativar — mesmo conjunto de Conta/Categoria/Tag,
  mesmos ícones (`Eye`/`Pencil`/`Ban`/`RotateCcw`).
- **Estado vazio**: `emptyIcon={CreditCard}` (`lucide-react`, mesmo ícone já usado como
  "Cartão" no registry de `lib/icons.ts` de Categoria — sem conflito, contextos diferentes,
  mesmo raciocínio que já validou `Tags` vs `Tag` na F8: aqui não há colisão porque
  `lib/icons.ts` é só consumido por `IconField`/`CategoryBadge`, nunca por `emptyIcon` de
  outra entidade).
- **Feedback visual**: toasts de sucesso/erro mesmo padrão de sempre
  (`"Cartão \"X\" criado/atualizado/desativado."`); 409 de nome duplicado tratado
  genericamente (mesmo caminho que Tag validou — `detail` é string solta, vira toast, nunca
  destaque de campo); 404 de `conta_pagamento_id` inválido não deveria acontecer na prática
  (a UI só oferece contas reais do usuário via `AccountSelect`), mas se acontecer (ex. conta
  desativada entre abrir o formulário e submeter) cai no mesmo tratamento genérico de erro.

## 12. Regras de negócio não duplicadas

Mesma disciplina de todas as etapas anteriores — nenhuma regra de negócio é reimplementada no
frontend, só refletida via schema Zod de **formato**:

```ts
export const cartaoFormSchema = z.object({
  nome: z.string().min(1, "Informe o nome do cartão.").max(120, "Use no máximo 120 caracteres."),
  conta_pagamento_id: z.string().min(1, "Selecione a conta de pagamento."), // AccountSelect devolve string, convertido no payload
  instituicao: z.string().min(1, "Informe a instituição.").max(120, "Use no máximo 120 caracteres."),
  bandeira: z.enum(["VISA", "MASTERCARD", "ELO", "AMERICAN_EXPRESS", "HIPERCARD", "DINERS_CLUB", "OUTRA"]),
  ultimos_quatro_digitos: z.string().regex(/^\d{4}$/, "Informe os 4 últimos dígitos."),
  limite: z.string().min(1, "Informe o limite."),
  dia_fechamento: z.number({ error: "Informe o dia de fechamento." }).min(1).max(31),
  dia_vencimento: z.number({ error: "Informe o dia de vencimento." }).min(1).max(31),
});
```

Note: diferente de Conta (`instituicao` opcional), em Cartão `instituicao` é **obrigatório**
no backend (`Field(min_length=1, ...)`, sem `| None` em `CartaoCreate`) — o schema Zod reflete
essa obrigatoriedade real, não uma escolha de UX independente.

- **`dia_fechamento`/`dia_vencimento` (1-31)**: validação de faixa é só feedback antecipado —
  o backend valida de verdade (`Field(ge=1, le=31)`). Reaproveita `NumberField` puro
  (`decimalPlaces={0}`), **nenhum componente de campo novo** — a validação de intervalo é
  responsabilidade do Zod, não do componente (mesmo padrão já usado em todo o projeto: campos
  formatam, schemas validam). `docs/design-system.md`, seção 17, já antecipa exatamente este
  par de campos como exceção explícita ao "coluna única sempre": "campos logicamente pareados
  e curtos (ex. `dia_fechamento`/`dia_vencimento` de Cartão) podem dividir uma linha em duas
  colunas iguais" — decisão de layout já tomada antes desta etapa começar, só aplicada aqui.
- **Reativação implícita, 409 de nome duplicado, validação de posse de `conta_pagamento_id`**:
  tratados 100% no backend, zero lógica condicional nova no frontend (seção 2).
- **`limite_utilizado`**: calculado no frontend só para exibição (seção 9) — nunca enviado ao
  backend, nunca usado para decidir nada (o backend já manda `limite_disponivel` pronto).

## 13. Motion

Nenhum timing novo — reaproveitamento de `lib/motion.ts`/`docs/motion-principles.md`:

- `ProgressBar` já anima com `SPRING.gentle` (seção 6.1 de motion-principles: elementos onde
  um movimento abrupto pareceria errático — limite de cartão é exatamente esse caso).
- `InstitutionBadge`/`BandeiraBadge` são estáticos (sem motion próprio), consistente com
  `Badge`/`InstitutionBadge` hoje.
- Preview do formulário (`CartaoVisual` dentro de `CartaoFormDialog`) usa o mesmo padrão de
  `useWatch` escopado — sem motion extra além do que `FormDialog`/campos já trazem.
- Mudança de status (Badge ativo/inativo) já usa o crossfade padrão de `Badge`, sem alteração.

## 14. Acessibilidade e mobile

- `ProgressBar` já expõe `role="progressbar"`/`aria-valuenow` (seção `components/ui/ProgressBar.tsx`,
  já lido) — nenhuma mudança necessária, `CartaoVisual` só passa o `aria-label` com contexto
  ("Limite utilizado do cartão Nubank Roxinho", por exemplo).
- `BandeiraBadge`/`InstitutionBadge` seguem o mesmo padrão de `title`/texto acessível já
  usado por `InstitutionBadge` (o monograma sozinho não é a única forma de identificar o
  banco/bandeira — o nome também aparece como texto ao lado, na tabela e no formulário,
  nunca só cor+monograma isolados).
- Área de toque mínima de 40px nas ações de linha, já garantido por `RowActions` (herdado, sem
  mudança).
- Mobile: card do `DataTable` já reformata a tabela em lista de cards abaixo de `md` (seção
  9) — a faixa de `MetricCard`s (seção 10) já usa `grid-cols-2` em telas pequenas (mesmo grid
  responsivo de `IndicadoresStrip`, confirmado lendo o componente).

## 15. Performance

- `useCartoes` com `placeholderData: keepPreviousData` desde o primeiro commit (mesmo
  tratamento que Tag já recebeu, não uma correção posterior).
- Indicadores agregados (seção 10) são `reduce` sobre um array pequeno (um usuário não tem
  dezenas de cartões na prática) — sem necessidade de memoização além de um `useMemo` simples
  dependente de `cartoes`.
- Nenhuma requisição nova: `AccountSelect` reaproveita `useContas` (já em cache se o usuário
  já visitou `/contas` nesta sessão — React Query dedup automático).

## 16. `/dev` — laboratório visual

Nenhuma rota nova necessária. `CartaoVisual`/`BandeiraBadge`/`AccountSelect` podem ganhar uma
seção de demonstração em `/dev/forms` (mesmo padrão de `ColorField`/`IconField` quando
foram criados na F7) — decisão de conveniência para desenvolvimento, não estrutural.

## 17. Fora de escopo

- `CardSelect` (`domain/cartao/CardSelect.tsx`) — nasce quando Transação for implementada
  (mesma decisão de `TagSelect`).
- Slot de ícone/badge por opção dentro de `SearchSelect`/`Select` genérico (seção 7) — melhoria
  de infraestrutura futura, não decidida isoladamente aqui.
- Qualquer tela de Fatura (extrato do ciclo, fechar fatura, pagar fatura) — entidade própria,
  fora desta etapa.
- Gráfico de evolução de limite utilizado ao longo do tempo — precisaria de histórico de
  Fatura, que não existe no frontend ainda.

## 18. Revisão crítica de UX — checklist pedido

Respondendo item a item ao que foi pedido para esta análise:

- **Visual dos cartões**: `CartaoVisual` (seção 9), reaproveitado na coluna da tabela, no card
  mobile (automático) e no preview do formulário — três lugares, um componente só.
- **Identificação visual do banco**: `InstitutionBadge`, já existente, zero trabalho novo.
- **Identificação da bandeira**: `BandeiraBadge`/`lib/bandeiras.ts` (seção 8), novo mas
  pequeno, espelha `institutions.ts`.
- **Limite utilizado / limite disponível**: `limite_disponivel` vem pronto do backend;
  `limite_utilizado` é `limite - limite_disponivel`, derivado no frontend só para exibição.
  Ambos os números aparecem (não só a barra) — número exato sempre disponível, a barra é
  reforço visual, nunca o único canal (design-system.md, seção 23: "nenhuma informação
  comunicada só por cor").
- **Progresso do limite**: `ProgressBar` já existente, cor reage a proximidade do limite
  (normal/warning/negative) usando só tokens semânticos já existentes.
- **Indicadores rápidos**: faixa de `MetricCard` no topo da página (seção 10) — primeira
  página de entidade a ter isso, justificado pela natureza agregável do limite.
- **Filtros**: por bandeira (`FilterDef`, mesmo mecanismo de Conta).
- **Pesquisa**: nome + instituição + últimos 4 dígitos.
- **Feedback visual**: toasts genéricos já existentes, 409/404 tratados sem código novo.
- **Animações**: zero timing novo, tudo reaproveitado de `lib/motion.ts` (seção 13).
- **Consistência com o restante do sistema**: mesma estrutura de página de Conta/Categoria/Tag
  (título + botão + switch "mostrar inativas" + `DataTable` + `FormDialog` + `ConfirmAction`),
  só com a faixa de indicadores extra no topo — nenhuma divergência de padrão visual/motion/
  espaçamento.
- **Mobile**: card do `DataTable` já reformata automaticamente; indicadores em grid responsivo;
  nenhum componente teve que ser desenhado duas vezes (desktop/mobile).
- **Performance**: nenhuma requisição nova, `keepPreviousData` desde o início, cálculos
  agregados são `reduce` simples sobre lista já em cache.

## 19. Critérios de pronto

- `tsc -b` e `vite build` limpos.
- Smoke test real contra backend descartável: criar cartão (com conta de pagamento própria),
  tentar criar outro com mesmo nome ativo (409), desativar, criar de novo com o mesmo nome
  (reativação implícita, campos sobrescritos), reativar explicitamente via `PATCH
  {ativo:true}`, editar renomeando para um nome já em uso por outro cartão ativo (409),
  listar com `apenas_ativos=true/false`.
- `limite_disponivel` exibido corretamente inclusive quando negativo (cartão "estourado" —
  precisa de uma transação de teste ligada ao cartão para simular; se não houver Transação
  implementada ainda, validar ao menos que a UI não quebra com um valor negativo simulado
  manualmente contra a API).
- Indicadores da página batem com a soma manual dos cartões listados.
- Filtro por bandeira e busca por últimos 4 dígitos funcionam.
- Formulário: `AccountSelect` só lista contas ativas do próprio usuário; campos
  `dia_fechamento`/`dia_vencimento` lado a lado (duas colunas).

## 20. Próximos passos

Aguardando aprovação. Se aprovado, implementação segue esta ordem:

1. `lib/bandeiras.ts` + `components/ui/BandeiraBadge.tsx`.
2. `components/domain/conta/AccountSelect.tsx`.
3. Camada de dados: `types/cartao.ts`, `schemas/cartao.ts`, `services/cartaoService.ts`,
   `queryKeys.cartoes`, `hooks/useCartaoQueries.ts`.
4. `components/domain/cartao/CartaoVisual.tsx`, `cartaoTableColumns.tsx`,
   `CartaoFormDialog.tsx`.
5. `pages/cartoes/CartoesPage.tsx` (com faixa de indicadores) + rota `/cartoes` + item de
   navegação (`navItems.ts` — participa automaticamente da Organização da Sidebar, sem
   nenhuma mudança extra, exatamente como Tag participou ao ser adicionada).
6. Validação: `tsc -b`, `vite build`, smoke test real, README, `docs/revisao-tecnica-cartao-frontend.md`.

Sem código escrito nesta etapa, conforme solicitado.
