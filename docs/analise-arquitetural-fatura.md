# Análise arquitetural — Fatura

Análise de modelagem prévia à implementação do CRUD de `Fatura`, seguindo o mesmo rigor das
revisões técnicas de `Conta`/`Categoria`/`Tag`/`Cartão`, mas feita **antes** do código em vez
de depois: `Fatura` é o elo entre `Cartao` e `Transacao`, e um erro de modelagem aqui se
propagaria para o CRUD de `Transacao` (a próxima etapa) e para qualquer cálculo financeiro
que dependa de cartão. **Status: aprovada** — este documento registra a arquitetura validada
antes da implementação.

## Fatura ↔ Cartão

Já modelado corretamente em `Cartao`/`Fatura`: `Fatura.cartao_id` (CASCADE) +
`UniqueConstraint(cartao_id, mes_referencia)` impede dois ciclos para o mesmo mês. Nenhuma
mudança de schema necessária aqui.

Decisão de Service (não de schema): `data_fechamento`/`data_vencimento` de uma Fatura são
sempre derivadas de `Cartao.dia_fechamento`/`dia_vencimento` no momento em que o ciclo é
criado — nunca um valor livre. Mudar `dia_fechamento` de um Cartão via `PATCH` depois que
faturas já existem **não** altera retroativamente ciclos já criados (nem a `ABERTA` atual);
só afeta ciclos futuros a partir da mudança.

## Fatura ↔ Transação

Também já modelado (`Transacao.fatura_id`, nullable, `SET NULL`). `fatura_id` nunca vem do
payload do cliente — é sempre resolvido internamente por um método único de
`FaturaService` ("resolver, ou criar, a fatura aberta para esta data neste cartão"), mesmo
princípio já usado para `usuario_id` (nunca vem do payload) e `conta_pagamento_id` de
Cartão (sempre validado no Service).

**`Transacao.status` (PENDENTE/PAGO) não é autoridade sobre cobrança de fatura.** Esse
campo foi desenhado pensando em `Conta` ("já aconteceu ou ainda vai acontecer"); para uma
transação de cartão isso não tem o mesmo significado — a compra "acontece" no ato,
independente de quando a fatura é paga. Quem decide "isso está pago?" é sempre `Fatura`
(via `valor_pago`, ver seção de pagamento parcial), nunca `Transacao.status`. Mesmo
princípio já aplicado em `CartaoRepository.somar_gastos_nao_pagos`, que ignora `status` de
propósito.

## Fatura ↔ Parcelamento

Sem FK direta. Cada parcela de um `Parcelamento` é uma `Transacao` própria com sua própria
`data`, então cada uma resolve para o ciclo correspondente à sua data — possivelmente
ciclos diferentes (parcela 1 na fatura de julho, parcela 2 na de agosto). O
`CheckConstraint` de "no máximo um contrato" em `Transacao` já corretamente não inclui
`fatura_id` na exclusão mútua — uma parcela pode ter `parcelamento_id` e `fatura_id`
preenchidos ao mesmo tempo. Nenhuma mudança de schema necessária.

O método de resolução de ciclo por data (ver próxima seção) precisa ser genérico o
suficiente para ser chamado tanto na criação de uma compra avulsa quanto na geração das
parcelas de um `Parcelamento` — um único ponto de resolução, reaproveitado.

## Fatura ↔ Financiamento / Empréstimo

Não há relação, e não deve haver. `Financiamento`/`Emprestimo` (via `ContratoCreditoMixin`)
só têm `conta_id`, nunca `cartao_id` — parcelas de contrato de crédito saem direto da
conta, nunca passam por cartão/fatura. Confirmado como correto na modelagem atual; nenhuma
mudança necessária.

## Resolução de ciclo por data: compras após o fechamento e estornos

