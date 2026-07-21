# Análise Arquitetural — Rich Pickers (Design System)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Responde a um
adendo de UX do usuário, feito durante a preparação da Etapa F10 (CRUD de Fatura): "alguns
componentes de seleção já começam a ficar pequenos e difíceis de usar conforme o sistema
cresce" — pedido explícito para **não corrigir só a tela de Categoria**, e sim estabelecer um
padrão reutilizável, oficial do Design System, para qualquer seleção visual do projeto daqui
em diante. Segue a mesma convenção de todo documento de arquitetura: aprovado antes de
qualquer implementação.

Este documento é irmão de `docs/analise-arquitetural-fatura-frontend.md` (Etapa F10), mas
trata de infraestrutura **cross-cutting** — não pertence a nenhuma entidade específica, por
isso ganha documento próprio, mesmo padrão já usado para `docs/analise-arquitetural-organizacao-sidebar.md`
(outra peça de UX que atravessa o projeto inteiro em vez de nascer dentro de um CRUD).

## 0. Diagnóstico — o que existe hoje, e por que ficou pequeno

Levantamento direto do código (não hipótese) de todo componente de "escolher algo visual" já
implementado:

| Componente | Onde vive | Formato atual | Problema |
|---|---|---|---|
| `IconField` | `components/ui/IconField.tsx`, usado por `CategoriaFormDialog` | Popover fixo `w-72` (≈345px após `--ui-scale`), grid de 6 colunas, **59 ícones**, sem busca, sem categoria visível (o registry já tem grupos nos comentários — "Moradia", "Transporte" — mas nunca chegam à UI) | Grid de 6×10 é alto e sem busca; achar "Cinema" entre 59 ícones exige rolar e ler um por um |
| `ColorField` | `components/ui/ColorField.tsx`, usado por `CategoriaFormDialog`/`TagFormDialog` | Popover `w-72`, `flex-wrap` de **43 swatches** de 28px, `max-h-56` com scroll, sem busca, sem grupo visível (mesma situação: grupos de matiz existem só em comentário) | Mesma limitação — 43 bolinhas pequenas coladas, nenhuma forma de pular direto para "a família do verde" |
| `SelectField` (bandeira) | `CartaoFormDialog`, via `BANDEIRA_OPTIONS` | `Select` de texto puro (nenhuma cor/logo por opção) | Nenhuma riqueza visual — bandeira é uma marca (cor real conhecida, `lib/bandeiras.ts`), mas a lista mostra só a palavra "Visa"/"Mastercard" |
| Instituição financeira | `TextField` livre em `ContaFormDialog`/`CartaoFormDialog` | Texto livre, sem nenhum picker — `InstitutionBadge` só decora o texto **depois** de digitado | Nem chega a ser um "picker pequeno": não existe seleção nenhuma hoje, só digitação livre torcendo para o nome bater com um dos 17 aliases de `lib/institutions.ts` |
| `SearchSelect` (base de `CategorySelect`/`AccountSelect`, e da futura `CardSelect`/`TagSelect`) | `components/ui/SearchSelect.tsx` | Combobox com busca client-side, **mas cada opção é só `{value, label}` — texto puro**, nenhum slot de ícone/cor | Categoria já tem ícone e cor cadastrados (`CategoryBadge` os mostra na tabela) — mas o próprio seletor de categoria não os usa, obrigando o usuário a reconhecer a categoria só pelo nome |

Conclusão do diagnóstico: existem **dois problemas diferentes**, não um só, e cada um pede uma
solução diferente (seção 1 explica por quê):

1. **Popover pequeno demais para um conjunto fixo e grande de itens visuais** (ícone, cor,
   instituição, bandeira) — o problema é a forma do picker em si.
2. **Lista com busca correta, mas sem riqueza visual por item** (categoria, e a futura tag) —
   o problema não é a forma (busca-enquanto-digita já é o padrão certo para uma lista que
   cresce com o uso, ex. dezenas de categorias), é a ausência de ícone/cor na opção.

## 1. Decisão central: nem tudo vira o mesmo componente

