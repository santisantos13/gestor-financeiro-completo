# Análise arquitetural — limite de cartão (nova auditoria) e escopo de exclusão de Parcelamento

## 0. Pedido do usuário

Dois problemas relatados, com pedido explícito de causa raiz (não correção pontual) e de
centralizar a regra de negócio para crescer sem refatoração:

1. Limite do cartão não libera ao pagar fatura / não recalcula ao excluir compra.
2. Excluir uma parcela de uma compra parcelada remove só aquela parcela — deveria remover o
   parcelamento inteiro (todas as parcelas, vínculos, reflexos no cartão/fatura/calendário/
   dashboard/histórico), com uma confirmação clara antes, e a arquitetura pronta para no
   futuro suportar granularidade (editar/excluir só esta parcela, editar todas as parcelas).

## 1. Limite do cartão — o backend já estava certo, faltavam mais dois pontos de cache

Uma etapa anterior desta mesma sprint (`docs/analise-arquitetural-limite-cartao-invalidacao.md`)
já tinha corrigido o gap principal: `queryKeys.cartoes.detail(id)` sendo invalidado em vez de
`queryKeys.cartoes.all` em `useFaturaQueries.ts`/`useTransacaoQueries.ts` — `list`/`detail` são
ramos IRMÃOS da chave de Cartão, não pai/filho, então a página `/cartoes` continuava com o
`limite_disponivel` antigo mesmo depois de pagar uma fatura ou excluir uma compra.

Reauditando a cadeia inteira para este pedido (backend confirmado, de novo, 100% derivado —
nenhum `limite_utilizado` persistido em lugar nenhum, ver seção 1 do documento anterior),
apareceram DOIS gaps adicionais da **mesma classe de bug**, ambos em
`useTransacaoQueries.ts::invalidarTransacoes` (o ponto único chamado por toda mutation de
Transação — criar, editar, excluir — e reaproveitado por `useCriarParcelamento`,
`useFinanciamentoQueries.ts` e `useEmprestimoQueries.ts`):

- **`contas.detail(contaId)` em vez de `contas.all`**: uma transação de Conta (não-cartão)
  deixava `/contas` (`ContasPage`, que lê `contas.list`) com `saldo_atual` desatualizado,
  mesmo a página de detalhe já se atualizando. Mesma causa raiz exata do bug de Cartão, só que
  do lado de Conta — `useContaQueries.ts` e `invalidarTransferencias`
  (`useTransferenciaQueries.ts`) já usavam `contas.all` corretamente; só esta função ainda
  usava a chave estreita.
- **`["faturas"]` nunca invalidado por mutação de Transação**: uma compra de cartão tem
  `fatura_id` — criar/editar/excluir uma compra muda `valor_total_calculado`/
  `status_calculado` (sempre derivados, `FaturaService._com_valores_calculados`) da fatura do
  ciclo correspondente, mas só `dashboard.faturas` (o agregado da Central Financeira) era
  invalidado. A lista de faturas de UM cartão (`useFaturas(cartaoId)`, usada em
  `CartaoDetalhePage`) ficava com o total antigo até um F5 — o `limite_disponivel` do cartão já
  estava certo (corrigido na etapa anterior), mas o card de cada fatura individual, logo
  abaixo, mostrava um valor que não batia. Provavelmente a origem de "o limite não recalcula
  direito" continuar sendo percebido mesmo após a primeira correção.

Ambos corrigidos em `invalidarTransacoes` (`frontend/src/hooks/useTransacaoQueries.ts`):
`contas.all` sempre que `contaId` é conhecido, `["faturas"]` sempre que `cartaoId` é conhecido
(mesmo prefixo cru que `useFaturaQueries.ts::useInvalidateFaturas` já usa). Como
`useFinanciamentoQueries.ts`/`useEmprestimoQueries.ts`/`useCriarParcelamento` reaproveitam esta
mesma função, a correção se propaga a pagamento de parcela de financiamento/empréstimo e
criação de parcelamento automaticamente — nenhum outro arquivo precisou mudar.

## 2. Exclusão de compra parcelada — já cascateava, mas a regra estava implícita

Investigação encontrou que o comportamento pedido (excluir qualquer parcela cancela TODO o
parcelamento, preservando só parcelas já em fatura fechada) **já existia** — implementado numa
etapa anterior (`TransacaoService.excluir` → `cancelar_parcelas_do_parcelamento`, com 3 testes
de integração já cobrindo o caso principal, a preservação de parcela travada e o bloqueio da
parcela clicada quando ela mesma está travada) e já com um diálogo de confirmação em
`TransacoesPage.tsx` avisando sobre a cascata. O que faltava:

