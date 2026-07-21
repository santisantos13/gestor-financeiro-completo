# Revisão técnica — CRUD de Financiamento

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.**

## Resumo

Segue `Router → Service → Repository`, compondo `TransacaoService` (nunca `TransacaoRepository`
diretamente para escrita) exatamente como `ParcelamentoService`/`ContaRecorrenteService` já
faziam. Reaproveita `ContratoCreditoMixin` sem alteração. Cronograma PRICE/SAC é função pura dos
campos imutáveis do contrato, recalculada quando necessário (criação e pagamento), sem colunas
novas de juros/amortização por parcela. As duas decisões arquiteturais que ficaram em aberto na
análise foram implementadas exatamente como aprovado: pagamento de parcela exclusivo pela ação
dedicada (`POST /financiamentos/{id}/parcelas/{numero_parcela}/pagar`), e obrigatoriedade de
`conta_id` validada só no Service, sem tocar a nullability do `ContratoCreditoMixin` (que também
afeta o ainda não implementado Empréstimo). 586 testes passam no total (355 unitários, 231 de
integração) — 37 unitários novos de `FinanciamentoService`, mais os acréscimos em
`TransacaoService` (posse/faixa/duplicidade de `financiamento_id`, bloqueio de `status`,
`marcar_parcela_de_contrato_paga`) e 20 de integração novos do fluxo de Financiamento.

## Problema real encontrado e corrigido nº 1: ordem de precedência em `criar()`

Encontrado durante a própria implementação, antes mesmo da revisão final formal — ao escrever os
testes unitários de `TransacaoService.criar()` para transação de financiamento. A regra "parcela
de contrato de crédito sempre nasce PENDENTE" havia sido colocada ANTES do bloco que resolve
conta/cartão. Como esse bloco força `status = PAGO` incondicionalmente sempre que `cartao_id` é
informado, um payload (estruturalmente incomum, mas não proibido pelo schema genérico de
`Transacao`/`TransacaoCreate`, já que `ContratoCreditoMixin` não tem `cartao_id`) combinando
`cartao_id` + `financiamento_id` fazia o PAGO do cartão sobrescrever silenciosamente o PENDENTE
do contrato. Corrigido movendo a checagem de `financiamento_id`/`emprestimo_id` para rodar por
último, depois do ramo conta/cartão, com comentário no código explicando por quê. Coberto por
teste unitário dedicado.

## Problema real encontrado e corrigido nº 2: estado pré-merge em `atualizar()` (achado central da revisão)

Este foi o achado mais sério da revisão crítica final — uma falha de segurança/consistência, não
um problema cosmético. `TransacaoService.atualizar()` tem um guard que bloqueia edição de
`status` numa transação vinculada a financiamento/empréstimo, para proteger `saldo_devedor`
(campo armazenado, só decrementado por `FinanciamentoService.pagar_parcela()`) de desincronizar.
Na primeira versão, esse guard checava `transacao.financiamento_id`/`transacao.emprestimo_id` —
os valores JÁ EXISTENTES na transação antes do PATCH, e não os valores que o PATCH estava prestes
a gravar.

O efeito prático: um único `PATCH /transacoes/{id}` com payload
`{"financiamento_id": 1, "numero_parcela": 1, "status": "PAGO"}`, enviado contra uma transação de
conta comum (sem nenhum vínculo prévio a contrato), passava pelo guard sem erro — porque o valor
antigo de `financiamento_id` ainda era `None` no momento da checagem —, `_validar_financiamento`
validava e aceitava o novo vínculo, e o `setattr` final aplicava as duas mudanças
(`financiamento_id` novo E `status=PAGO`) atomicamente numa única chamada. Resultado: uma parcela
marcada PAGA sem nunca passar por `marcar_parcela_de_contrato_paga()`, e `saldo_devedor`
permanentemente desincronizado — exatamente o cenário que Conflito 1 da análise arquitetural
existia para prevenir.

Corrigido recalculando `parcelamento_id`, `numero_parcela`, `financiamento_id` e `emprestimo_id`
mesclados (payload sobre estado existente) ANTES do guard de `status`, e checando o guard contra
esses valores mesclados — não contra o estado anterior isolado. `_validar_estrutura()` passou a
usar as mesmas variáveis já computadas, eliminando também uma pequena duplicação onde
`emprestimo_id` mesclado era calculado inline só para essa chamada. Regression test dedicado:
`test_atualizar_vinculando_financiamento_e_status_pago_na_mesma_chamada_levanta_business_rule_error`,
que reproduz exatamente o payload combinado acima e confirma `BusinessRuleError`.

## Cronograma PRICE/SAC: matemática confirmada por invariantes, não por valores fixos

