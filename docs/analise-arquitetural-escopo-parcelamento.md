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
