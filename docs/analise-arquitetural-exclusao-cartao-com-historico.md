# Exclusão de Cartão com histórico — Análise Arquitetural

## Situação encontrada

`CartaoService.excluir()` (hard delete, Etapa F10) bloqueia com `BusinessRuleError`
sempre que o cartão tem qualquer fatura vinculada, em qualquer status — a única saída
oferecida ao usuário era desativar (soft delete) em vez de excluir.

Pedido explícito do usuário: ao tentar excluir um cartão com fatura vinculada, oferecer
a opção de excluir tudo junto — faturas E as transações feitas com aquele cartão
(despesas/compras, inclusive parceladas). Diferente do padrão usado em toda outra
exclusão do projeto até hoje (Fatura, Financiamento, Empréstimo: sempre *desvincula*
a transação, nunca apaga) — aqui o pedido explícito é apagar de verdade. Confirmado
com o usuário via pergunta direta antes de implementar (opção escolhida: "Apagar as
transações também", não "desvincular").

## Decisão

`CartaoService.excluir()` ganha um parâmetro opcional `apagar_transacoes: bool = False`:

- `False` (padrão, comportamento inalterado): continua bloqueando com o mesmo erro de
  antes se houver fatura vinculada.
- `True`: em vez de bloquear, executa a cascata abaixo, reaproveitando 100% de Services
  já existentes (nenhuma query nova, nenhuma regra duplicada):

  1. Para cada Fatura do cartão (`FaturaService.listar`): `FaturaService.excluir()` —
     método já existente que desvincula (`fatura_id`/`fatura_paga_id = NULL`) toda
     transação ligada àquele ciclo e apaga a fatura. Isso já preserva corretamente
     qualquer transação de PAGAMENTO (`fatura_paga_id`, sempre uma transação de
     *Conta*, dinheiro real que já saiu do banco) — ela nunca é apagada, só perde a
     referência à fatura que deixou de existir.
  2. Para cada Transação do cartão (`TransacaoService.listar(cartao_id=...)`):
     `TransacaoService.excluir()` — mesmo método que a tela de Transações já usa.
     Como o passo 1 já zerou `fatura_id` de toda transação de compra deste cartão,
     `_impedir_escrita_em_fatura_fechada` (a única trava que existiria aqui) nunca
     dispara — nenhuma trava nova precisou ser criada ou contornada. Se a transação
     pertencer a um Parcelamento, `excluir()` já delega para
     `cancelar_parcelas_do_parcelamento` (mesmo método usado por
     `ParcelamentoService.cancelar()`), que apaga as parcelas e marca
     `Parcelamento.ativo = False` — o cabeçalho do Parcelamento nunca é apagado
     fisicamente (mesmo padrão que cancelar um parcelamento já usa hoje, mesmo com o
     cartão ainda ativo); fica inativo e some das listagens padrão
     (`apenas_ativos=True`), igual a qualquer outro parcelamento cancelado.
     Como uma chamada a `excluir()` pode cascatear e apagar outras parcelas do mesmo
     Parcelamento antes do loop chegar nelas, cada iteração ignora `NotFoundError`
     (transação já removida por uma chamada anterior).
  3. `CartaoRepository.delete(cartao)` — igual ao fluxo já existente.

  Anexos de cada transação são removidos automaticamente pelo SQLAlchemy
  (`Transacao.anexos` já declara `cascade="all, delete-orphan"` — funciona no nível do
  ORM, independente do SQLite deste projeto nunca ligar `PRAGMA foreign_keys=ON`, ver
  comentário em `fatura_repository.py::desvincular_transacoes`).

`CartaoService` passa a depender também de `TransacaoService` (mesmo padrão já usado
para `FaturaService`: Service depende de Service, nunca acessa Repository de outro
domínio diretamente). Sem risco de dependência circular — `TransacaoService` não
depende de `CartaoService`.

Rota `DELETE /cartoes/{id}/permanente` ganha o parâmetro de query opcional
`apagar_transacoes` (default `false`), repassado direto ao Service.

Frontend: ao tentar excluir um cartão e receber o erro de fatura vinculada, o usuário
agora vê uma segunda confirmação, mais explícita sobre a perda de dados ("isso vai
apagar N fatura(s) e as transações feitas neste cartão, permanentemente"), e só então
a exclusão é refeita com `apagar_transacoes=true`.

## Bug encontrado durante a implementação (corrigido)

Testando a cascata com uma compra parcelada no cartão, `cartao_repo.delete(cartao)`
passou a levantar `IntegrityError: CHECK constraint failed: ck_parcelamento_cartao_xor_conta`.

Causa: mesmo sem nenhum `cascade` declarado em `Cartao.parcelamentos`/
`Cartao.contas_recorrentes` (`app/models/cartao.py`), o SQLAlchemy ORM, por padrão,
tenta ZERAR o `cartao_id` de qualquer `Parcelamento`/`ContaRecorrente` relacionado
*carregado na sessão* antes de apagar o Cartao - comportamento do unit-of-work do
SQLAlchemy, independente do SQLite deste projeto nunca ligar
`PRAGMA foreign_keys=ON`. Como `Parcelamento`/`ContaRecorrente` exigem
`cartao_id XOR conta_id` (nunca os dois nulos), zerar só o `cartao_id` quebra a
CHECK. Isso já era um bug latente antes desta sprint (bastava um `ContaRecorrente`
vinculado ao cartão, sem nenhuma fatura, para o `excluir()` original quebrar do mesmo
jeito) - só ficou visível agora porque a cascata `apagar_transacoes=True` é o primeiro
fluxo a de fato chegar em `cartao_repo.delete()` com um Parcelamento ainda vinculado
ao cartão (histórico antes bloqueava sempre, via `existe_fatura_vinculada`).

Correção: `passive_deletes=True` nas duas relações (`parcelamentos`,
`contas_recorrentes`) em `Cartao` - desliga essa "limpeza" automática do lado do
Python. `Parcelamento`/`ContaRecorrente` nunca são apagados fisicamente por esta
cascata (mesmo padrão de sempre: `Parcelamento.ativo` já vira `False` via
`cancelar_parcelas_do_parcelamento`); ficam com uma referência "pendurada" a um
cartão que não existe mais - mesmo trade-off já aceito e documentado acima para o
`cartao_id` do Parcelamento após a exclusão.
