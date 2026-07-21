# Análise arquitetural — Conta Recorrente

Análise de modelagem prévia à implementação do CRUD de `ContaRecorrente`, seguindo o mesmo
rigor de `docs/analise-arquitetural-parcelamento.md` e `docs/analise-arquitetural-transacao.md`.
Apresentada em chat antes de qualquer código, com dois pontos explicitamente levados ao
usuário para decisão (não resolvidos unilateralmente). **Status: aprovada, com escopo restrito
pelo usuário a `FrequenciaRecorrencia.MENSAL`.**

## ContaRecorrente ↔ Transação: quem é a fonte da verdade

`ContaRecorrente` é o TEMPLATE (frequência, valor, dia de vencimento, categoria, conta/cartão);
a fonte da verdade de saldo e relatórios continua sendo exclusivamente a `Transacao` gerada
para cada ocorrência (`origem_recorrente_id`), nunca o template em si. Isso já estava
implícito no docstring original do model ("uma rotina... gera a Transacao correspondente a
cada ocorrência") — diferente de Transferência, aqui não havia conflito algum com decisão
arquitetural prévia: nenhuma mudança em `ContaRepository`/`CartaoRepository` foi necessária,
saldo e relatórios já enxergam as ocorrências automaticamente por serem `Transacao` normais.

## Quando uma nova transação recorrente deve existir

Regra: uma ocorrência deve existir quando `data_da_ocorrência <= hoje` **e** ainda não existe
nenhuma `Transacao` com aquele `origem_recorrente_id` naquela data. Diferente de Parcelamento
(compromisso finito, gerado eager de uma vez), ContaRecorrente é potencialmente sem fim
(`data_fim` opcional) — gerar hoje uma ocorrência futura criaria uma `Transacao` fantasma para
algo que ainda não aconteceu. Geração é sempre **lazy**, disparada por ação explícita do
usuário, nunca por GET (que deve permanecer seguro/sem efeito colateral) nem por scheduler.

## Como evitar geração duplicada

Duas camadas, mesma lição aprendida no bug de `numero_parcela` de Parcelamento: o Service
consulta ocorrências já existentes (`TransacaoRepository.listar_do_usuario(origem_recorrente_id=...,
data_inicio=X, data_fim=X)`) antes de gerar, e uma `UniqueConstraint(origem_recorrente_id, data)`
em `Transacao` funciona como rede de segurança no banco. Aplicada desde o início, sem esperar
descobrir o mesmo bug de novo.

## Geração de ocorrências: sempre lazy, gatilho duplo

- `criar()` gera imediatamente as ocorrências vencidas até hoje (cobre "já pago desde
  janeiro, só cadastrando agora"; se `data_inicio` for futura, nada é gerado ainda).
- `POST /contas-recorrentes/{id}/gerar-ocorrencias-pendentes` cobre a sincronização quando o
  usuário reabre o app depois de um tempo — idempotente (ocorrência já gerada é pulada).

Ambos chamam o mesmo método interno (`_gerar_ocorrencias_pendentes`), sem duplicar a lógica de
"qual é a próxima data e ela já foi gerada?". A próxima data é sempre calculada a partir da
**última ocorrência já gerada** (nunca a partir de `data_inicio`) — editar `dia_vencimento`
depois de já existirem ocorrências só afeta as futuras, nunca reescreve o passado.

## Como preservar histórico quando a recorrência é alterada ou cancelada

Mais simples que Parcelamento, por uma razão estrutural: como nenhuma ocorrência futura é
gerada adiantada (só até "hoje"), não existe nada a desfazer ao desativar — `desativar()` é
soft delete puro (`ativo=False`), sem efeito colateral, mesmo padrão de
Conta/Categoria/Tag/Cartão (não o `POST /cancelar` de Fatura/Parcelamento/Transferência, que
*têm* efeito colateral a desfazer).

Editar o template (`PATCH`) é seguro aqui e não é seguro em Parcelamento/Fatura pela mesma
razão: cada ocorrência gerada é uma `Transacao` independente que grava seu próprio
`valor`/`data`/`categoria_id` no momento da geração e nunca mais volta a ler o template depois
— diferente de Parcelamento, onde as parcelas são pré-computadas a partir de `valor_total` na
criação, fortemente acopladas. `ContaRecorrenteUpdate` existe (diferente de
Fatura/Parcelamento/Transferência, que não têm `Update`) exatamente por essa divergência.

## Como reutilizar TransacaoService

Mesma composição de `ParcelamentoService`: `ContaRecorrenteService` recebe
`ContaRecorrenteRepository`, `TransacaoRepository` (só leitura, achar a última ocorrência) e
`TransacaoService` (escrita). Cada ocorrência nasce via `transacao_service.criar()` — herda de
graça posse/ativo de conta ou cartão, resolução de fatura para recorrência no cartão,
compatibilidade de categoria, e agora também a duplicidade de data (achado desta análise).
`ContaRecorrenteService` nunca fala com `TransacaoRepository` para escrever, e nunca chama
métodos privados de `TransacaoService` — só os públicos, mesmo limite de encapsulamento já
respeitado entre Parcelamento e Transação.

Consequência aceita conscientemente: como a criação do template já dispara a geração da
primeira ocorrência pendente quando `data_inicio <= hoje`, um `conta_id`/`categoria_id`
inválido falha imediatamente (mesma Unit of Work, rollback atômico). Se `data_inicio` for
futura, o erro só aparece na primeira geração de fato — trade-off documentado, mesmo nível já
aceito para o "conta em uso" de Transferência.

## Domínio simples: sem scheduler, sem infraestrutura antecipada

Nenhum scheduler/cron/job/fila/background worker. Nenhuma integração com `Alerta` (que já tem
`TipoAlerta.VENCIMENTO_CONTA_RECORRENTE` no enum, mas sem CRUD próprio ainda — fora de escopo).
Nenhum novo conceito de status além de `PENDENTE`/`PAGO` já existente em `Transacao`.

## Decisão levada ao usuário: escopo de frequência (MENSAL apenas)

`FrequenciaRecorrencia` tem `SEMANAL`/`MENSAL`/`ANUAL`, mas `dia_vencimento` (int 1-31, "dia do
mês") e o utilitário compartilhado `app/core/datas.py` (`dia_valido`/`proximo_mes`) só têm
semântica bem definida para `MENSAL` — `SEMANAL` precisaria de dia da semana, `ANUAL` de mês+dia.
Esse ponto foi levado explicitamente ao usuário antes de decidir sozinho. **Resposta do
usuário: suportar oficialmente só `MENSAL` nesta etapa.** `TipoRecorrencia`/`FrequenciaRecorrencia`
permanece no enum como está (evita refatoração do model), mas o Service rejeita `SEMANAL`/`ANUAL`
com `BusinessRuleError` explícito. Nenhum campo novo foi adicionado para suportar os outros
tipos — API aceita o valor, mas a regra de negócio barra o que ainda não tem lógica de datas
correta por trás. Extensão futura, se necessária, será evolução do domínio, não código
antecipado.

## Mudanças de modelagem necessárias antes da implementação

1. Novo `CheckConstraint` em `ContaRecorrente`: `conta_id` XOR `cartao_id` — mesma lacuna que
   existia em Parcelamento antes de sua própria análise corrigir.
2. Nova `UniqueConstraint(origem_recorrente_id, data)` em `Transacao`.
3. `TransacaoRepository.listar_do_usuario` ganha filtro opcional `origem_recorrente_id`
   (mesmo padrão de `parcelamento_id`).
4. `ContaRecorrenteRepository` novo; `TransacaoService` passa a validar posse e duplicidade de
   data ao vincular manualmente um `origem_recorrente_id` — fecha a lacuna YAGNI deixada em
   aberto em `docs/analise-arquitetural-transacao.md` especificamente para este campo.
   `financiamento_id`/`emprestimo_id`/`meta_id` continuam sem essa validação.
5. Nenhuma extração de utilitário nova — `app/core/datas.py` já resolve tudo que `MENSAL`
   precisa; reaproveitado sem alteração.

## Conclusão

Arquitetura validada. Nenhuma abstração nova além do que já existia para Parcelamento —
mesma composição de Services, mesmo padrão de soft delete, mesma família de CheckConstraints.
A única divergência deliberada (permitir `PATCH`) tem justificativa estrutural própria, não é
uma inconsistência. Escopo restrito a `MENSAL` por decisão explícita do usuário, evitando
código para `SEMANAL`/`ANUAL` sem utilidade prática imediata. Pronta para servir de base à
implementação do CRUD de `ContaRecorrente`.
