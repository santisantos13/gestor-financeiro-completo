# Revisão técnica — CRUD de Conta Recorrente

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.**

## Resumo

Segue `Router → Service → Repository`. Duas mudanças de modelagem, ambas já previstas e
aprovadas na análise arquitetural: `CheckConstraint` de `conta_id` XOR `cartao_id` em
`ContaRecorrente`, e `UniqueConstraint(origem_recorrente_id, data)` em `Transacao`. 510 testes
passam no total (42 unitários novos de `ContaRecorrenteService`, 8 unitários novos em
`TransacaoService` para a validação de posse/duplicidade de `origem_recorrente_id`, 29 de
integração novos de `ContaRecorrenteService`, mais os 431 pré-existentes).

## Problema real encontrado e corrigido: `data_fim` anterior a `data_inicio`

Achado da revisão final (não fazia parte da análise original, surgiu ao caçar problemas antes
de fechar): nada impedia criar (ou editar) uma `ContaRecorrente` com `data_fim` anterior a
`data_inicio`. O efeito não era um erro visível — era pior: a recorrência era aceita
normalmente e **nunca gerava nenhuma ocorrência**, silenciosamente. Causa raiz:
`_gerar_ocorrencias_pendentes` calcula `limite = min(hoje, data_fim)`; se `data_fim` já é
anterior a `data_inicio`, `limite` fica sempre anterior à primeira data possível de gerar, e o
laço de geração nunca executa nem uma vez. Um template "morto por construção" sem nenhum
aviso ao usuário. Corrigido com `ContaRecorrenteService._validar_datas()`, chamada em `criar()`
e em `atualizar()` (contra o estado mesclado, mesmo raciocínio já usado para a validação
estrutural conta XOR cartão) — rejeita com `BusinessRuleError` (422) antes de persistir.
Testado em quatro níveis: unitário na criação, unitário na atualização (os dois sentidos —
mover `data_fim` para antes, e mover `data_inicio` para depois), e integração via HTTP nos
dois verbos (`POST`/`PATCH`).

## Geração lazy: fiel ao pedido, sem scheduler

Nenhum `cron`/scheduler/fila/background worker em nenhum lugar do código — confirmado por
grep no módulo inteiro. Os dois únicos gatilhos de geração (`criar()` e
`POST /{id}/gerar-ocorrencias-pendentes`) são síncronos, dentro do ciclo de vida normal de uma
requisição HTTP. `gerar_ocorrencias_pendentes()` é idempotente por construção: testado
explicitamente chamando a sincronização logo após uma criação que já gerou tudo até hoje —
retorna lista vazia, nenhuma chamada adicional a `TransacaoService.criar()`.

## Escopo de frequência: MENSAL respeitado de ponta a ponta

`ContaRecorrenteService._validar_frequencia_suportada()` rejeita `SEMANAL`/`ANUAL` tanto em
`criar()` quanto em `atualizar()` (quando o campo é enviado) — testado nos dois verbos, unitário
e integração. Nenhum campo novo foi adicionado ao model para suportar as outras frequências;
`app/core/datas.py` não foi tocado. Verificado que a mensagem de erro cita o valor recebido
(`"Frequência 'SEMANAL' ainda não é suportada..."`), não um erro genérico.

## Duplicidade de origem_recorrente_id: mesma dupla camada de Parcelamento

`TransacaoService._validar_conta_recorrente()` (posse + duplicidade de data) segue exatamente
o mesmo padrão de `_validar_parcelamento()` (posse + duplicidade de `numero_parcela`) — inclusive
o mesmo parâmetro `transacao_id_excluir` para `atualizar()` não conflitar consigo mesma.
Testado que editar `data` de uma transação vinculada a uma recorrência revalida a duplicidade
(não só na criação), e que editar mantendo a mesma data não levanta falso positivo. A
`UniqueConstraint(origem_recorrente_id, data)` no banco foi confirmada como rede de segurança
real: um `POST /transacoes` manual reivindicando uma data já usada por outra ocorrência da
mesma recorrência devolve `409` limpo (`ConflictError`), nunca um `IntegrityError` cru — a
mesma lição do bug de `numero_parcela` aplicada proativamente aqui, sem esperar descobrir de
novo.

