# Análise arquitetural — bug crítico de limite de cartão não liberado

## 0. Pedido do usuário

Relato de bug crítico: "quando uma fatura é marcada como paga, o limite utilizado do cartão
NÃO é liberado corretamente" e "quando uma transação vinculada ao cartão é excluída (ou
desfeita), o limite utilizado também NÃO é recalculado corretamente". Pedido explícito:
investigar a **causa raiz** em toda a cadeia (Cartão, Fatura, Compra, Pagamento, Exclusão,
Cancelamento, React Query, Cache, Backend, Frontend), não aplicar um `if` pontual. Hipótese
do próprio usuário: "suspeito que o limite utilizado esteja sendo armazenado como um valor
persistido, quando o ideal seria ele ser derivado dos dados".

## 1. O que a investigação encontrou no BACKEND — já é 100% derivado

Leitura direta de `app/models/cartao.py`, `app/services/cartao_service.py`,
`app/repositories/cartao_repository.py` e `app/services/fatura_service.py` confirma que **não
existe nenhum campo `limite_utilizado` persistido** — nunca existiu nesta forma. `Cartao` só
guarda `limite` (o teto) e `saldo_inicial_utilizado` (o "estado inicial" declarado pelo
usuário, ver seção 2). `limite_disponivel` é um atributo **transiente**, calculado em toda
leitura por `CartaoService._com_limite_disponivel`:

```python
ids_faturas_pagas = self.fatura_service.ids_faturas_pagas(cartao.id)
gastos_nao_pagos = self.cartao_repo.somar_gastos_nao_pagos(cartao.id, ids_faturas_pagas)
cartao.limite_disponivel = cartao.limite - gastos_nao_pagos - cartao.saldo_inicial_utilizado
```

`somar_gastos_nao_pagos` é uma query `SUM` live sobre `Transacao`/`Fatura` (despesas do cartão
sem fatura OU cuja fatura ainda não é `PAGA`, mais `Fatura.ajuste_manual` de toda fatura não
paga) — nunca lê um contador incremental. `ids_faturas_pagas` deriva `status_calculado` de
cada fatura a partir de `valor_pago`/`valor_total`, nunca da coluna `Fatura.status` (que só
grava `ABERTA`/`FECHADA` de verdade). Ou seja: **pagar uma fatura, fechar um ciclo, excluir
uma transação de compra, cancelar um parcelamento — todos automaticamente mudam o resultado
desta soma na próxima leitura**, porque não há nenhum valor a "sincronizar" manualmente. A
suspeita do usuário (campo persistido desatualizado) não corresponde ao estado atual do
código — essa classe de bug já tinha sido corrigida numa etapa anterior deste mesmo projeto
(ver comentários "bug corrigido em 2026-07" espalhados por `cartao_repository.py`/
`fatura_service.py`/`transacao_service.py`, cobrindo exatamente os casos de pagamento de
fatura e exclusão de parcela de parcelamento).

Suíte de testes que cobre este comportamento (102 testes, todos passando antes de qualquer
mudança nesta etapa): `tests/integration/test_cartao_flow.py`,
`tests/integration/test_fatura_flow.py`, `tests/unit/test_cartao_service.py`.

## 2. Causa raiz real — gap de invalidação de cache no FRONTEND

O bug é real, mas mora inteiramente no React Query: a chave de cartão tem três ramos
(`frontend/src/api/queryKeys.ts`):

```ts
cartoes: {
  all: ["cartoes"],
  list: (apenasAtivas) => ["cartoes", "list", apenasAtivas],
  detail: (id) => ["cartoes", "detail", id],
}
```

`all` é PREFIXO de `list` e `detail` (`invalidateQueries` casa por prefixo) — mas `list` e
`detail` são **irmãos**, não pai/filho um do outro. Invalidar só `detail(id)` nunca re-busca
`list(...)`.

`useCartaoQueries.ts` (mutations que pertencem ao próprio Cartão — criar/atualizar/desativar/
excluir) sempre usa `queryKeys.cartoes.all`, cobrindo os dois ramos corretamente. Mas as duas
mutations que de fato **disparam os dois cenários relatados pelo usuário** — pagar fatura
(`useFaturaQueries.ts`) e excluir/editar/criar transação (`useTransacaoQueries.ts`) — foram
escritas de forma independente e invalidavam só `queryKeys.cartoes.detail(cartaoId)`:

- `useFaturaQueries.ts::useInvalidateFaturas` (usado por `useCriarFatura`, `useFecharFatura`,
  `useRegistrarPagamento`, `useAjustarSaldoInicialFatura`, `useExcluirFatura`,
  `useExcluirFaturasEmLote` — ou seja, TODAS as mutations de Fatura de uma vez, por
  compartilharem esta mesma função).
- `useTransacaoQueries.ts::invalidarTransacoes` (usado por `useCriarTransacao`,
  `useAtualizarTransacao`, `useExcluirTransacao` — TODAS as mutations de Transação).

Efeito prático: a página `/cartoes` (`CartoesPage.tsx`, via `useCartoes()` →
`queryKeys.cartoes.list(...)`) e o combobox de cartão em `/transacoes`
(`TransacoesPage.tsx`/`CardSelect`, mesmo hook) continuavam mostrando o `limite_disponivel`
de ANTES da ação, até um F5 manual ou a próxima vez que o React Query decidisse re-buscar por
conta própria (`staleTime`/refoco de aba). A página de detalhe do cartão
(`CartaoDetalhePage.tsx`, via `useCartao(id)` → `queryKeys.cartoes.detail(id)`) **já
atualizava corretamente**, porque `detail(cartaoId)` era exatamente a chave invalidada — isso
explica por que o problema parecia inconsistente/intermitente: dependia de qual tela o
usuário estava olhando no momento.

