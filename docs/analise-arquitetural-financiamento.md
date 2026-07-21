# Análise arquitetural — Financiamento

Análise de modelagem prévia à implementação do CRUD de `Financiamento`, seguindo o mesmo
rigor de `docs/analise-arquitetural-parcelamento.md` e
`docs/analise-arquitetural-conta-recorrente.md`. Apresentada em chat antes de qualquer
código, com dois conflitos reais levados ao usuário para decisão (não resolvidos
unilateralmente). **Status: aprovada, ambos os conflitos resolvidos pelo usuário.**

## Reuso de `ContratoCreditoMixin`

Sem alteração nenhuma no mixin. `Financiamento` já herda `instituicao_financeira`,
`taxa_juros`, `sistema_amortizacao`, `num_parcelas`, `saldo_devedor`, `status`, `conta_id`,
`categoria_id` do jeito que estão. `cet` e `permite_quitacao_antecipada` ficam persistidos
mas **sem nenhuma regra construída em cima** nesta etapa — quitação antecipada é
"funcionalidade bancária avançada" pelo critério de exclusão explícito do usuário. Mesmo
princípio já aplicado a `TipoRecorrencia`: o campo existe no model, o Service não constrói
regra incompleta em cima dele até ter utilidade real.

## O que reaproveita de Parcelamento, o que não reaproveita

Reaproveita a **forma** de `ParcelamentoService._gerar_parcelas`: criar o cabeçalho, gerar
N `Transacao` via `TransacaoService.criar()` na mesma Unit of Work (eager, não lazy -
`num_parcelas`/`data_inicio`/`valor_financiado` são conhecidos de imediato, mesma
justificativa já usada para Parcelamento), mesmo rollover de data via
`dia_valido`/`proximo_mes` de `app/core/datas.py`, sem nenhuma cópia paralela.

Não reaproveita o cálculo de valor. `ParcelamentoService._dividir_valor` é divisão simples
(resto na última parcela) - regra de "compra parcelada sem juros formal". Financiamento
precisa de amortização real (PRICE ou SAC), lógica nova que não existia em nenhum lugar do
código. Nenhuma abstração comum foi criada entre os dois cálculos - são fórmulas
genuinamente diferentes; forçar uma interface compartilhada seria overengineering.

Também não reaproveita XOR cartão/conta: `ContratoCreditoMixin` não tem `cartao_id` (um
financiamento não é comprado no cartão). A única checagem estrutural é "`conta_id` precisa
existir".

## Como gerar as parcelas via Transacao

**PRICE** (parcela fixa): com `PV = valor_financiado − valor_entrada` (ou apenas
`valor_financiado` se não houver entrada) e `i = taxa_juros`, `PMT = PV × i / (1 − (1+i)^-n)`.
Cada parcela `k` decompõe em `juros_k = saldo_k-1 × i` e `amortizacao_k = PMT − juros_k`,
com `saldo_k = saldo_k-1 − amortizacao_k`.

**SAC** (amortização constante): `amortizacao = PV / n` (fixa), `juros_k = saldo_k-1 × i`
(decrescente), `valor_k = amortizacao + juros_k` (parcela decrescente).

O cronograma é **função pura** dos campos já persistidos no contrato (`valor_financiado`,
`valor_entrada`, `taxa_juros`, `num_parcelas`, `sistema_amortizacao`) - nenhuma coluna nova
de juros/amortização por parcela. O cronograma inteiro (`list[tuple[valor, amortizacao]]`,
O(n), trivial mesmo para 30 anos de parcelas) é recalculado sempre que necessário, tanto na
geração inicial quanto depois, ao processar o pagamento de uma parcela específica - a mesma
técnica de "última parcela absorve o resto" de `_dividir_valor` garante soma exata (sem
sobra de centavo no saldo final).

`valor_entrada`, se houver, vira uma `Transacao` avulsa separada (DESPESA, sem
`financiamento_id`/`numero_parcela`) - não uma "parcela zero". Decisão deliberada: se
carregasse `financiamento_id`, corromperia a conta "parcelas restantes = `num_parcelas` −
pagas" que a Central Financeira já espera (`docs/central-financeira-especificacao.md`,
seção 4).

## Fonte da verdade

Mesmo padrão de Parcelamento/ContaRecorrente: `Financiamento` é o cabeçalho/contrato;
`Transacao` (com `financiamento_id`) é a fonte da verdade de saldo e relatórios - nenhuma
mudança em `ContaRepository.somar_transacoes_pagas`, que já soma qualquer `Transacao PAGO`
independente da origem. Única exceção documentada é `saldo_devedor`, já armazenado por
decisão prévia (justificada em `mixins.py`: PRICE/SAC não permite derivar saldo devedor por
"total menos pago" sem rodar a fórmula inteira). Nenhuma inconsistência aqui - decisão já
tomada, só confirmada.

## Conflito 1 (resolvido): quem pode marcar uma parcela como paga

`status` de uma `Transacao` era editável via `PATCH /transacoes/{id}` genérico. Se uma
parcela de financiamento virasse `PAGO` por esse caminho, nada atualizaria
`saldo_devedor` - e `TransacaoService` não pode depender de `FinanciamentoService` (criaria
dependência circular, já que `FinanciamentoService` depende de `TransacaoService` para
gerar as parcelas).