- A regra vivia como um `if transacao.parcelamento_id is not None:` inline dentro de
  `excluir()` — funcional, mas sem um nome/conceito próprio, então uma futura variação
  ("excluir só esta parcela") exigiria decidir, no meio de outro método, onde encaixar a
  ramificação nova.
- O diálogo de confirmação não mostrava o número real de parcelas (pedido explícito do
  usuário: "Esta compra possui 12 parcelas...").

### Centralização: `EscopoOperacaoParcela`

Novo enum interno em `app/services/transacao_service.py` (deliberadamente FORA de
`app/models/enums.py` — nenhum valor é aceito via payload de cliente ainda, não é vocabulário
de API/schema, é uma decisão só de Service):

```python
class EscopoOperacaoParcela(str, enum.Enum):
    ESTA_PARCELA = "ESTA_PARCELA"        # reservado, NÃO implementado
    TODO_PARCELAMENTO = "TODO_PARCELAMENTO"  # único suportado hoje, sempre usado
```

`TransacaoService.excluir()` agora delega para `_aplicar_exclusao_de_parcela(transacao,
usuario_id, escopo=EscopoOperacaoParcela.TODO_PARCELAMENTO)` — um método novo, único ponto de
decisão "o que fazer com as outras parcelas". Ele chama o mesmo `cancelar_parcelas_do_
parcelamento` de sempre (nenhuma mudança de comportamento/regra de negócio, só nomeação e
extração) e levanta `NotImplementedError` explícito para qualquer outro escopo — nunca cai
silenciosamente para um comportamento parecido mas errado.

`atualizar()` (edição) ganhou uma nota de docstring apontando para o mesmo conceito: hoje edita
só a linha clicada (nenhuma mudança de comportamento aqui, não foi pedido), mas se um dia
existir "editar todas as parcelas"/renegociação, o lugar de decidir é o início deste método,
reusando `EscopoOperacaoParcela` em vez de inventar uma segunda convenção.

**Como isso prepara o futuro pedido explicitamente**: adicionar "excluir apenas esta parcela"
um dia = adicionar um `elif escopo is ESTA_PARCELA` dentro de
`_aplicar_exclusao_de_parcela` (hoje um `NotImplementedError`) + expor `escopo` como parâmetro
opcional em `TransacaoUpdate`/query string de `DELETE /transacoes/{id}` — nenhuma outra parte
do sistema muda. "Editar todas as parcelas" = mesmo raciocínio dentro de `atualizar()`. Nenhuma
dessas duas foi implementada agora (YAGNI, pedido explícito do usuário) — só o ponto de
extensão existe.

### Diálogo de confirmação — agora com contagem real

`TransacoesPage.tsx` passou a buscar o `Parcelamento` (`GET /parcelamentos/{id}`, novo hook
`useParcelamento(id)` em `useParcelamentoQueries.ts`, só disparado quando a transação
selecionada tem `parcelamento_id`) para mostrar `num_parcelas` de verdade:

> "Esta compra possui 12 parcelas. Ao excluí-la, todas as parcelas serão removidas
> permanentemente (as que já estiverem em faturas fechadas são preservadas como histórico).
> Esta ação não pode ser desfeita."

A ressalva sobre faturas fechadas foi mantida (não é opcional silenciar isso): é o mesmo
invariante de "documento financeiro histórico nunca é reescrito" usado em todo o projeto — uma
parcela já paga/fechada não desaparece, mesmo cancelando o resto da compra. Sem essa frase, o
usuário poderia clicar esperando ver TODAS as parcelas sumirem e ficar confuso ao ver uma
sobrar. Compra não-parcelada mantém a mensagem genérica de sempre (comportamento inalterado).

`queryKeys.parcelamentos` ganhou `detail(id)` (antes só `all`) — `all` continua sendo o único
alvo de invalidação (nenhuma mutation nova foi criada), casando `detail(id)` por prefixo
automaticamente.

## 3. Outras inconsistências encontradas durante a auditoria (já corrigidas)

Cobertas nas seções 1 (gaps de invalidação de Conta/Fatura) e 2 (nomeação da regra) acima — não
foi encontrada nenhuma inconsistência adicional de dado (backend permanece 100% derivado em
toda a cadeia Cartão/Fatura/Transação/Parcelamento; nenhum contador incremental em lugar
nenhum).

## 4. Validação