## Migração: sem drift, ciclo completo validado

`alembic upgrade head` → `downgrade -1` → `upgrade head` executado limpo num banco descartável.
`alembic revision --autogenerate` rodado contra o schema pós-migração não detectou nenhuma
diferença. O `CheckConstraint` foi escrito à mão (autogenerate não detecta CheckConstraint,
limitação já conhecida); a `UniqueConstraint` foi detectada automaticamente. Ambas usam
`batch_alter_table`, mesma estratégia das migrações anteriores.

## Rollover e clamping de datas: reaproveitado, não reimplementado

`_gerar_ocorrencias_pendentes` usa exatamente `dia_valido`/`proximo_mes` de
`app/core/datas.py`, sem nenhuma cópia paralela da lógica. Testado explicitamente: clamping de
dia 31 em fevereiro (28 e 29, incluindo o caso de mês mais curto do ano), rollover de
dezembro→janeiro com virada de ano, e o caso central de que a próxima data é sempre calculada a
partir da ÚLTIMA ocorrência gerada — mudar `dia_vencimento` no meio do caminho só afeta
gerações futuras, nunca reescreve datas já geradas (testado unitariamente via chamada direta ao
método privado, a única forma de controlar deterministicamente "hoje" sem introduzir uma
dependência de mocking de tempo só para isso).

## PATCH: a divergência deliberada do padrão, verificada como segura

Diferente de Fatura/Parcelamento/Transferência (sem `Update`), `ContaRecorrenteUpdate` existe.
Testado que editar `valor`/`descricao`/`categoria_id` no template NÃO altera retroativamente
ocorrências já geradas (`test_atualizar_conta_recorrente_nao_gera_nem_apaga_ocorrencias`,
integração completa via HTTP: gera 2 ocorrências reais, edita o `valor` do template para
9999.00, confirma que as 2 já geradas continuam com o valor original de 1500.00). Também
testado que o PATCH não gera nem apaga nenhuma ocorrência por si só (nem no caso feliz, nem
tentando trocar `conta_id`↔`cartao_id`).

## Validação cruzada: mesmo padrão, aplicado sem duplicar

`ContaRecorrenteService._validar_estrutura()` é a mesma checagem de
`ParcelamentoService._validar_estrutura()`, aplicada sobre o estado mesclado (existente +
alterações) em `atualizar()` — mesma técnica já usada em `TransacaoService.atualizar()` para
`parcelamento_id`. Testado que enviar só `cartao_id` sem limpar `conta_id` existente é
rejeitado (o par resultante violaria o XOR), e que trocar explicitamente `conta_id=None,
cartao_id=X` é aceito.

## O que foi deliberadamente NÃO alterado

`ContaRecorrenteService.criar()`/`atualizar()` não validam posse/ativo de `conta_id`/`cartao_id`
diretamente — isso é herdado "de graça" da primeira chamada a `TransacaoService.criar()` dentro
da geração de ocorrências. Se `data_inicio` for futura (nenhuma ocorrência gerada ainda na
criação), um `conta_id` inválido só é pego na primeira sincronização — mesmo nível de trade-off
já aceito e documentado para o "conta em uso" de Transferência. Decisão deliberada da análise
arquitetural, não uma omissão: evita duplicar a validação cruzada de posse que já existe em
`TransacaoService`, e o pior caso é um erro `404` limpo mais tarde, nunca uma falha silenciosa
ou dado corrompido.

## Conclusão

A implementação segue a arquitetura aprovada, reaproveita `TransacaoService` e
`app/core/datas.py` sem duplicar nenhuma regra, respeita o escopo de MENSAL-apenas pedido
explicitamente pelo usuário, e corrige um problema real (`data_fim` anterior a `data_inicio`)
encontrado durante a própria revisão, antes de qualquer usuário real esbarrar nele. Nenhum
outro problema de arquitetura, regra de negócio, consistência ou segurança foi encontrado.
