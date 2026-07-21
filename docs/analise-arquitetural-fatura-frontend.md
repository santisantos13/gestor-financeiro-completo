# Análise Arquitetural — CRUD de Fatura (Etapa F10, frontend)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Quinta entidade real
do frontend (`Conta` → `Categoria` → `Tag` → `Cartão` → `Fatura`), seguindo a mesma convenção
de aprovação prévia de Conta/Categoria/Tag/Cartão. Lido em conjunto com
`docs/analise-arquitetural-rich-pickers.md`, `docs/analise-arquitetural-exclusao.md` e
`docs/analise-arquitetural-overlays.md` (os três entram antes ou junto desta etapa) — nenhum
dos três é reexplicado aqui; o `Drawer` em particular é especificado só em `overlays.md`
(seção 4.5) — este documento só descreve *como Fatura o usa*, não a mecânica do componente.

**Ajuste aprovado pelo usuário em relação à primeira versão deste documento**: a versão
original propunha um único `Drawer` "Gerenciar faturas" cobrindo a lista inteira (aberto a
partir de uma ação de linha em `/cartoes`). O usuário pediu explicitamente o contrário —
*"não quero que Fatura fique presa apenas a um Drawer. Quero que o Cartão evolua para uma
página de detalhes (`/cartoes/:id`), e as Faturas sejam exibidas nessa página, utilizando
Drawers apenas para as ações e detalhes de cada fatura"*. As seções 1 a 4 abaixo refletem essa
decisão final — a lista de faturas vive **na página**, inline, sempre visível; o `Drawer` é
usado só para **uma fatura por vez** (ações/detalhes), nunca para gerenciar a lista inteira.

## 0. Contrato real do backend (lido diretamente, não hipótese)

`app/api/routes/fatura.py`, `app/schemas/fatura.py`, `app/services/fatura_service.py`,
`app/repositories/fatura_repository.py` — sem nenhum PATCH genérico (diferente de toda
entidade anterior): datas/cartão são imutáveis por design, e as únicas transições de estado
viram endpoints de ação própria.

| Rota | Payload | Efeito |
|---|---|---|
| `POST /faturas` | `{cartao_id, mes_referencia}` | Cria um ciclo novo (`mes_referencia` precisa ser dia 1 do mês) — `data_fechamento`/`data_vencimento` são sempre derivadas, nunca aceitas do cliente |
| `GET /faturas?cartao_id=X` | — | Lista as faturas **de um cartão específico** — não existe "listar todas as faturas do usuário" nesta rota (isso é papel de `/central-financeira/faturas`, seção 1) |
| `GET /faturas/{id}` | — | Detalhe de uma fatura |
| `POST /faturas/{id}/fechar` | — | ABERTA → FECHADA, congela `valor_total` |
| `POST /faturas/{id}/pagamentos` | `{valor, data, descricao?}` | Registra pagamento (parcial ou total, pode ser chamado várias vezes) — só permitido se não estiver ABERTA |
| `DELETE /faturas/{id}` | — | Hard delete real (Fatura nunca teve soft delete) — só se ABERTA e sem nenhuma transação vinculada |

`FaturaRead`: `id`, `cartao_id`, `mes_referencia`, `data_fechamento`, `data_vencimento`,
`valor_pago`, `valor_total` (sempre calculado), `status` (`ABERTA`/`FECHADA`/
`PARCIALMENTE_PAGA`/`PAGA`/`ATRASADA` — `FinancialBadge` já sabe resolver as cinco, nenhuma
mudança necessária ali).

## 1. Decisão de IA: Fatura não é uma página de topo, vive dentro da página de detalhes do Cartão

Diferente de Conta/Categoria/Tag/Cartão (cada uma com sua própria rota `/entidade` e item de
navegação), Fatura **não tem uma rota própria no menu**. Motivo, direto do contrato:
`GET /faturas` exige `cartao_id` — não existe "ver todas as minhas faturas" nesta API (só
existe agregado, somente-leitura, via `/central-financeira/faturas`, já consumido pelo
`FaturasCard` do Dashboard). Uma página `/faturas` no menu principal não teria o que listar
sem primeiro escolher um cartão — a mesma pergunta que motivou o `CardSelect` a ficar adiado
(`docs/analise-arquitetural-frontend.md`) se resolve aqui de outra forma: **Fatura se
gerencia a partir do cartão dono dela**, nunca isolada.