O pedido do usuário lista categoria e tag lado a lado com ícone/cor/instituição/bandeira como
candidatos a "Rich Picker". Avaliado caso a caso (exatamente como pedido — "avalie se faz mais
sentido"), a decisão **não** é tratar os seis exemplos da mesma forma:

- **Conjunto fixo, pequeno-a-médio, curado pelo projeto** (ícones ~59, cores ~43, instituições
  ~17, bandeiras 7): vira o novo componente `RichPicker` (seção 2) — popover/dialog maior,
  busca, grupos, grid, preview, animação. Cardinalidade conhecida de antemão, cabe
  inteiramente em memória, nunca precisa de paginação.
- **Lista aberta, específica do usuário, que cresce com o uso** (categorias, e a futura tag):
  **continua sendo `SearchSelect`** — busca-enquanto-digita já é a UX certa para uma lista que
  pode ter dezenas de itens criados pelo próprio usuário (um grid visual grande não escala
  bem aqui, e obrigaria rolar uma área maior em vez de digitar 3 letras). O que muda é dar a
  `SearchSelect` um **slot visual por opção** (ícone/cor), corrigindo a ausência de riqueza
  sem trocar a forma do componente. Ver seção 5.

Esta distinção é o próprio "avalie a melhor UX" pedido — tratar os seis casos como um único
componente seria a solução mais fácil de descrever, mas errada para pelo menos dois deles.

## 1.1 Heurística geral de decisão — ver `docs/analise-arquitetural-overlays.md`

O adendo do usuário sobre "mais de 2 cliques, ou o espaço fica comprometido → avaliar
Popover/Dialog/Drawer/Command Palette" é uma regra permanente do Design System, não específica
de Rich Pickers — por isso foi movida para o documento canônico de overlays,
`docs/analise-arquitetural-overlays.md` (seção 3), que também define a relação de tiers entre
os overlays e evita esta regra ficar duplicada (e potencialmente divergente) em cada documento
de entidade/feature que precisar dela. A decisão da seção 1 acima (por que
ícone/cor/instituição/bandeira viram `RichPicker`, mas categoria/tag continuam `SearchSelect`)
é a aplicação concreta dessa heurística a este caso específico.

## 2. `RichPicker` — o componente base reutilizável

Novo componente de `components/ui/`, generic sobre o tipo do valor (`T`), sem nenhum
conhecimento de ícone/cor/instituição/bandeira específico — mesmo espírito de `SearchSelect`
(que não sabe nada de Categoria/Conta) e de `DataTable`/`FormDialog` (infraestrutura genérica
consumida por composição). API proposta:

```ts
interface RichPickerItem<T> {
  value: T;
  label: string;
  /** O que renderizar no grid/lista — ícone, swatch de cor, monograma de
   * instituição, o que fizer sentido para o registry que está usando o
   * picker. O componente base não sabe o que é isso, só posiciona. */
  render: ReactNode;
  /** Grupo opcional (ex. "Moradia", "Vermelho") — quando presente em pelo
   * menos um item, o picker organiza em seções com cabeçalho; quando
   * ausente em todos, vira uma grade/lista única sem seção. */
  group?: string;
  /** Termos extras de busca além do label (ex. aliases de instituição). */
  keywords?: string[];
}

interface RichPickerProps<T> {
  value: T | null;
  onChange: (value: T) => void;
  items: RichPickerItem<T>[];
  layout: "grid" | "list"; // grid para ícone/cor (swatch puro), list para instituição/bandeira (monograma + nome legível)
  placeholder: string;
  searchPlaceholder?: string;
  /** Abaixo deste número de itens, a busca nem aparece — não faz sentido
   * pedir para "buscar" entre 7 bandeiras. Default: 10. */
  searchThreshold?: number;
  /** Preview maior no topo do painel (ex. swatch grande + hex do
   * ColorPicker) — opcional, cada consumidor decide se precisa. */
  renderPreview?: (item: RichPickerItem<T> | null) => ReactNode;
  disabled?: boolean;
  "aria-label"?: string;
}
```

Comportamento (segue `docs/design-system.md` e `docs/motion-principles.md` à risca — mesmo
nível de acabamento dos demais componentes compostos, nenhuma exceção):

- **Popover maior**: `w-80` a `w-96` (contra o `w-72` atual), `max-h-96` com scroll interno —
  nunca um popover que ultrapassa a viewport (mesma regra de `max-w-[90vw]` já usada, mantida).
- **Busca client-side instantânea** (mesmo padrão de `SearchSelect`: `useDeferredValue`, sem
  debounce de rede — todo o registry já está em memória), some com `< searchThreshold` itens.
- **Grupos**: quando o registry declara `group`, o picker renderiza um cabeçalho de seção
  (`--text-caption`, `--color-text-tertiary`, mesmo tratamento de rótulo secundário do resto
  do sistema) antes de cada grupo — os itens dentro do grupo respeitam o filtro de busca
  (grupo que fica vazio após o filtro desaparece inteiro).
- **Grid (ícone/cor)**: células quadradas com `hover:scale-110` (mesmo padrão já usado no
  swatch de cor hoje) + `transition-colors`/`transition-transform` `--duration-fast`
  `--ease-out` — nada novo, reaproveita o hover que já existe em `ColorField`.
- **List (instituição/bandeira)**: linha com o `render` (monograma) à esquerda + label +
  indicador de selecionado (`Check`, mesmo ícone/posição de `ColorField` hoje) à direita.
- **Navegação por teclado**: `ArrowUp`/`ArrowDown`/`ArrowLeft`/`ArrowRight` movem o foco dentro
  do grid/lista (calculado a partir do layout — grid usa as 4 setas, list só cima/baixo),
  `Enter` seleciona o item focado, `Esc` fecha — evolução real sobre `IconField`/`ColorField`
  hoje (que só fecham com `Esc`/clique-fora, sem navegação por seta nenhuma). Reforça o
  princípio "teclado em primeiro lugar" (`docs/design-system.md`, seção 3) que já é
  não-negociável no projeto e que os pickers atuais não cumprem.
- **Preview do selecionado**: já existe parcialmente hoje (o botão-gatilho mostra o ícone/cor
  atual) — mantido e, quando `renderPreview` é passado, ganha uma área maior no topo do
  próprio painel (ex. `ColorPicker` mostra um swatch grande + hex por extenso antes da grade).
- **Fechamento**: `Esc`, clique fora, `Enter` sobre um item, ou clicar o próprio item — mesma
  mecânica de hoje, sem mudança.
- **Responsivo**: abaixo de `md`, o `RichPicker` reaproveita o `Dialog` (`FormDialog`) como
  shell em vez do popover ancorado — evita um popover cortado nas bordas de uma tela de
  celular, sem introduzir um terceiro padrão de overlay (bottom-sheet) sem outro consumidor no
  projeto; mesmo raciocínio de tiers de `docs/analise-arquitetural-overlays.md` (seção 2): o
  `RichPicker` é sempre tier 1, mas no breakpoint mobile pega emprestada a superfície de um
  overlay tier 2 já existente.
- **Motion**: entrada/saída idêntica ao popover atual (`fade + 4px slide`, `--duration-base`/
  `--ease-out` na entrada, `--duration-fast`/`--ease-in` na saída) — já correto hoje, mantido
  sem mudança. A troca para `FormDialog` no breakpoint mobile herda a entrada de modal
  (`scale(0.96→1) + fade`, spring `smooth`) automaticamente, por composição.
- **Acessibilidade**: `role="listbox"`/`role="option"` (grid) ou `role="listbox"`/`role="option"`
  (list, igual), `aria-selected`, `aria-label` no painel — mesmo tratamento que `IconField`/
  `ColorField`/`SearchSelect` já cumprem hoje, preservado.

## 3. `IconPicker` e `ColorPicker` — evolução direta de `IconField`/`ColorField`

Decisão de nomenclatura: **`IconPicker`/`ColorPicker` substituem `IconField`/`ColorField`**
como os componentes de formulário (mesmo contrato de fora — `name`/`label`/`optional`/
`description`/`disabled`, wrapper de `Controller`/`FormField` idêntico ao que já existe) — por
dentro, compõem o novo `RichPicker` em vez de reimplementar popover/busca/grid do zero.
`IconField`/`ColorField` são removidos (nenhum outro consumidor além de `CategoriaFormDialog`/
`TagFormDialog`, ver grep já feito nesta análise), não mantidos como alias morto.

- **`lib/icons.ts`**: `IconInfo` ganha um campo `grupo: string` real (hoje só existe como
  comentário — "Moradia", "Transporte", "Alimentação", etc., já visíveis no arquivo atual,
  só formalizados em dado em vez de comentário). Nenhuma mudança de `id`/`label`/`Icon`
  existente — o valor salvo no backend (`Categoria.icone`, string livre) não muda.
- **`IconPicker`**: `layout="grid"`, busca por `label` (ex. digitar "cinema" já filtra),
  agrupado por `grupo`, preview no topo do painel opcional (o próprio botão-gatilho já mostra
  o ícone escolhido, suficiente aqui — sem uma segunda área de preview redundante).
- **`lib/color.ts`**: `PALETA_SUGESTAO` deixa de ser `readonly string[]` e vira
  `{ cor: string; grupo: string }[]` (grupo = "Vermelho"/"Laranja"/.../"Marca", já visível nos
  comentários atuais). `eCorHexValida`/`corDeContraste` inalterados.
- **`ColorPicker`**: `layout="grid"`, agrupado por `grupo`, **mantém o input de hex livre ao
  lado do gatilho** (não é substituído pelo picker — o usuário que já sabe o hex exato de uma
  cor continua podendo digitá-lo direto, mesmo comportamento de hoje). Busca é opcional aqui:
  como os "labels" seriam nomes de família de cor (não um texto natural por item individual),
  a busca filtra por `grupo` (digitar "verde" restringe à família verde) — filtro mais simples
  que o de ícone, mas ainda útil com 43 itens.

## 4. `BankPicker` e `CardBrandPicker` — pickers novos (nenhuma seleção existia antes)

Diferente de ícone/cor, estes dois **não têm um componente de formulário anterior para
evoluir** — instituição é texto livre hoje, bandeira é um `Select` de texto puro. São os dois
casos onde o ganho de UX é maior (de "nenhuma seleção visual" para uma completa).

- **`BankPicker`** (`components/domain/*` ou `components/ui/`? decisão: `components/ui/`,
  porque não pertence a nenhuma entidade — Conta e Cartão consomem o mesmo registry): consome
  `lib/institutions.ts` (`TODAS_INSTITUICOES_CONHECIDAS`), `layout="list"` (monograma sobre a
  cor de marca real + nome — o mesmo visual de `InstitutionBadge`, só dentro do picker em vez
  de só na exibição), busca por `nome`/`aliases`. **Ponto crítico de compatibilidade**: o
  backend aceita qualquer string livre em `instituicao` (`Conta`/`Cartão`), então o picker
  **não pode virar uma lista fechada** — precisa de uma opção final "Outra (digitar nome)" que
  revela um `TextField` inline, preservando exatamente a liberdade que o campo já tem hoje.
  Sem essa opção, o picker regrediria a experiência de quem usa um banco fora da lista de 17
  conhecidos. Substitui o `TextField` de instituição em `ContaFormDialog`/`CartaoFormDialog`.
- **`CardBrandPicker`** (`components/ui/`): consome `lib/bandeiras.ts` (`Bandeira` é enum
  FECHADO — diferente de instituição, aqui uma lista fechada é o comportamento correto e já é
  o que `SelectField` faz hoje, só sem riqueza visual). `layout="list"`, sem busca (7 itens,
  abaixo do `searchThreshold`), cada linha com o monograma sobre a cor de marca real
  (`BandeiraBadge` já faz isso na exibição — o picker reaproveita a mesma resolução via
  `resolveBandeira`). Substitui o `SelectField`/`BANDEIRA_OPTIONS` em `CartaoFormDialog`.

## 5. Categoria e Tag — `SearchSelect` ganha riqueza visual, não uma nova forma

Conforme a decisão da seção 1: `SearchSelect`/`SelectOption` ganham um campo opcional:

```ts
interface SelectOption {
  value: string;
  label: string;
  /** Novo — opcional. Quando presente, renderizado à esquerda do label,
   * tanto no botão-gatilho (quando selecionado) quanto em cada linha da
   * lista. `undefined` mantém o comportamento de hoje (texto puro),
   * nenhum consumidor existente quebra. */
  render?: ReactNode;
}
```

- **`CategorySelect`**: cada opção passa a montar `render` a partir de `resolveIconInfo(categoria.icone)`
  + o próprio `categoria.cor` (mesmo par ícone+cor que `CategoryBadge` já usa na tabela) — a
  cadeia de ancestrais (`"Moradia > Aluguel"`) continua sendo o `label`, texto de busca
  inalterado. Zero mudança de comportamento de busca/seleção, só a linha fica visualmente
  idêntica à de `CategoryBadge`.
- **`TagSelect`** (ainda não construído — nasce quando `Transação` precisar dele, decisão já
  registrada em `docs/revisao-tecnica-tag-frontend.md`): já nasce, quando for construído, sobre
  o `SearchSelect` enriquecido — sem nenhum trabalho extra além do `TagBadge` que já existe.
- **`AccountSelect`**: revisado e mantido como está — conta não tem ícone/cor próprios no
  model (só `instituicao`, que já ficará mais rico quando `BankPicker` existir). Não é um
  retrabalho pendente: se o usuário quiser o badge de instituição também dentro do
  `AccountSelect` no futuro, é uma composição trivial de `render` sobre o mesmo mecanismo —
  não implementado agora por não ter sido pedido explicitamente.

## 6. Auditoria — outros candidatos revisados, nenhum outro urgente

Pedido explícito do adendo: procurar qualquer outro componente "apertado" antes de encerrar.
Revisados:

- **`VariantePicker`** (`CartaoFormDialog`, seletor de variante visual do tema do cartão) — é
  uma fileira de círculos pequenos (`h-8 w-8`), mesma forma de swatch de cor. Não é um
  candidato urgente: no máximo 2-3 variantes por instituição hoje (`lib/cardThemes.ts`), uma
  fileira curta continua legível. Registrado aqui para reavaliação **só se** o número de
  variantes por instituição crescer o bastante para justificar o mesmo tratamento de
  `ColorPicker` — não implementado agora (evita retrabalho especulativo).
- **`MultiSelectField`** (seleção múltipla genérica, sem consumidor de domínio ainda — nasce
  com `tag_ids` em Transação) — texto puro como `SearchSelect` de hoje, mesmo raciocínio da
  seção 5: quando `TagSelect`/multi-tag nascer, herda o mesmo `render` opcional de
  `SelectOption`. Nenhuma mudança necessária agora, nada para corrigir hoje (não existe
  consumidor real ainda).
- **`Select`/`SelectField` genérico** (base de `SelectField`, usado por campos de enum curto —
  ex. `tipo` de Conta, `bandeira` hoje) — revisado: continua correto para enums pequenos sem
  identidade visual própria (ex. `tipo` de Conta: "Corrente"/"Poupança"/"Carteira"/
  "Investimento", nenhum tem cor/ícone de marca real). `bandeira` é a exceção que já vira
  `CardBrandPicker` (seção 4) porque tem cor de marca real; os demais consumidores de
  `SelectField` ficam como estão.

Nenhum outro componente do projeto foi encontrado com o mesmo padrão de "lista pequena demais
para o que precisa mostrar" além dos já listados nas seções 3-4.

## 7. Onde isso entra no Design System

Após implementado, `RichPicker`/`IconPicker`/`ColorPicker`/`BankPicker`/`CardBrandPicker`
passam a ser especificados em `docs/design-system.md` (seção 15, junto de `CategorySelect`/
`AccountSelect`/`CardSelect`/`TagSelect`) com o mesmo nível de detalhe de qualquer componente
composto existente — atualização a ser feita durante a implementação (Etapa F10), não neste
documento de arquitetura. `docs/motion-principles.md` não precisa de nenhuma seção nova: toda
animação do `RichPicker` reaproveita tokens/padrões já existentes (seção 2 acima), nenhuma
duração/curva/spring nova é introduzida.

## 8. Ordem de implementação sugerida (dentro da Etapa F10)

1. `RichPicker` genérico (`components/ui/RichPicker.tsx`) + testes manuais via `/dev/forms`.
2. `lib/icons.ts`/`lib/color.ts`: adicionar `grupo` real aos registries existentes.
3. `IconPicker`/`ColorPicker` (substituem `IconField`/`ColorField`) — atualizar
   `CategoriaFormDialog`/`TagFormDialog` para os novos nomes (mesmo contrato de fora).
4. `BankPicker` (`lib/institutions.ts`) — substituir `TextField` de instituição em
   `ContaFormDialog`/`CartaoFormDialog`, com a opção "Outra" preservando texto livre.
5. `CardBrandPicker` (`lib/bandeiras.ts`) — substituir `SelectField`/`BANDEIRA_OPTIONS` em
   `CartaoFormDialog`.
6. `SelectOption.render` opcional em `SearchSelect` + `CategorySelect` passando ícone/cor.
7. Atualizar `docs/design-system.md` (seção 15) e rodar `tsc -b`/`vite build` + smoke test dos
   três formulários afetados (Categoria, Tag, Conta, Cartão) antes de seguir para o CRUD de
   Fatura propriamente dito.

## 9. Fora de escopo (explicitamente, para não crescer sozinho)

- Logotipos SVG reais de instituição/bandeira — decisão de direitos de marca já tomada em
  `docs/revisao-tecnica-branding-e-microinteracoes.md`, inalterada; o monograma sobre cor real
  continua sendo a solução (o `RichPicker` só melhora a moldura ao redor dele, não o dado).
  Se um dia entrarem SVGs reais, o ponto de extensão é `InstitutionInfo`/`BandeiraInfo`
  (adicionar `Logo`/`logoUrl`), já documentado em `lib/institutions.ts` — sem tocar nos
  pickers.
- Seleção de emoji — citada como "caso existam futuramente" no pedido; não existe nenhum
  campo de emoji no backend hoje, então não há registry para alimentar um `EmojiPicker` ainda.
  Quando existir, é o mesmo `RichPicker` com um registry novo — nenhuma peça de arquitetura
  nova.
- Bottom-sheet dedicado — decisão da seção 2 já resolve mobile reaproveitando `FormDialog`.

## 10. Critérios de pronto

- `RichPicker` funciona com teclado completo (setas + Enter + Esc), `prefers-reduced-motion`
  respeitado, `focus-visible` correto — mesmo checklist de acessibilidade de
  `docs/motion-principles.md`, seção 8.
- `IconPicker`/`ColorPicker` mostram grupo + busca, sem nenhuma regressão de comportamento
  (mesmo valor salvo, mesma validação Zod).
- `BankPicker` preserva a liberdade de digitar uma instituição não listada.
- `CardBrandPicker` mostra a cor de marca real de cada bandeira.
- `CategorySelect` mostra ícone+cor por opção, mesma busca/seleção de hoje.
- `tsc -b` e `vite build` limpos, smoke test manual dos formulários afetados.

## 11. Próximos passos

Aprovado pelo usuário junto com `docs/analise-arquitetural-fatura-frontend.md`,
`docs/analise-arquitetural-exclusao.md` e `docs/analise-arquitetural-overlays.md` — os quatro
formam o pacote completo da Etapa F10. Ordem combinada: infraestrutura de overlay (`Drawer`,
consolidação do `Popover`) → Rich Pickers (seção 8 acima) → Exclusão → CRUD de Fatura (os
pickers não são um bloqueio técnico do CRUD de Fatura em si, mas o usuário pediu
explicitamente que a revisão aconteça "durante a implementação do CRUD de Fatura" — feita
antes, para que qualquer tela nova de Fatura já nasça usando os componentes corretos, sem
retrabalho). Próximo passo: implementação.