`FinanciamentoService._gerar_cronograma_price`/`_gerar_cronograma_sac` são funções puras testadas
por invariantes matemáticos (mais robusto que fixar um valor esperado de calculadora externa):
soma exata das amortizações igual ao principal (garantida pelo truque "última parcela absorve o
resto", mesmo usado em `ParcelamentoService._dividir_valor`), parcela PRICE fixa em todas exceto
a última, amortização SAC constante em todas exceto a última (com parcela SAC estritamente
decrescente, já que os juros decrescem sobre saldo decrescente), PRICE degenera para divisão
simples quando `taxa_juros=0`, e uma checagem de regressão cruzada confirmando que SAC sempre
paga menos juros totais que PRICE para o mesmo principal/prazo/taxa (propriedade financeira
conhecida, boa forma de pegar um erro de sinal ou de fórmula que os testes isolados por sistema
não pegariam sozinhos).

## Entrada como transação separada: verificado que não corrompe a contagem de parcelas

`valor_entrada` (quando informado) gera uma `Transacao` avulsa, sem `financiamento_id`/
`numero_parcela` — testado que ela nunca aparece na lista filtrada por `financiamento_id`, e que
o número de parcelas restantes/geradas continua batendo com `num_parcelas` do contrato
independente de ter entrada ou não. Testado também que `valor_entrada >= valor_financiado` é
rejeitado (`BusinessRuleError`, 422) antes de qualquer escrita no banco.

## Pagamento de parcela: ação dedicada, PATCH genérico bloqueado — verificado nos dois lados

`POST /financiamentos/{id}/parcelas/{numero_parcela}/pagar` é o único caminho capaz de marcar uma
parcela como PAGA — delega para `TransacaoService.marcar_parcela_de_contrato_paga()` (o mesmo
método interno que também seria usado por um futuro `EmprestimoService`) e depois decrementa
`saldo_devedor` pela amortização daquela parcela específica (recalculada via o mesmo cronograma
usado na geração), nunca por uma fração ingênua do valor total. Testado: faixa de
`numero_parcela` (1..num_parcelas), posse cruzada (404 para financiamento de outro usuário),
pagamento duplicado da mesma parcela (422), transição para `QUITADO` tanto no caso normal (última
parcela) quanto no caso de pagamento fora de ordem que zera `saldo_devedor` antes da última
parcela numerada. Do outro lado, testado via integração HTTP completa que
`PATCH /transacoes/{id}` com `status` em transação de financiamento devolve 422 e que
`saldo_devedor` permanece inalterado após a tentativa — o teste que teria capturado o problema nº
2 acima se já existisse antes da implementação inicial.

## `conta_id` obrigatório: validado só no Service, como combinado

Confirmado que a obrigatoriedade vive inteiramente em
`FinanciamentoService._validar_conta_obrigatoria()`, chamada em `criar()` antes de qualquer
escrita. `ContratoCreditoMixin.conta_id` permanece `nullable=True` no banco, sem nenhuma
`CheckConstraint`/`NOT NULL` nova — decisão explícita para não acoplar essa regra ao Empréstimo
antes de esse CRUD existir. Testado que omitir `conta_id` no payload de criação devolve 422 com
mensagem clara, nunca um erro de banco.

## Migração: sem drift real, mas com um detalhe que merece transparência total

`alembic upgrade head` → `downgrade -1` → `upgrade head` validado limpo num banco descartável. A
migração real (`441dd71b0fe8`) adiciona
`UniqueConstraint(financiamento_id, numero_parcela)` em `Transacao` via `batch_alter_table`, mesma
estratégia já usada para a constraint equivalente de Parcelamento. `alembic check` confirma "No
new upgrade operations detected." contra o head atual.

O detalhe a documentar: o histórico de migrações inclui três arquivos com nomes fora do padrão
usual do projeto —`zzz_dummy_test.py` (revisão `aaaa0000dummy`), `0fecbf64f7db_drift_check.py` e
`8b100b274a2e_final_drift_check.py` (head atual). Eles não existem por decisão de design — são
artefato de uma limitação do ambiente desta sessão de trabalho: o sistema de arquivos usado não
permite excluir arquivos via terminal (nem `rm`, nem operações equivalentes), só truncar
conteúdo. Em algum momento da verificação de drift, `alembic revision --autogenerate` (que sempre
cria um arquivo, mesmo quando não há diferença real a registrar) foi usado por engano em vez de
`alembic check` (que não cria arquivo nenhum). Como o arquivo criado não podia ser apagado, a
solução foi neutralizá-lo: reescrever seu conteúdo para um upgrade/downgrade genuinamente vazios
(`pass`/`pass`), documentar no próprio docstring do arquivo que é um resíduo transparente dessa
limitação, e encadeá-lo corretamente via `down_revision` na sequência real de migrações. Isso
aconteceu três vezes seguidas até a verificação de drift ser refeita corretamente com
`alembic check`. O resultado é um histórico com três migrações vazias e devidamente documentadas,
mas com zero risco: nenhuma delas altera schema, `alembic upgrade head`/`downgrade` funcionam de
ponta a ponta, e `alembic check` contra o head confirma zero drift real pendente.

## O que foi deliberadamente NÃO implementado

Confirmado por leitura do código final: nenhuma menção a renegociação, refinanciamento,
amortização extraordinária, carência, juros variáveis/indexadores (IPCA/CDI), seguros ou multas.
`cet` e `permite_quitacao_antecipada` existem no model e no schema de criação, mas não são lidos
em nenhuma regra de negócio — persistidos e devolvidos, YAGNI respeitado. `INADIMPLENTE` e
qualquer ação de cancelamento não têm nenhum caminho de código que os produza; a única transição
de status implementada é `ATIVO → QUITADO`, automática.

## Conclusão

A implementação segue a arquitetura aprovada, reaproveita `ContratoCreditoMixin` e
`TransacaoService` sem duplicar regras, e respeita as duas decisões de conflito exatamente como
aprovadas pelo usuário. Dois problemas reais foram encontrados e corrigidos durante o próprio
trabalho: um bug de ordenação em `criar()` (achado durante a escrita dos testes unitários,
corrigido antes da revisão formal) e um bug de estado pré-merge em `atualizar()` (achado durante
a revisão final, o mais sério dos dois — abria uma via real para desincronizar `saldo_devedor`
via um único PATCH malicioso ou acidental). Ambos têm regression test dedicado. A migração inclui
três arquivos de nome atípico, cuja origem (limitação de exclusão de arquivo do ambiente desta
sessão, não uma decisão de design) está documentada tanto nos próprios arquivos quanto aqui, sem
nenhum impacto real no schema ou no funcionamento do Alembic. Nenhum outro problema de
arquitetura, regra de negócio, consistência ou segurança foi encontrado.