Isso também significa que **nenhum novo Picker nasce para esta etapa**: `cartao_id` nunca é
escolhido por dropdown — já está implícito no contexto (o usuário já está vendo um cartão
específico quando cria/gerencia suas faturas). `docs/analise-arquitetural-rich-pickers.md`
não precisa de nenhuma adição para Fatura.

"A partir do cartão dono dela" deixa de significar "dentro do `FormDialog` de edição do
cartão" ou "num Drawer que lista tudo" (ambas descartadas, seção 2) e passa a significar:
**Cartão ganha uma página de detalhes própria, `/cartoes/:id`, e é lá que as faturas vivem**.

## 2. Onde a UI nasce: página de detalhes do Cartão (não um Drawer de lista)

Nos ajustes de UX/UI que precederam esta etapa (revisão de ponto 4, "Cartões parece só um
cadastro"), `CartaoFormDialog` ganhou `FaturasDoCartao` — um mini-painel somente leitura
(últimas 3 faturas, sem ação nenhuma) dentro da visualização de um cartão. Esse painel nasceu
deliberadamente pequeno porque, na época, criar/fechar/pagar fatura ainda não existia no
frontend.

Aplicando a heurística de `docs/analise-arquitetural-overlays.md` (seção 3): gerenciar
faturas de um cartão (ver histórico completo, criar uma nova, fechar um ciclo, registrar
pagamento parcial, excluir uma fatura vazia) é mais do que um mini-painel de 3 itens sem ação
suporta — mas a conclusão **não** é empurrar tudo isso para dentro de um único overlay. A
lista de faturas é, por si, um conteúdo primário o suficiente (histórico financeiro de um
cartão, potencialmente 12+ ciclos) para merecer uma página — não um painel secundário escondido
atrás de um clique extra. Decisão final (ajuste pedido pelo usuário sobre a primeira versão
deste documento, que ainda propunha um Drawer único de lista):

- **`Cartão` ganha uma página de detalhes, rota `/cartoes/:id`** — primeira entidade do
  projeto com página de detalhes própria (todas as outras usam só `FormDialog` para
  visualizar/editar). Aberta por uma nova ação de linha em `/cartoes` (`Eye`/`ArrowUpRight` do
  `lucide-react`, "Ver detalhes", ao lado de Editar/Desativar/Excluir) — ou clicando no próprio
  `CartaoVisual` da listagem.
- **A lista de faturas do cartão fica inline nessa página**, sempre visível, sem precisar
  abrir nada para vê-la — substitui o `FaturasDoCartao` de 3 itens do `CartaoFormDialog` (que é
  removido, seção 8) por uma seção completa da própria página.
- **`Drawer`** (`docs/analise-arquitetural-overlays.md`, seção 4.5) é usado só para **uma
  fatura por vez** — ações e detalhes de uma fatura específica (fechar, pagar, excluir, ver
  detalhe expandido) abrem ancorados àquela linha da lista, nunca um Drawer que gerencia a
  lista inteira. Isso é consistente com a regra de tier 2 de `overlays.md` (só um por vez) e
  com o motivo de existir um Drawer: "detalhes/ações de um item dentro do contexto de uma
  página maior" (`overlays.md`, seção 3, item 4) — aqui a "página maior" é literalmente a nova
  página de detalhes do Cartão, não mais uma linha de tabela em `/cartoes`.

## 3. `Drawer` de fatura individual — o que abre, o que não abre

A mecânica do `Drawer` (superfície, animação, foco, regra de tier 2) é 100% a de
`docs/analise-arquitetural-overlays.md`, seção 4.5 — não repetida aqui. Esta seção descreve só
o que é específico do consumo por Fatura:

- **Escopo sempre uma fatura só** — o Drawer é aberto a partir de uma linha da lista inline
  (seção 4) e recebe o `id` daquela fatura; fechar o Drawer e abrir outra linha troca o
  conteúdo, nunca acumula múltiplas faturas na mesma sessão de Drawer aberto.
- **"Nova fatura" não abre um Drawer** — criar uma fatura não tem "detalhes de item existente"
  para mostrar; é um mini-formulário inline na própria página (seção 4), coerente com a
  heurística de `overlays.md` seção 3 (a criação é uma ação curta de poucos campos, não precisa
  do espaço de um Drawer).
- Depois de implementado, este consumo entra em `docs/design-system.md` (seção 15) como
  exemplo de uso do `Drawer` (o componente em si já está documentado em `overlays.md`).

## 4. Conteúdo da página de detalhes do Cartão (`/cartoes/:id`)

- **Cabeçalho da página**: `CartaoVisual` completo (não a versão compacta usada em listagem),
  nome/instituição/bandeira, métricas já existentes (limite disponível, utilização — mesmos
  dados de `CartoesCard`/`CartaoFormDialog` hoje).
- **Seção "Faturas" inline, sempre visível** (substitui `FaturasDoCartao` de 3 itens) — lista
  completa (não mais limitada a 3), `mes_referencia` formatado (`nomeMes`/ano, já existe em
  `utils/date.ts`), `FinancialBadge` de status, `valor_total`/`valor_pago` (Geist Mono,
  tabular). Cada linha abre o `Drawer` de detalhes/ações daquela fatura ao ser clicada (seção
  3), sem precisar de um botão "ver mais" separado.
- **Botão "Nova fatura"** — mini-formulário inline na própria seção (não um `FormDialog`, não
  um `Drawer` — seção 3), um único campo: mês de referência (`DateField` restrito a dia 1, ou
  um seletor mês/ano dedicado — decisão de implementação). `cartao_id` já vem da rota
  (`/cartoes/:id`), nunca um campo do formulário.
- **Dentro do `Drawer` de uma fatura** (aberto ao clicar numa linha):
  - Detalhe completo: `mes_referencia`, datas de fechamento/vencimento, `valor_total`/
    `valor_pago`, status.
  - **Ação "Fechar ciclo"** — só visível quando `status === "ABERTA"`, sem formulário (POST
    sem payload), confirmação leve (`ConfirmAction`, "Fechar esta fatura congela o valor
    total. Confirma?").
  - **Ação "Registrar pagamento"** — só visível quando `status !== "ABERTA"`, formulário com
    `valor` (`CurrencyField`), `data` (`DateField`), `descricao` (opcional, `TextField`) —
    dentro do próprio Drawer, sem abrir um segundo overlay (regra de tier 2 de `overlays.md`).
  - **Ação "Excluir"** — sempre oferecida (mesma filosofia de
    `docs/analise-arquitetural-exclusao.md`, seção 3: nunca pré-calculada no cliente), backend
    responde 422 se não for `ABERTA` ou tiver transação vinculada, mensagem exata do
    `BusinessRuleError` já existente em `FaturaService.excluir()` vira o toast; ao confirmar
    exclusão, o Drawer fecha e a lista inline é invalidada.
- **Estado vazio**: `EmptyState` padrão ("Nenhuma fatura ainda" + botão "Nova fatura") quando a
  lista está vazia — mesmo componente de sempre.

## 5. Camada de dados

Mesmo molde de Cartão (F9): `types/fatura.ts` (`FaturaRead`/`FaturaCreate`/
`FaturaPagamentoCreate`, espelhando `app/schemas/fatura.py` 1:1), `schemas/fatura.ts` (Zod só
de formato — `mes_referencia` dia 1, `valor`/`data`/`descricao` do pagamento), `services/faturaService.ts`,
`queryKeys.faturas(cartaoId)` (a chave inclui `cartaoId`, já que a listagem é sempre escopada a
um cartão — nunca uma chave global `faturas.all`), `hooks/useFaturaQueries.ts`
(`useFaturas(cartaoId)`/`useCriarFatura`/`useFecharFatura`/`useRegistrarPagamento`/
`useExcluirFatura`). Invalidação toca `faturas(cartaoId)` **e** `dashboard.faturas`/
`dashboard.cartoes` (a Central Financeira agrega os mesmos dados — mesmo cuidado de
invalidação cruzada já aplicado em outras etapas quando duas partes do app leem a mesma
informação de fontes diferentes).

## 6. Sem PATCH — nenhum componente de edição genérica

Diferente de todo CRUD anterior, não existe `FaturaFormDialog` de editar campos livres — as
únicas "edições" são as ações de negócio da seção 4, cada uma com seu próprio botão/mini-form.
Isso é fiel ao próprio backend (`app/api/routes/fatura.py` já documenta essa decisão) — o
frontend não inventa um PATCH que o backend não tem.

## 7. Fora de escopo (explicitamente)

- Geração automática de próximos ciclos (rotina agendada) — já fora de escopo no backend
  (`docs/analise-arquitetural-fatura.md`), permanece fora aqui.
- Uma página `/faturas` independente no menu — decisão da seção 1, não revisitada.
- Qualquer Rich Picker novo — seção 1 já conclui que não é necessário.
- Um Drawer único gerenciando a lista inteira de faturas — descartado (seção 2); a lista é
  inline na página de detalhes, o Drawer é só por fatura individual.
- Histórico de transações na página/Drawer de Fatura — pertence à Etapa F11 (Transação); a
  página mostra só os dados que a própria Fatura já expõe (`valor_total`/`valor_pago`/status),
  nunca a lista de compras individuais que compõem esse total.
- Páginas de detalhes para as demais entidades (Conta/Categoria/Tag) — Cartão é o primeiro e
  único caso desta etapa; se fizer sentido para outra entidade no futuro, é decisão de uma
  etapa própria, não uma extensão automática deste documento.

## 8. Ordem de implementação sugerida

Depois de Rich Pickers e Exclusão (ambos tocam entidades já existentes, sem dependência desta
etapa) e da infraestrutura de overlay (`docs/analise-arquitetural-overlays.md`):

1. `Drawer` genérico (`components/ui/Drawer.tsx`), conforme `overlays.md` seção 4.5.
2. Camada de dados de Fatura (seção 5).
3. Página de detalhes do Cartão — rota `/cartoes/:id`, `components/pages/CartaoDetalhePage.tsx`
   (ou equivalente), com cabeçalho + seção "Faturas" inline (seção 4).
4. `FaturaDrawer` (`components/domain/fatura/`) — Drawer de uma fatura, com detalhe + ações
   (fechar/pagar/excluir) da seção 4.
5. Nova `RowAction`/clique no `CartaoVisual` em `CartoesPage` navegando para `/cartoes/:id`.
6. Remover `FaturasDoCartao` de dentro do `CartaoFormDialog` (a versão de 3 itens fica
   redundante com a página de detalhes — evita duas UIs mostrando a mesma coisa).
7. `tsc -b`/`vite build` + smoke test real: criar fatura, fechar, pagar parcial, pagar total,
   tentar excluir fatura fechada (deve bloquear), excluir fatura aberta vazia (deve permitir).
8. Atualizar `docs/design-system.md` (seção 15, `Drawer` + página de detalhes) e README.

## 9. Critérios de pronto

- Fatura gerenciada inteiramente a partir da página de detalhes do cartão dono dela, sem
  página própria no menu.
- `/cartoes/:id` exibe a lista de faturas inline, sempre visível, sem exigir abrir nenhum
  overlay para vê-la.
- `Drawer` de fatura individual funciona com teclado (`Esc`, focus trap),
  `prefers-reduced-motion` respeitado — mesma verificação já exigida em `overlays.md`.
- As quatro ações de negócio (criar, fechar, pagar, excluir) refletem exatamente as regras já
  existentes no backend, sem duplicar validação de negócio no frontend.
- `tsc -b`/`vite build` limpos, smoke test contra backend real.

## 10. Próximos passos

Aprovado pelo usuário, com o ajuste de IA registrado no topo deste documento (página de
detalhes do Cartão + Drawer por fatura individual, em vez de um Drawer único de lista) — junto
com `docs/analise-arquitetural-rich-pickers.md`, `docs/analise-arquitetural-exclusao.md` e
`docs/analise-arquitetural-overlays.md`, fecha o pacote de preparação da Etapa F10. Próximo
passo: implementação, seguindo a ordem da seção 8.