Confirmado por leitura de todos os call-sites (`grep` em `frontend/src`): `cartaoId`/`contaId`
sempre chegam corretos até essas duas funções de invalidação (`FaturaDrawer.tsx`,
`TransacaoFormDialog.tsx`, `TransacoesPage.tsx`) — o dado nunca esteve errado, só o alvo da
invalidação estava incompleto.

## 3. Correção — mesma causa raiz, ponto único por arquivo

Troca de `queryKeys.cartoes.detail(cartaoId)` por `queryKeys.cartoes.all` nos dois pontos
acima (`useInvalidateFaturas` em `useFaturaQueries.ts`, `invalidarTransacoes` em
`useTransacaoQueries.ts`) — mesmo padrão que `useCartaoQueries.ts`/`useContaQueries.ts` (linha
114, exclusão de Conta) já usavam. Não é um `if` novo: é alinhar as duas funções que faltavam
a uma convenção que já existia no projeto (invalidar pelo prefixo `all` sempre que a mutação
pode afetar qualquer visão — lista ou detalhe — da entidade). Nenhuma mudança de regra de
negócio, nenhuma mudança de schema/endpoint backend — o cálculo já estava certo, só o cache
do cliente não era avisado por completo.

## 4. Por que não uma mudança de modelagem no backend

A hipótese inicial do usuário (persistir `limite_utilizado` e mantê-lo sincronizado a cada
operação) é exatamente o padrão que o backend **já evita deliberadamente** — um campo
persistido exigiria lembrar de atualizá-lo em todo INSERT/UPDATE/DELETE de `Transacao`/
`Fatura` que toque um cartão (compra, edição, exclusão, cancelamento de parcelamento,
fechamento de fatura, pagamento, exclusão de fatura, ajuste manual), multiplicando os pontos
de falha. O desenho atual (soma em SQL a cada leitura, fonte única de verdade em
`CartaoService._com_limite_disponivel`) já é a arquitetura "calculado, nunca armazenado"
pedida — description que se aplica a esta funcionalidade não precisou de nenhuma alteração.

## 5. Terceira causa raiz encontrada (2026-07-20) — fatura importada não pagava o preço no cálculo

Depois da correção da seção 3, o usuário reportou (com print da tela real) que o cartão
"Inter" ainda mostrava `Disponível` inconsistente com a única fatura visível já paga.
Inspeção direta (somente leitura) do banco de produção do usuário mostrou a causa: um
**segundo ciclo**, invisível na tela mostrada, existia para o mesmo cartão — uma fatura
**importada** (`Fatura.importada=True`, criada via `POST /faturas/importar`, `FECHADA`,
`valor_total=796.60`, **zero** `Transacao` vinculada, `ajuste_manual=0`) ainda não paga.

`CartaoRepository.somar_gastos_nao_pagos` somava só duas fontes de dívida (seção 1): `SUM` de
`Transacao.valor` e `SUM` de `Fatura.ajuste_manual`. Uma fatura importada não alimenta
nenhuma das duas — por desenho ela nasce com `valor_total` declarado diretamente pelo usuário
e `ajuste_manual` forçado a `0` (`FaturaService.importar`, ver `FaturaImportarCreate`), pois
representa um ciclo **histórico já fechado antes do usuário começar a usar o app** — não uma
lista de compras a recriar uma a uma. Resultado: o valor aparecia em `FaturaRead.valor_total`
(a tela de faturas mostrava o número certo) mas nunca entrava em `limite_disponivel` — a
mesma dívida existia em dois lugares que não se falavam.

**Correção**: terceiro termo em `somar_gastos_nao_pagos` — `SUM(Fatura.valor_total)` para
faturas `importada=True` ainda não pagas (filtrado por `importada=True` para nunca duplicar a
dívida de uma fatura fechada normalmente, cujo `valor_total` já vem do `SUM` de `Transacao`
reais). Teste dedicado:
`test_limite_disponivel_desconta_fatura_importada_nao_paga` em `test_cartao_flow.py`.

Esta é a mesma classe de causa raiz da seção 1 (nenhum campo persistido a sincronizar) — o gap
não era um valor desatualizado, era uma **fonte de dívida real inteira ausente da soma**. As
seções 1-4 continuam válidas para as duas fontes que já existiam (`Transacao`,
`ajuste_manual`); esta seção documenta a terceira, que só existe desde que
`FaturaService.importar()` foi implementado (fatura histórica) e não tinha sido auditada
contra `somar_gastos_nao_pagos` até este momento.

### 5.1 Regra nova: importação bloqueada para ciclo ainda não fechado

Mid-turn, o usuário também relatou uma inconsistência de UX ligada ao mesmo fluxo: importar
uma fatura de um `mes_referencia` **futuro** a fazia nascer `FECHADA` — sem sentido, já que
"fechar" pressupõe que o ciclo real já aconteceu. `FaturaService.importar()` agora rejeita
(`BusinessRuleError`, HTTP 422) qualquer `mes_referencia` cujo `data_fechamento` calculado
(`_calcular_datas_ciclo`) seja `>= date.today()`. Para um ciclo atual/futuro o caminho correto
já existia e continua sendo: criar uma fatura normal (`POST /faturas`, nasce `ABERTA`) e usar
"Informar saldo já utilizado" (`ajustar_saldo_inicial`, seção 1) para declarar o valor sem
lançar cada compra — diferente da importação, essa fatura continua `ABERTA` e o ajuste pode
ser corrigido a qualquer momento. Teste dedicado:
`test_importar_fatura_com_ciclo_ainda_nao_fechado_retorna_422` em `test_fatura_flow.py`.