Backend: suíte completa (~700+ testes) + testes novos cobrindo compra simples, parcelada 2x,
12x, parcialmente paga (preserva parcela travada, cancela o resto), totalmente paga (bloqueia
exclusão de QUALQUER parcela, não só a "clicada" do teste anterior), múltiplos cartões,
`GET /parcelamentos/{id}` (usado pelo novo diálogo), e o novo `NotImplementedError` de
`EscopoOperacaoParcela.ESTA_PARCELA`. Frontend: `tsc -b` e `vite build` limpos.

## 5. `parcelamento_cancelado` — a parcela preservada precisava de um aviso (2026-07-25)

Bug relatado pelo usuário: "registro despesas, mas depois excluo e o valor não sai da
informação geral" (print de `TransacoesPage`, cards "Despesas do período"/"Receitas do
período"/"Saldo do período").

**Reprodução** (script ad-hoc contra `TestClient`, não um teste automatizado - só para isolar a
causa): compra parcelada em 3x num cartão, primeira parcela cai num ciclo cujo `fatura_id` foi
fechado (`POST /faturas/{id}/fechar`). Excluir a compra inteira (clicando em qualquer parcela
destravada) preserva a parcela da fatura fechada, exatamente como a seção 2 deste documento já
documenta - **isso não é um bug novo, é o comportamento deliberado de sempre**. O
`GET /central-financeira/visao-mensal` do mês da parcela preservada continuou corretamente
somando aquele valor (`_somar_periodo` não filtra por `Parcelamento.ativo` - não faria sentido,
já que a Transacao continua existindo de verdade e o dinheiro realmente saiu do cartão).

**A causa raiz real não era um cálculo errado - era a ausência de qualquer explicação visível**
de por que aquela parcela específica sobrevivia. Sem isso, o usuário via "excluí a compra" e o
total do mês não mudando (para o mês da parcela travada), com nenhum jeito de descobrir o
porquê a partir da tela de Transações.