**Decisão do usuário: aprovada.** `PATCH /transacoes/{id}` passa a bloquear edição de
`status` quando `financiamento_id is not None` (mesma família de guarda que já existe para
`cartao_id is not None`, só que bloqueando em vez de forçar um valor fixo). O pagamento de
parcela vira ação dedicada, `POST /financiamentos/{id}/parcelas/{numero_parcela}/pagar`,
dentro de `FinanciamentoService`: chama `TransacaoService` para virar o status daquela
parcela para `PAGO`, recalcula a amortização daquele número de parcela via o cronograma
determinístico, decrementa `saldo_devedor`, e - se era a última parcela ou `saldo_devedor`
chegou a zero - transiciona `status` do contrato para `QUITADO`. Mesmo espírito
arquitetural já usado em Fatura (pagamento por ação dedicada, não PATCH genérico,
justamente para proteger um agregado calculado/armazenado).

## Conflito 2 (resolvido): nullability de `conta_id` no mixin

`ContratoCreditoMixin.conta_id` é `nullable=True`, mas toda `Transacao` exige `conta_id
XOR cartao_id`, e Financiamento/Empréstimo não têm opção de cartão - sem `conta_id`
preenchido é estruturalmente impossível gerar qualquer parcela.

**Decisão do usuário: aprovada, sem mudança no banco agora.** O `nullable=True` do mixin
permanece como está - `ContratoCreditoMixin` é compartilhado com `Emprestimo`, que ainda
não teve sua própria análise; mudar a coluna no banco mexeria nas duas tabelas sem validar
os requisitos de Empréstimo. `FinanciamentoService.criar()` valida explicitamente
`conta_id is not None` (`BusinessRuleError` se faltar) - mesma técnica já usada em vários
lugares para devolver erro de negócio antes de bater numa restrição de banco. Quando o CRUD
de Empréstimo existir, os dois contratos são revisados juntos e, se fizer sentido, uma
única migration consolida a regra no banco para os dois.

## Encerramento do contrato e histórico

`StatusContratoCredito` é ATIVO/QUITADO/INADIMPLENTE - não é o padrão `ativo: bool` de
soft delete usado em Conta/Categoria/Parcelamento. Nesta etapa, só a transição ATIVO →
QUITADO é implementada, automática, disparada dentro de `pagar_parcela()` quando a última
parcela é quitada. `INADIMPLENTE` fica sem transição própria (exigiria comparar vencimento
com "hoje", o tipo de lógica de scheduler que o projeto já decidiu evitar) - mesmo
raciocínio já aprovado para `FrequenciaRecorrencia`: o enum existe, o Service só implementa
o que tem utilidade real agora.

Nenhum `cancelar()` como o de Parcelamento (que desfaz parcelas futuras) foi implementado -
não foi pedido, e "desistir do meio do contrato" preservando consistência de
`saldo_devedor` cai em amortização extraordinária/renegociação, ambos excluídos
explicitamente. Sem essa ação, o histórico se preserva sozinho: nenhuma `Transacao` de
financiamento é apagada, e o cabeçalho nunca é hard-deleted. Evolução futura de domínio, se
necessária - não código antecipado.

## Mudanças de modelagem necessárias

1. `FinanciamentoRepository` novo (mesmo padrão de `ParcelamentoRepository`, com
   `listar_do_usuario` filtrando por `status != QUITADO` em vez de um booleano `ativo`, já
   que a entidade não tem esse campo).
2. Nova `UniqueConstraint(financiamento_id, numero_parcela)` em `Transacao`, proativamente -
   mesma lição já aplicada duas vezes (Parcelamento e ContaRecorrente) em vez de esperar
   descobrir o mesmo bug de novo.
3. `TransacaoService` ganha `_validar_financiamento()` (posse + faixa + duplicidade de
   `numero_parcela`), fechando a lacuna YAGNI que o próprio docstring do Service já previa
   para este campo.
4. `TransacaoService` bloqueia edição de `status` quando `financiamento_id` está
   preenchido (Conflito 1).
5. `FinanciamentoService.criar()` valida `conta_id is not None` no próprio Service
   (Conflito 2).
6. Sem `FinanciamentoUpdate` - mesmo motivo de Parcelamento/Fatura: todo campo estrutural
   determina o cronograma inteiro, editar depois de gerado desincroniza tudo.

## Resumo do escopo excluído (confirmado)

Renegociação, refinanciamento, amortização extraordinária, carência, juros variáveis,
indexadores, seguros, multas: nenhum desses tem campo, rota ou lógica. `INADIMPLENTE` e
cancelamento de contrato: fora desta etapa pelos motivos acima, não esquecimento.

## Conclusão

Arquitetura validada, com dois conflitos reais identificados e resolvidos explicitamente
pelo usuário antes de qualquer código. Nenhuma abstração nova além do que já existia para
Parcelamento - mesma composição de Services, mesmo padrão de geração eager. A lógica
genuinamente nova (amortização PRICE/SAC) fica isolada em `FinanciamentoService`, como
função pura sobre os campos do contrato, sem nenhuma coluna nova. Pronta para servir de
base à implementação do CRUD de `Financiamento`.
