# Exclusão de Conta com histórico — Análise Arquitetural

## Situação encontrada

`ContaService.excluir()` (hard delete, Etapa F10) bloqueia com `BusinessRuleError`
sempre que `ContaRepository.existe_vinculo()` encontra qualquer Transacao, Transferencia
(origem ou destino) ou Cartão vinculado a ela — a única saída era desativar (soft
delete).

Pedido explícito do usuário: essa restrição não deve mais ser um bloqueio definitivo —
ele quer poder excluir a Conta junto com tudo que estiver vinculado a ela, mesmo padrão
já confirmado e implementado para Cartão (`docs/analise-arquitetural-exclusao-cartao-com-historico.md`):
apagar de verdade, não só desvincular.

## Gap encontrado em `existe_vinculo()` (bug pré-existente, independente deste pedido)

`existe_vinculo()` só verifica Transacao/Transferencia/Cartão. Ela NÃO verifica
`Financiamento.conta_id`, `Emprestimo.conta_id`, `ContaRecorrente.conta_id` nem
`Parcelamento.conta_id` — ou seja, hoje já é possível (bug) excluir definitivamente
uma Conta que ainda está referenciada por um contrato de Financiamento/Empréstimo ou
por um template de ContaRecorrente/Parcelamento vinculado à conta (não ao cartão).
Corrigido nesta mesma mudança, ampliando `existe_vinculo()` para cobrir os quatro.

`Meta.conta_id` fica de fora dessa checagem de propósito: ali a relação é invertida
— é a própria Meta que é "dona" de uma Conta dedicada (o "cofrinho" oculto,
`Conta.oculta=True`), nunca o contrário. Uma Conta comum do usuário nunca deveria ser
apontada por uma Meta. Em vez de tentar apagar o cofrinho por aqui (o que corromperia o
estado da Meta), `ContaService.excluir()` passa a bloquear INCONDICIONALMENTE (mesmo
com `apagar_vinculos=True`) quando `conta.oculta` é `True`, orientando a excluir a
Meta em vez da conta — a Meta já tem seu próprio fluxo de exclusão que decide o
destino correto do cofrinho (`MetaService.excluir` → `_encerrar_cofrinho`).

## Decisão

`ContaService.excluir()` ganha um parâmetro opcional `apagar_vinculos: bool = False`:

- Conta oculta (cofrinho de Meta): sempre bloqueia, independente do parâmetro —
  "Esta conta é o cofrinho de uma Meta e não pode ser excluída diretamente. Exclua a
  Meta em vez disso."
- `False` (padrão, comportamento inalterado nas demais contas): continua bloqueando
  com o mesmo erro de antes se houver qualquer vínculo (lista ampliada acima).
- `True`: em vez de bloquear, executa a cascata abaixo, reaproveitando 100% de
  Services já existentes (nenhuma regra de negócio duplicada):

  1. **Financiamento** (`FinanciamentoService.listar` + `.excluir()` por contrato
     vinculado a esta conta) — método já existente: desvincula
     `financiamento_id`/`numero_parcela` de cada parcela antes de apagar o contrato,
     preservando as parcelas como Transacao avulsa (ainda com `conta_id` apontando
     para esta conta — recolhidas no passo 6 abaixo).
  2. **Empréstimo** — espelha o passo 1, via `EmprestimoService.excluir()`.
  3. **ContaRecorrente** — método NOVO, `ContaRecorrenteService.excluir()` (não
     existia nenhum hard delete para este model ainda): apaga o template
     diretamente. Não precisa desvincular nada antes — `Transacao.origem_recorrente_id`
     não tem nenhuma CHECK constraint amarrada a ele (diferente de
     financiamento_id/emprestimo_id/parcelamento_id, que têm
     `ck_transacao_numero_parcela_condiz_com_contrato`) — as ocorrências já geradas
     ficam com uma referência "pendurada" a um template que não existe mais, sem
     nenhum problema de integridade.
  4. **Cartão** (`CartaoService.listar` + `.excluir(..., apagar_transacoes=True)` por
     cartão cuja `conta_pagamento_id` é esta conta) — reaproveita a cascata inteira já
     implementada para Cartão (apaga faturas e transações do cartão junto). Não existe
     "trocar a conta de pagamento de um cartão" no sistema, então preservar o Cartão
     sem uma conta de pagamento não é uma opção válida.
  5. **Transferencia** — método NOVO, `TransferenciaService.excluir()` (só existia
     `cancelar()`, soft delete): apaga fisicamente cada transferência em que esta conta
     é origem OU destino.
  6. **Transacao** (`TransacaoService.listar(conta_id=...)` + `.excluir()` por
     transação) — mesmo método que a tela de Transações já usa. Reúne tanto as
     transações "nativas" da conta quanto as parcelas de Financiamento/Empréstimo que
     os passos 1-2 desvincularam (ainda têm `conta_id` preenchido). Delega
     automaticamente para `cancelar_parcelas_do_parcelamento` quando a transação
     pertence a um Parcelamento (mesmo comportamento já usado na cascata de Cartão) —
     cobre tanto parcelamento de cartão quanto de conta. `NotFoundError` é ignorado
     (mesma tolerância a corrida de cascata já usada na exclusão de Cartão).
  7. `ContaRepository.delete(conta)` — igual ao fluxo já existente.

## Bug de `passive_deletes` (mesma classe do já corrigido em Cartão)

Igual ao que aconteceu com `Cartao.parcelamentos`/`Cartao.contas_recorrentes`
(`docs/analise-arquitetural-exclusao-cartao-com-historico.md`): nenhuma das relações em
`Conta` (`cartoes`, `transacoes`, `parcelamentos`, `financiamentos`, `emprestimos`,
`contas_recorrentes`, `metas`, `transferencias_enviadas`, `transferencias_recebidas`)
tinha `passive_deletes=True`. Sem isso, o SQLAlchemy ORM tentaria zerar o `conta_id` de
qualquer linha relacionada carregada na sessão antes de apagar a Conta — quebrando
`ck_transacao_conta_xor_cartao`/`ck_parcelamento_cartao_xor_conta`/
`ck_conta_recorrente_cartao_xor_conta` (mesma família de CHECK XOR) e as colunas
`NOT NULL` de `Transferencia.conta_origem_id`/`conta_destino_id`/
`Cartao.conta_pagamento_id`/`Meta.conta_id`. Corrigido adicionando
`passive_deletes=True` em TODAS as relações de `Conta` — a cascata acima já apaga (ou
já apagou) explicitamente cada linha relacionada antes de chegar em
`conta_repo.delete()`; qualquer referência que ainda assim sobrar (ex: um
Financiamento/Empréstimo que por algum motivo não foi pego) fica "pendurada"
(dangling), mesmo trade-off já aceito e documentado para Cartão — nunca um crash.

## Frontend

Mesmo padrão já usado em `CartaoDetalhePage`/`CartoesPage`: ao tentar excluir uma
Conta e receber 422 (vínculo), uma segunda confirmação mais explícita aparece,
avisando que TUDO relacionado à conta (transações, transferências, cartões e seus
respectivos históricos, contratos de financiamento/empréstimo, recorrências) será
apagado permanentemente, e só então a exclusão é refeita com `apagar_vinculos=true`.
