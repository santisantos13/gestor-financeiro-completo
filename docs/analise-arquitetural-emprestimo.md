# Análise arquitetural — CRUD de Empréstimo

Formaliza as decisões já definidas pelo usuário para a implementação completa do CRUD de
Empréstimo, no mesmo estilo dos documentos anteriores (`docs/analise-arquitetural-financiamento.md`,
`docs/analise-arquitetural-parcelamento.md`). Diferente das entidades anteriores, aqui não há
conflito em aberto para resolver — o domínio já foi definido como "praticamente idêntico" ao de
Financiamento, com uma única diferença estrutural relevante (desembolso). Este documento existe
para deixar essa diferença e as decisões reaproveitadas explícitas antes do código.

## Reuso de `ContratoCreditoMixin`

`Emprestimo` (`app/models/emprestimo.py`) já herda `ContratoCreditoMixin` sem alteração —
mesmos campos de `Financiamento`: `instituicao_financeira`, `numero_contrato`, `taxa_juros`,
`sistema_amortizacao`, `num_parcelas`, `cet`, `data_inicio`, `saldo_devedor` (armazenado),
`permite_quitacao_antecipada`, `status` (`StatusContratoCredito`), `conta_id`, `categoria_id`.
Nenhuma coluna nova no mixin.

## A única diferença de domínio real: desembolso vs. entrada

Financiamento: o bem é pago diretamente ao vendedor/financeira — o dinheiro do `valor_financiado`
normalmente não passa pela conta do usuário. Só a entrada (opcional) gera uma `Transacao`.

Empréstimo: o valor liberado (`valor_liberado`, campo próprio de `Emprestimo`, obrigatório,
diferente de `valor_entrada` de Financiamento que é opcional) **entra** na conta do usuário no
momento da contratação — sempre, não é opcional. Por isso `EmprestimoService.criar()` sempre gera
uma `Transacao` de **RECEITA** avulsa (sem `emprestimo_id`/`numero_parcela`, mesmo raciocínio já
usado para a entrada de Financiamento: se carregasse o vínculo, corromperia a contagem de
"parcelas restantes") no valor de `valor_liberado`, além das parcelas de amortização (sempre
DESPESA, como em Financiamento). O principal amortizado pelo cronograma é o próprio
`valor_liberado` inteiro — não existe "entrada" a descontar em Empréstimo (o desembolso não reduz
o que precisa ser pago de volta, ao contrário da entrada de um financiamento).

## Cronograma PRICE/SAC: extraído para módulo compartilhado

Em vez de copiar `_gerar_cronograma_price`/`_gerar_cronograma_sac`/`_gerar_cronograma` de
`FinanciamentoService` para `EmprestimoService` (seria duplicar a mesma matemática pela segunda
vez, violando DRY), a função pura foi extraída para `app/core/amortizacao.py`
(`gerar_cronograma(principal, taxa_juros, num_parcelas, sistema)`), a mesma técnica já usada para
`app/core/datas.py` (rollover de datas compartilhado entre Parcelamento/Financiamento/
ContaRecorrente). `FinanciamentoService._gerar_cronograma` passa a ser um staticmethod fino que
delega para o módulo compartilhado — comportamento e assinatura idênticos aos já testados,
nenhuma regressão. `EmprestimoService._gerar_cronograma` delega da mesma forma.

## Fonte da verdade

Mesma decisão de Financiamento: nenhuma coluna nova de juros/amortização por parcela. O
cronograma é recalculado sempre que necessário (criação, pagamento) a partir dos campos
imutáveis do contrato (`valor_liberado`, `taxa_juros`, `num_parcelas`, `sistema_amortizacao`).

## Pagamento de parcela: ação dedicada (decisão já aprovada, reaplicada)

Mesma decisão de Conflito 1 de Financiamento: `POST /emprestimos/{id}/parcelas/{numero_parcela}/pagar`
é o único caminho para marcar uma parcela como paga. `TransacaoService.marcar_parcela_de_contrato_paga`
já é genérico o bastante para `emprestimo_id` (checa `financiamento_id is None and emprestimo_id
is None`) — nenhuma mudança necessária nesse método. O guard de `atualizar()` que bloqueia edição
de `status` também já cobre `emprestimo_id` desde a implementação de Financiamento (checagem
`financiamento_id is not None or emprestimo_id is not None` sobre o estado mesclado) — também
nenhuma mudança necessária ali.

## `conta_id` obrigatório: mesma decisão, agora consolidável

Financiamento já validava `conta_id` obrigatório só no Service (Conflito 2, decisão explícita de
não alterar a nullability de `ContratoCreditoMixin.conta_id` antes de Empréstimo existir "para
revisar os dois contratos juntos"). Agora que Empréstimo existe, a mesma validação
(`_validar_conta_obrigatoria`) é replicada em `EmprestimoService` com o mesmo raciocínio: uma
parcela de empréstimo não pode ser gerada sem uma conta de origem/destino. A nullability do
mixin **continua não alterada nesta etapa** — mudar para `NOT NULL` no banco exigiria uma
migration de dados para linhas hoje nulas (nenhuma existe em produção real ainda, mas a migration
ganharia complexidade sem necessidade prática); a validação em dois Services (com o mesmo texto
de regra) é redundância aceitável e já é o padrão estabelecido, não uma dívida nova.

## Fechamento do contrato

Mesma decisão de Financiamento: só a transição `ATIVO → QUITADO` é implementada, automática (na
última parcela numerada ou quando `saldo_devedor` chega a zero). `INADIMPLENTE` e qualquer ação
de cancelamento continuam fora de escopo.

## Posse de `emprestimo_id` em `TransacaoService`

Mesma lacuna YAGNI documentada no módulo desde a criação de `TransacaoService`, fechada agora que
`EmprestimoRepository` existe — mesmo padrão de `_validar_financiamento`:
`_validar_emprestimo(emprestimo_id, numero_parcela, usuario_id, transacao_id_excluir=None)`
valida posse, faixa (`1..num_parcelas`) e duplicidade (levantando `ConflictError`, com a
`UniqueConstraint(emprestimo_id, numero_parcela)` como rede de segurança do banco). Depois desta
etapa, `meta_id` é o único campo que resta na lista de vínculos manuais sem posse validada (não
tem CRUD/Repository próprio ainda).

## Nova constraint de banco

`UniqueConstraint(emprestimo_id, numero_parcela)` em `Transacao` — mesma família das constraints
já existentes para `parcelamento_id` e `financiamento_id`, aplicada proativamente (sem esperar
descobrir o mesmo bug pela terceira vez).

## Resumo do escopo excluído (confirmado)

Sem renegociação, refinanciamento, amortização extraordinária, carência, juros variáveis/
indexadores, seguros, multas, inadimplência, ou qualquer ação de cancelamento. `cet` e
`permite_quitacao_antecipada` seguem existindo no model/schema, mas não são lidos em nenhuma
regra de negócio (YAGNI, mesma decisão de Financiamento).

## Conclusão

Domínio praticamente idêntico a Financiamento, como pedido — mesma arquitetura Router → Service →
Repository, mesma composição de `TransacaoService`, mesmo mecanismo de `saldo_devedor`, mesma
ação dedicada de pagamento, mesmo padrão de bloqueio de PATCH e de validação de posse. A única
diferença real de negócio (desembolso como RECEITA obrigatória vs. entrada opcional como DESPESA)
é isolada em `EmprestimoService.criar()`; o cronograma de amortização foi extraído para
`app/core/amortizacao.py` para as duas entidades compartilharem a mesma implementação, em vez de
duplicá-la.