Toda `Transacao` vinculada a um cartão (compra ou estorno) resolve seu `fatura_id` pela
**mesma regra única**: encontrar (ou criar) a fatura cujo ciclo cobre a `data` da transação,
segundo `dia_fechamento`/`dia_vencimento` do cartão. Não existem regras separadas para
"compra atrasada" e "estorno" — as duas situações são resolvidas pelo mesmo mecanismo,
evitando duplicar lógica de ciclo em dois lugares.

**Compra após o fechamento**: se `data > data_fechamento` da fatura `ABERTA` atual, ela não
pode ser anexada a essa fatura — a resolução por data naturalmente aponta para o ciclo
seguinte (criado sob demanda se ainda não existir). Isso não é uma trava extra a
implementar; é uma consequência de resolver corretamente por data.

**Estorno (reversão de uma compra anterior)**: modelado como uma `Transacao` comum, tipo
`RECEITA`, vinculada ao mesmo `cartao_id` da compra original — sem entidade ou campo novo.
O ponto que precisa ficar explícito: a `data` de um estorno é a data em que o estorno **foi
processado** (tipicamente "hoje"), nunca a data da compra original. É essa data — não a da
compra — que passa pela resolução de ciclo. Consequência direta:

- Se o estorno acontece enquanto a fatura da compra original ainda está `ABERTA`, ele cai
  **na mesma fatura** (a data do estorno ainda resolve para aquele ciclo) — reduz o
  `valor_total` daquele ciclo antes mesmo de fechar.
- Se o estorno acontece depois que a fatura original já fechou (caso comum: compra dia 5,
  fatura fecha dia 10, loja processa o estorno só dia 20), ele cai **na fatura seguinte** —
  nunca reabre ou reescreve retroativamente a fatura já fechada. É exatamente o
  comportamento de uma fatura de cartão real: o crédito aparece no extrato seguinte,
  reduzindo o total daquele ciclo, não corrigindo o extrato antigo já emitido.

Se alguém tentar forçar a `data` de um lançamento (compra ou estorno) para dentro de um
ciclo já `FECHADA`, a resolução encontra uma fatura que não está `ABERTA` — nesse caso o
`FaturaService` deve **rejeitar** o lançamento (erro de regra de negócio), nunca redirecionar
silenciosamente para outro ciclo. Redirecionar sem avisar esconderia um provável erro de
data de digitação; rejeitar obriga a correção explícita.

## Cálculo do valor da fatura e snapshot no fechamento

**Enquanto `ABERTA`**: `valor_total` (em aberto) é sempre **calculado, nunca armazenado** —
soma líquida (`DESPESA` soma, `RECEITA`/estorno subtrai) de todas as `Transacao` com aquele
`fatura_id`, reaproveitando o mesmo padrão `case()`/`func.sum()` já usado em
`ContaRepository.somar_transacoes_pagas`. Nenhuma query nova a inventar.

**No momento da transição `ABERTA → FECHADA`**: o Service computa essa mesma soma uma
última vez e grava o resultado em `Fatura.valor_total`, **congelando-o permanentemente**. A
partir desse instante, `valor_total` deixa de ser recalculado em qualquer leitura — passa a
ser um snapshot histórico do valor emitido naquele ciclo, não mais um valor "ao vivo".

Isso é uma exceção deliberada ao princípio "calculado, nunca armazenado" usado em
`Conta.saldo_atual`/`Cartao.limite_disponivel` — e a exceção é justificada pela mesma razão
já usada para `saldo_devedor` em `ContratoCreditoMixin`: uma fatura fechada é um documento
financeiro histórico (equivalente a um extrato emitido), e seu valor não pode variar
retroativamente, mesmo que algo mude depois. A regra de imutabilidade de transações (próxima
seção) e a regra de resolução de ciclo (seção anterior) juntas garantem que, na prática, a
soma em tempo real das transações daquele `fatura_id` sempre coincidiria com o snapshot de
qualquer forma — mas persistir o valor explicitamente é o que torna esse histórico
resistente a qualquer falha futura nessas outras duas regras, em vez de depender
silenciosamente delas.

