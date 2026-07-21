# Análise arquitetural — Refinamento de pagamento de Fatura + integração com Transação

## 0. Escopo

Zero mudança de regra de negócio ou API. `FaturaService.registrar_pagamento` já foi lido por
completo (`backend/app/services/fatura_service.py`) — nenhuma linha de backend muda nesta
etapa. Objetivo: tornar a ação já existente mais acessível e mais clara, e corrigir um gap
real de atualização em tempo real encontrado durante a leitura (seção 2).

## 1. O que o backend já garante (não precisa de lógica nova)

- `POST /faturas/{id}/pagamentos` (`FaturaPagamentoCreate { valor: Decimal (gt=0), data,
  descricao? }`) já aceita QUALQUER valor positivo — pagamento total, parcial ou
  personalizado são todos, do ponto de vista do backend, "a mesma chamada com um número
  diferente". Não há variação de payload nem endpoint por tipo de pagamento.
- `valor_pago` (em `FaturaRead`) é sempre a SOMA de todas as `Transacao`s com
  `fatura_paga_id` igual ao da fatura — pagamentos múltiplos/parciais já são,
  literalmente, "chamar `registrar_pagamento` mais de uma vez". Nenhum estado adicional a
  gerenciar no frontend.
- Só permitido quando a fatura não está `ABERTA` (precisa fechar o ciclo primeiro) — já
  respeitado hoje pelo `FaturaDrawer` (botão "Registrar pagamento" só aparece fora de
  `ABERTA`).
- **`registrar_pagamento` já cria uma `Transacao` de verdade**: `tipo=DESPESA`,
  `conta_id=cartao.conta_pagamento_id`, `fatura_paga_id=fatura.id`, descrição default
  `"Pagamento de fatura - {nome do cartão}"`. Ou seja, **a integração com Transação pedida
  já existe na modelagem** — todo pagamento de fatura JÁ é uma transação real na conta de
  pagamento do cartão. Não é preciso criar nenhum vínculo novo; é preciso só que o frontend
  reflita isso (seção 2).
- Não há trava de "não pagar mais que o valor total" no backend — `valor` só precisa ser
  `> 0`. Decisão: não inventar uma trava no cliente que o backend não tem (evita duas fontes
  de verdade divergentes); no máximo, um aviso visual não-bloqueante se o valor digitado
  ultrapassar o restante calculado.

## 2. Achado real — gap de invalidação (a causa de "não atualiza sozinho")

`hooks/useFaturaQueries.ts` → `useRegistrarPagamento(cartaoId)` invalida hoje:
`["faturas"]`, `dashboard.faturas`, `dashboard.cartoes`, `cartoes.detail(cartaoId)`.

Isso NUNCA invalida `queryKeys.transacoes.*`, `contas.detail(contaPagamentoId)`,
`dashboard.resumo`, `dashboard.saldoConsolidado`, `dashboard.visaoMensal`,
`dashboard.agenda` ou `dashboard.indicadores` — mesmo o pagamento criando uma `Transacao`
real que afeta todos eles (exatamente o mesmo raciocínio já aplicado em
`useTransacaoQueries.ts`, que tem uma função `invalidarTransacoes` dedicada a isso). Esta é
a causa raiz concreta de "a Central Financeira/Transações não refletem o pagamento
imediatamente" — não é preciso adivinhar, o Service confirma que uma `Transacao` é criada e
os hooks confirmam que essa invalidação não existe.

**Correção**: exportar `invalidarTransacoes` de `hooks/useTransacaoQueries.ts` (deixa de ser
uma função privada do módulo) e reutilizá-la dentro de `useRegistrarPagamento`, além da
invalidação de Fatura que já existe — mesma função, dois pontos de chamada, zero lógica
duplicada. `contaId` vem de `cartao.conta_pagamento_id` (já disponível via `useCartao`/
`useCartoes` no componente que chama o hook).

## 3. Decisão — Atalhos de valor (client-side, sem chamada de API nova)

Três atalhos acima do campo de valor no formulário de pagamento (dentro do `FaturaDrawer`
já existente):

- **Pagar valor total** — preenche o campo com `fatura.valor_total`. Só faz sentido (e só
  aparece) quando `valor_pago === 0`; depois do primeiro pagamento parcial, "total" deixa de
  ser uma opção coerente.