**Por que não em `TransacoesPage`, e sim em `FaturaDrawer`**: `TransacoesPage` sempre envia
`apenas_conta=true` (`TransacaoRepository.listar_do_usuario`, pedido de 2026-07-20: "a tela de
Transações não deve listar compras de cartão") - toda parcela sobrevivente tem `cartao_id`
preenchido (só compra de CARTÃO tem `fatura_id`/conceito de fechamento; parcelamento de CONTA
nunca preserva nada, `_impedir_escrita_em_fatura_fechada` não trava nada sem `fatura_id`), então
ela NUNCA aparece naquela tabela, badge nenhum ajudaria ali. O único lugar onde a parcela
preservada é de fato visível é `FaturaDrawer` → "Compras desta fatura" (`useComprasDaFatura`,
sem esse filtro) - é lá que o aviso foi colocado.

**Implementação**: `TransacaoService._marcar_parcelamento_cancelado` (chamado por
`obter`/`listar`/`criar`/`atualizar`/`marcar_parcela_de_contrato_paga` - todo return path que
vira `TransacaoRead`, mesmo cuidado de sempre anexar o campo calculado em 100% dos casos, nunca
só "quando dá") anexa `Transacao.parcelamento_cancelado` (transiente, nunca persistido) = `True`
só quando `parcelamento_id` aponta para um `Parcelamento` com `ativo=False`. Busca em lote
(`ParcelamentoRepository.listar_por_ids`, 1 query `IN` para toda a página) - nunca 1 query por
transação. `TransacaoRead.parcelamento_cancelado: bool = False` no schema;
`TransacaoRead.parcelamento_cancelado: boolean` no tipo do frontend. `FaturaDrawer` renderiza um
`Badge` "Compra cancelada" ao lado da descrição da compra quando o campo é `true`, com `title`
explicando o motivo.

Nenhum valor histórico foi alterado - a fatura fechada, seu `valor_total` congelado e o total do
período continuam exatamente como sempre foram (o invariante "documento financeiro fechado
nunca é reescrito", já citado na seção 2, permanece intacto). Esta é puramente uma correção de
comunicação visual.

## 6. Revisão da decisão: "Despesas do período" também não deve contar cartão (2026-07-25, mesmo dia)

Depois da correção da seção 5, o usuário voltou: "os valores de despesas ainda está errado.
lembra das nossas decisões sobre esta aba?" - referência direta à seção 14 de
`docs/analise-arquitetural-transacao-frontend.md` (2026-07-20): compra de cartão nunca aparece
como linha na tabela de `/transacoes`.

Até este ponto, `TransacaoResumoPeriodo` (os 3 `MetricCard`s "Receitas/Despesas/Saldo do
período" no topo da página) reaproveitava `GET /central-financeira/visao-mensal` **sem** nenhum
filtro - o mesmo total usado pelo Dashboard, que sempre incluiu compra de cartão de propósito
(gasto real do mês, independente da forma de pagamento). Resultado: o total no topo da página de
Transações somava mais do que a soma das linhas realmente visíveis logo abaixo - toda compra de
cartão do mês entrava no número sem nunca aparecer como linha, com nenhuma explicação visível
(diferente da seção 5, aqui não tem nem uma parcela "órfã" para apontar - a extensão inteira do
gasto de cartão do mês simplesmente não bate).

**Decisão do usuário**: não, cartão não deve contar em "Despesas/Receitas do período" desta
tela também - o total precisa bater com a tabela.

### Por que não reaproveitar `visao-mensal` sem alteração

`visao-mensal` é usado por DOIS consumidores com necessidades opostas: `ResumoFinanceiroSection`
(Dashboard, quer o gasto real do mês, cartão incluído - nunca foi questionado, continua correto)
e agora `TransacaoResumoPeriodo` (quer bater com a tabela, cartão excluído). Mudar o
comportamento padrão do endpoint quebraria o Dashboard. Solução: mesmo padrão aditivo/opt-in já
usado para a tabela em si (`apenas_conta: bool = False`, seção 14 de
`analise-arquitetural-transacao-frontend.md`), agora estendido para a AGREGAÇÃO:

- `TransacaoRepository.somar_por_periodo` ganhou `apenas_conta: bool = False` - quando `True`,
  soma `Transacao.cartao_id IS NULL` (mesma condição já usada em `listar_do_usuario`).
- `TransacaoService.somar_por_periodo` e `CentralFinanceiraService._somar_periodo`/`visao_mensal`
  só repassam o parâmetro adiante - nenhuma regra nova.
- `GET /central-financeira/visao-mensal?apenas_conta=true` - novo query param opcional, mesmo
  default `False` de sempre.
- Frontend: `queryKeys.dashboard.visaoMensal` ganhou um terceiro parâmetro `apenasConta`
  **dentro da própria chave** - crítico, porque os dois consumidores (Dashboard e
  `TransacaoResumoPeriodo`) chamam o MESMO endpoint com resultados DIFERENTES agora; sem entrar
  na chave, os dois React Query cache colidiriam (o que buscar por último "vence" e o outro
  consumidor mostraria o número errado até uma invalidação forçar um refetch - um bug sutil e
  intermitente, evitado desde o início). `centralFinanceiraService.visaoMensal` e
  `useVisaoMensalQuery` só repassam o parâmetro. `TransacaoResumoPeriodo` chama
  `useVisaoMensalQuery(ano, mes, true)`; `ResumoFinanceiroSection` continua chamando
  `useVisaoMensalQuery(ano, mes)` (sem o terceiro argumento), preservando 100% do comportamento
  do Dashboard.

`resumo_financeiro` (outro consumidor de `_somar_periodo`, usado por `/central-financeira/resumo`
- saldo total/patrimônio líquido/fluxo de caixa geral do Dashboard) não foi tocado - continua
sem passar `apenas_conta`, mesmo raciocínio de "gasto real" do Dashboard.

### Validação

Backend: 1 teste unitário novo (`test_visao_mensal_com_apenas_conta_exclui_compra_de_cartao`) +
1 de integração novo (mesmo nome, `test_central_financeira_flow.py`) provando que, com a mesma
massa de dados (uma despesa de Conta + uma de Cartão), `apenas_conta=false` soma as duas e
`apenas_conta=true` só a de Conta. Suíte completa (634 unit + toda integração) revalidada.
Frontend: `tsc -b`, `vite build` e suíte de 21 testes revalidados.

## 7. `ESTA_PARCELA` deixa de ser reservado: excluir só uma parcela (2026-07-28)

Pedido do usuário: fechar o ponto de extensão que a seção 2 deixou pronto, mas não implementado
- "excluir só esta parcela" de uma compra parcelada, sem cancelar as outras N-1 (diferente do
único comportamento existente até aqui, `TODO_PARCELAMENTO`, que sempre cancela a compra
inteira). Caso de uso real: lançamento duplicado por engano numa parcela específica, ou uma
parcela isolada que precisa ser corrigida sem mexer no resto da compra.

### Backend

`EscopoOperacaoParcela` **promovido** de enum interno de `transacao_service.py` para
`app/models/enums.py` - deixou de ser "decisão só de Service" (docstring antiga) no momento em
que passou a ser aceito de verdade via query string (`DELETE /transacoes/{id}?escopo=...`),
virando vocabulário de API. Mesma dupla de valores de sempre (`TODO_PARCELAMENTO`/
`ESTA_PARCELA`), sem nenhuma mudança de nome ou semântica do que já existia.

`TransacaoService.excluir()` ganhou o parâmetro opcional `escopo: EscopoOperacaoParcela =
TODO_PARCELAMENTO` - default preserva 100% do comportamento anterior para qualquer chamador que
não foi atualizado (nenhuma chamada interna existente precisou mudar). `_aplicar_exclusao_de_
parcela` deixou de levantar `NotImplementedError` para `ESTA_PARCELA` e passou a delegar para um
novo método, `_excluir_apenas_esta_parcela`:

- Remove só a `Transacao` clicada (`transacao_repo.delete`), nunca as demais - diferente de
  `cancelar_parcelas_do_parcelamento`, que sempre cancela a compra inteira.
- `Parcelamento.valor_total`/`num_parcelas` NUNCA são recalculados - permanecem o registro
  histórico da compra original, mesmo raciocínio já usado por `cancelar_parcelas_do_
  parcelamento` (que também nunca toca `valor_total`). Excluir uma parcela por engano/duplicidade
  não reescreve "quantas parcelas a compra tinha".
- `Parcelamento.ativo` só vira `False` se esta era a ÚLTIMA parcela restante (nenhuma outra
  sobrando, de qualquer status) - idempotente, mesmo padrão de `cancelar_parcelas_do_
  parcelamento`.
- A checagem "não mexe em fatura fechada" da parcela clicada continua rodando em `excluir()`
  ANTES da decisão de escopo (nenhuma duplicação) - ou seja, `ESTA_PARCELA` numa parcela já
  travada continua bloqueada com `BusinessRuleError`/422, igual `TODO_PARCELAMENTO` sempre foi.

`GET /transacoes` e o resto da cadeia (Fatura/Cartão/Central Financeira) não mudam - a exclusão
de uma parcela via `ESTA_PARCELA` é, do ponto de vista de todo o resto do sistema, indistinguível
de excluir qualquer outra `Transacao` avulsa (o cálculo de limite/fatura já é 100% derivado,
recalcula sozinho).

### Frontend

`transacaoService.excluir(id, escopo?)` repassa `escopo` como query param só quando informado
(`httpClient.delete` já ignora chaves `undefined`). `useExcluirTransacao`/`useExcluirCompra`
(dentro de `FaturaDrawer`) trocaram a assinatura da `mutationFn` de `(id: number)` para
`({ id, escopo? })` - único jeito de aceitar um segundo argumento opcional dentro de
`mutateAsync` sem quebrar a API de hooks do React Query (que só aceita 1 argumento de variables).

`ConfirmAction` (design system, Tier 2) ganhou uma segunda ação de confirmação opcional
(`secondaryConfirmLabel`/`onConfirmSecondary`/`secondaryLoading`) - primeiro caso do app com DUAS
variações de "confirmar" igualmente válidas. Nenhum `ConfirmAction` existente precisou mudar
(campos opcionais, default nenhum botão extra).

Os dois lugares onde uma parcela pode ser excluída pelo usuário ganharam a escolha:

- `TransacoesPage` (parcelamento de Conta, já que `/transacoes` nunca mostra compra de cartão -
  ver seção 14 de `docs/analise-arquitetural-transacao-frontend.md`): `ConfirmAction` mostra
  "Compra inteira" (ação principal, `TODO_PARCELAMENTO`, preserva o rótulo/comportamento visual de
  sempre para quem não usa parcelamento) e "Só esta parcela" (`ESTA_PARCELA`, novo botão
  secundário) só quando a transação tem `parcelamento_id`.
- `FaturaDrawer` → "Compras desta fatura" (parcelamento de Cartão): mesmo par de botões, dentro do
  bloco de confirmação inline já existente (não um `ConfirmAction` separado - continua valendo a
  regra de nunca empilhar dois Tier 2 com backdrop próprio, ver seção 2 acima).

Nenhuma transação sem `parcelamento_id` ganha o botão extra em nenhum dos dois lugares - o fluxo
de exclusão simples continua idêntico ao de sempre.

### Validação

Backend: 4 testes unitários novos (remove só a clicada; cancela o parcelamento quando era a
última parcela restante; ainda bloqueia fatura fechada da própria parcela; escopo default
continua cancelando tudo) substituindo o teste antigo que só verificava o `NotImplementedError` +
3 testes de integração novos (mesmos 3 cenários via `DELETE /transacoes/{id}?escopo=ESTA_PARCELA`
de ponta a ponta). Suíte completa (1157 testes) revalidada. Frontend: `tsc -b` limpo (build de
produção via Vite não pôde ser revalidado nesta sessão por limitação do sandbox - ver relato ao
usuário).