## Status: o que é persistido, o que é derivado

Apenas `ABERTA` e `FECHADA` são transições reais, causadas por eventos (o fechamento do
ciclo, com o snapshot acima) — essas duas continuam gravadas na coluna `status`.
`PARCIALMENTE_PAGA`, `PAGA` e `ATRASADA` são **valores derivados**, calculados a partir de
`valor_pago` (ver seção seguinte) vs. `valor_total` vs. `data_vencimento` vs. hoje, no
momento da leitura — nunca gravados. Mesmo raciocínio já aplicado a `limite_disponivel`/
`saldo_atual`: um valor derivado nunca fica desatualizado, porque é recalculado a cada
leitura a partir da mesma fonte de verdade.

## Pagamento parcial

`Fatura.transacao_pagamento_id` (FK singular, hoje via `use_alter=True`) não suporta
pagamento parcial ou múltiplos pagamentos. Substituir por `Transacao.fatura_paga_id`
(nullable, aponta para `faturas.id`, mesma forma de `fatura_id` mas propósito oposto: "esta
despesa na Conta é um pagamento — total ou parcial — desta fatura"). Permite N transações de
pagamento por fatura sem tabela nova, e elimina a dependência cíclica atual entre `Fatura` e
`Transacao` (as duas FKs passam a apontar na mesma direção, `Transacao → Fatura`, então
`use_alter=True` deixa de ser necessário).

`valor_pago` também é calculado, nunca armazenado: `SUM(Transacao.valor WHERE
fatura_paga_id = fatura.id)`. Overpayment (`valor_pago > valor_total`) não é bloqueado —
apenas resulta em `PAGA` sem nenhuma trava especial. Um único pagamento sempre quita no
máximo uma fatura (sem suporte a "uma transação paga duas faturas de uma vez") — mais
simples e mais auditável; pagar duas faturas de uma vez vira duas transações de pagamento
separadas.

Deliberadamente fora de escopo: pagamento mínimo e juros rotativo (revolving credit) — não
fazem parte das regras de negócio originais de Cartão e representam uma categoria de
complexidade nova (cálculo de juros sobre saldo não pago), a ser avaliada só se pedida
explicitamente no futuro.

## Imutabilidade de transações vinculadas a fatura fechada

Regra nova, explícita: uma vez que `Transacao.fatura_id` aponta para uma fatura cujo status
persistido não é mais `ABERTA` (ou seja, `FECHADA` — incluindo os estados derivados
`PARCIALMENTE_PAGA`/`PAGA`/`ATRASADA`, que são sempre `FECHADA` por baixo), os campos
**`valor`, `data`, `cartao_id` e `parcelamento_id`** dessa transação não podem mais ser
alterados. `TransacaoService.atualizar()` (a ser implementado no CRUD de Transação) precisa
consultar `Fatura.status` antes de aplicar qualquer `PATCH` que toque esses quatro campos —
mesmo princípio já seguido em todo o projeto: nenhum "flag de bloqueio" duplicado em
`Transacao`, `Fatura` continua sendo a única fonte de verdade sobre o estado do ciclo.

Esses quatro campos foram escolhidos porque são exatamente os que podem corromper o
snapshot congelado ou a composição histórica do ciclo: `valor` afeta o total já emitido,
`data` afeta a qual ciclo a transação pertenceria, `cartao_id` afeta a qual cadeia de
faturas ela pertence, `parcelamento_id` afeta o agrupamento/relacionamento da parcela.
Campos puramente descritivos ou organizacionais — `categoria_id`, `descricao`, `tags` —
**continuam editáveis** mesmo numa transação de fatura fechada (recategorizar uma compra
antiga, corrigir a descrição, adicionar uma tag não afeta nenhum valor financeiro nem a
composição do ciclo já emitido).

Como corolário do mesmo princípio: excluir (não só editar) uma transação vinculada a uma
fatura fechada deveria seguir a mesma trava — remover uma linha corromperia o snapshot tanto
quanto alterar seu valor. Não é um requisito novo, é a mesma regra aplicada a um caso mais
extremo.

## Geração automática das próximas faturas

Sem scheduler dentro do backend (consistente com a decisão já tomada de adiar
infraestrutura). Dois mecanismos, nenhum deles um cron:

**Criação de ciclo**: sempre *lazy*, sob demanda — o mesmo método de resolução por data é
chamado tanto na criação de uma `Transacao` de cartão quanto, futuramente, num endpoint de
"fatura atual do cartão" que o frontend chama ao abrir a tela. Faturas futuras nunca
precisam ser geradas com antecedência.

**Fechamento de ciclo** (transição real `ABERTA → FECHADA` com snapshot): nunca como efeito
colateral de um `GET` (quebraria a convenção do projeto de que leitura nunca escreve).
Acontece na primeira vez que uma nova transação precisar resolver o *próximo* ciclo
(momento em que sabemos estruturalmente que o ciclo anterior já deveria estar fechado), ou
via um endpoint de ação explícito, chamável manualmente ou por uma tarefa agendada externa
(ex: scheduled tasks do Cowork), nunca embutido no próprio backend.

## Invariantes e prevenção de inconsistência

Novo `CheckConstraint` em `Transacao` (mesma família dos já existentes — "conta XOR
cartão", "no máximo um contrato"): `fatura_id` e `fatura_paga_id` nunca preenchidos ao
mesmo tempo na mesma linha — uma transação é ou uma compra num ciclo, ou um pagamento de um
ciclo, nunca as duas coisas.

`fatura_id`/`fatura_paga_id` nunca são aceitos do payload do cliente — sempre resolvidos
internamente pelo Service, mesma regra já aplicada a `usuario_id`. `UniqueConstraint(cartao_id,
mes_referencia)` já existente continua suficiente para impedir ciclos duplicados; nenhuma
mudança necessária ali.

## Fora de escopo (simplicidade deliberada)

Pagamento mínimo/juros rotativo, múltiplas moedas/câmbio, scheduler embutido no backend,
uma tabela nova de "PagamentoFatura" separada de `Transacao` (reaproveitar `Transacao`
mantém "toda movimentação real de dinheiro passa por Transacao" como princípio único).

## Mudanças de modelagem necessárias antes da implementação

1. Remover `Fatura.transacao_pagamento_id` (FK singular, `use_alter=True`); adicionar
   `Transacao.fatura_paga_id` (nullable, mesma forma de `fatura_id`).
2. Novo `CheckConstraint` em `Transacao`: `fatura_id` e `fatura_paga_id` nunca preenchidos
   juntos.
3. `PARCIALMENTE_PAGA`/`PAGA`/`ATRASADA` tratados como valores derivados no Service/Schema,
   nunca gravados na coluna `status` — decisão de Service, não muda o enum `StatusFatura`
   em si.
4. Nenhuma mudança necessária em `Cartao`, `Parcelamento`, `Financiamento`, `Emprestimo`.
5. Observação de baixo custo, não bloqueante: aproveitar a migration que mexe em
   `Transacao` (para `fatura_paga_id`) para também adicionar `index=True` em
   `Transacao.fatura_id` — mesma categoria de achado já registrada para `conta_id`/
   `cartao_id`/`categoria_pai_id` em revisões anteriores; não obrigatório resolver agora.

## Conclusão

Arquitetura validada. Nenhuma mudança retroativa é necessária em `Conta`, `Categoria`,
`Tag` ou `Cartão` — o CRUD de Cartão já foi construído prevendo este cálculo
(`somar_gastos_nao_pagos` já ignora `Transacao.status` e já considera `Fatura.status !=
PAGA`). Pronta para servir de base à implementação do CRUD de `Fatura`.