- **Pagar restante** — preenche com `fatura.valor_total - fatura.valor_pago`. Aparece sempre
  que o restante for `> 0` (cobre tanto quitar de uma vez quanto quitar o que sobrou de
  pagamentos parciais anteriores).
- **Pagamento parcial** — não é um botão à parte: é simplesmente digitar um valor diferente
  no campo, que já aceita qualquer valor. Rotular um terceiro botão para isso seria
  redundante (o campo já É o pagamento parcial por padrão).

Todos os três só preenchem o `CurrencyField` já existente — nenhuma mudança no payload
enviado (`FaturaPagamentoCreate` continua idêntico), nenhuma rota nova.

## 4. Decisão — Preview client-side, explicitamente não-autoritativo

Enquanto o usuário digita o valor, mostrar: novo valor pago (`valor_pago + valor digitado`),
novo restante, e um selo de status previsto — usando a MESMA prioridade de
`FaturaService._derivar_status` (quitado > atrasado > parcial > fechado), mas como uma
função pura só de EXIBIÇÃO em `utils/fatura.ts` (`preverStatusPosPagamento`), claramente
comentada como preview, nunca persistida. Assim que a mutation resolve, o preview é
descartado e a UI volta a mostrar exatamente o que `useFatura`/`useFaturas` (dados reais)
retornam — nenhum risco de o preview divergir silenciosamente da fonte de verdade, porque
ele nunca é usado para nada além do instante de digitação.

## 5. Decisão — Onde a UX melhora (sem mudar o container do overlay)

O pedido descreve "Dialog ou Drawer elegante" — o projeto já tem exatamente o container
certo: `FaturaDrawer` (Tier 2, `docs/analise-arquitetural-overlays.md` seção 4.5), já aberto
a partir de `ProximaFaturaCard` (botão contextual "Registrar pagamento"/"Fechar ciclo") e da
lista inline de faturas em `/cartoes/:id`. Não há necessidade de promover para um Dialog
separado — o Drawer já resolve "sem precisar navegar por outras telas". O que melhora é o
CONTEÚDO da seção de pagamento dentro dele:

- Novo campo "Valor restante" no `dl` de detalhes (hoje só mostra total/pago).
- Novo `ProgressBar` de progresso de pagamento (`valor_pago / valor_total`), mesmo
  componente/tom (`utils/status.ts`) já usado em Cartão para limite.
- Os três atalhos (seção 3) + preview (seção 4) dentro do formulário que já existe.
- `ProximaFaturaCard` ganha o mesmo `ProgressBar` de progresso (hoje só mostra o valor
  total e a urgência do vencimento) — mesma peça reutilizada, sem componente novo.

## 6. Integração com Transação — já existe, só precisa aparecer

Como a seção 1 mostra, pagar uma fatura já é criar uma `Transacao`. Depois da correção de
invalidação (seção 2), abrir `/transacoes` no mês do pagamento já mostra a linha
"Pagamento de fatura - {cartão}" automaticamente, sem nenhuma tela nova. Não é necessário
nenhum indicador visual extra na tabela de Transações (ex. um ícone "veio de uma fatura") —
fora de escopo por ora: a descrição já é autoexplicativa, e adicionar mais uma coluna/badge
só para esse caso específico não foi pedido e aumentaria a densidade da tabela sem
benefício claro. Documentado aqui como oportunidade futura caso o usuário sinta falta.

## 7. Fora de escopo (explicitamente)

- Mudar `CartaoResumoCard`/`CartaoActionBar` para adicionar um atalho de pagamento direto
  no grid de `/cartoes` — o caminho já existe (clicar no cartão → `ProximaFaturaCard` →
  Registrar pagamento) e adicionar um segundo atalho paralelo arriscaria duas UIs para a
  mesma ação. Se o usuário sentir que ainda falta um passo, é um ajuste pontual futuro, não
  desta etapa.
- Qualquer trava client-side de "não pagar mais que o total" (seção 1) — no máximo um aviso
  visual não-bloqueante.
- Indicador de origem "veio de pagamento de fatura" na tabela de Transações (seção 6).

## 8. Auditoria final planejada

`tsc -b`, `vite build`, teste manual do fluxo completo (fechar ciclo → registrar pagamento
parcial → conferir Transações/Conta/Dashboard atualizados sem F5 → registrar o restante →
conferir status vira PAGA).
