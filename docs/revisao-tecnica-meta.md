# Revisão técnica — CRUD de Meta

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.**

## Resumo

Décima segunda entidade de domínio. Segue `Router → Service → Repository` estritamente:
`MetaRepository` só acesso ao banco, `MetaService` concentra toda a regra de negócio,
`app/api/routes/meta.py` sem nenhuma lógica além de tradução HTTP↔Service. Fecha a última
lacuna YAGNI documentada em `TransacaoService` (`meta_id` era o único vínculo manual restante
sem validação de posse). Suíte completa: 709 testes passando (431 unitários + 278 de
integração) — 28 unitários novos de `MetaService`, mais os acréscimos em
`TransacaoService`/`TransacaoRepository` (posse de `meta_id`, bloqueio de meta inativa,
ortogonalidade com `financiamento_id`, filtro em `listar()`), e 27 de integração novos do
fluxo de Meta. Migração validada em ciclo completo `upgrade` → `downgrade` → `upgrade` →
`check` contra banco descartável, zero drift.

## O conflito de modelagem foi resolvido ANTES do código — não depois

Diferente da maioria das entidades anteriores, onde os problemas mais sérios foram
encontrados na revisão técnica *após* a implementação, aqui o único ponto genuinamente
ambíguo do pedido do usuário foi identificado e resolvido antes de qualquer linha de código
ser escrita. O texto do usuário admitia duas leituras honestas para a fonte de
`valor_acumulado`: somar pelo saldo da `Conta` vinculada (quando houver), ou somar sempre
pelas `Transacao` com `meta_id` apontando para a meta, independente de `conta_id` estar
preenchido. As duas leituras produzem resultados diferentes sempre que a conta vinculada tem
outras movimentações não relacionadas à meta — a primeira leitura contaminaria o progresso
com dinheiro que não tem nada a ver com o objetivo.

Registrado em `docs/analise-arquitetural-meta.md` com as duas opções explicitadas, e
resolvido via `AskUserQuestion` direta ao usuário, que confirmou a opção recomendada: regra
única via `meta_id`, `conta_id` puramente organizacional. Isso evitou o padrão observado em
etapas anteriores deste projeto, onde uma ambiguidade não detectada a tempo virava um bug
"correto sintaticamente, errado semanticamente" só pego na revisão final. Vale registrar como
processo que funcionou: o valor de resolver decisões de modelagem ambíguas antes da
implementação, não depois.

## `valor_acumulado`/`percentual`: verificado que a independência de `conta_id` é real, não só documentada

A decisão de que `conta_id` não participa do cálculo é fácil de declarar e fácil de violar
silenciosamente (bastaria `MetaRepository.somar_transacoes_pagas` filtrar por
`Transacao.conta_id == meta.conta_id` em vez de `Transacao.meta_id == meta.id`, e o bug
passaria despercebido em qualquer teste que não force os dois valores a divergir). Verificado
na leitura final do código que a query em `MetaRepository.somar_transacoes_pagas` filtra
exclusivamente por `Transacao.meta_id == meta_id` — `conta_id` nunca aparece na cláusula
`WHERE`. Coberto por dois testes de regressão dedicados, não apenas um: o unitário
`test_valor_acumulado_independe_de_conta_vinculada` (usa um fake repository, então prova
só que o Service não filtra por conta) e o de integração
`test_valor_acumulado_independe_de_conta_vinculada_a_meta` (posta uma transação real via
`POST /transacoes` numa `Conta` DIFERENTE da vinculada à `Meta` e confirma que o aporte ainda
é contabilizado) — o segundo é o que realmente prova a query SQL real, não uma simulação.

## `_com_progresso`: sem risco de divisão por zero, verificado nos dois schemas

`MetaService._com_progresso()` calcula `valor_acumulado / meta.valor_alvo * 100` sem nenhuma
guarda contra `valor_alvo == 0`. Isso seria um bug real se `valor_alvo` pudesse chegar a zero
por qualquer caminho da API. Verificado que não pode: `MetaCreate.valor_alvo` tem
`Field(gt=0)` e `MetaUpdate.valor_alvo` também tem `Field(gt=0)` (não apenas `ge=0`) —
qualquer tentativa de `POST`/`PATCH` com `valor_alvo=0` é rejeitada pelo Pydantic com 422
antes de chegar ao Service. Não há caminho de escrita direta ao banco que contorne o schema
neste projeto. Sem ação necessária, mas vale o registro de que a ausência de guarda no
Service é segura porque depende de uma garantia de camada externa — se um dia `MetaService`
for chamado por outro caminho de entrada (ex.: um script de seed) sem passar pelo schema,
essa suposição precisa ser revisitada.

## `meta_id` em `TransacaoService`: fecha a lacuna, sem reintroduzir a complexidade de faixa/duplicidade

`_validar_meta_ativa()` verifica posse (existe + pertence ao usuário) e bloqueia meta
inativa — mesmo padrão de `_validar_conta_ativa`/`_validar_cartao_ativo`. Deliberadamente SEM
a lógica de faixa (`numero_parcela` dentro do total de parcelas) nem duplicidade
(`UniqueConstraint`) que `_validar_financiamento`/`_validar_emprestimo`/
`_validar_parcelamento` têm — correto, porque `Meta` não tem conceito de parcela: múltiplos
aportes à mesma meta ao longo do tempo são o comportamento normal e esperado, não um erro.
Verificado que `meta_id` é ortogonal à estrutura "no máximo um contrato" já existente (o
`CHECK constraint` que impede uma `Transacao` de ter mais de um entre
`parcelamento_id`/`financiamento_id`/`emprestimo_id`/`numero_parcela` simultaneamente) — uma
transação pode ter `meta_id` E `financiamento_id` ao mesmo tempo sem violar nenhuma
constraint, e isso é intencional (ex.: uma parcela de financiamento que também conta como
aporte para uma meta de "quitar a casa"). Coberto por teste unitário dedicado de
orthogonalidade (`meta_id` + `financiamento_id` na mesma transação, aceito sem erro).

Com isso, `parcelamento_id`, `origem_recorrente_id`, `financiamento_id`, `emprestimo_id` e
`meta_id` têm todos validação de posse em `TransacaoService` — não resta mais nenhum vínculo
manual em `Transacao` aceito sem checagem, fechando um débito rastreado desde
`docs/analise-arquitetural-transacao.md`.

## `MetaService` não compõe `TransacaoService` — verificado que isso é correto, não uma omissão

Diferente de `Parcelamento`/`ContaRecorrente`/`Financiamento`/`Empréstimo`, que todos
escrevem `Transacao` através de `TransacaoService` (gerando parcelas, ocorrências,
cronogramas ou desembolsos), `MetaService` nunca cria, edita ou paga uma `Transacao` — o
aporte à meta é um lançamento comum feito pelo fluxo normal de `POST /transacoes`, apenas com
`meta_id` preenchido. `MetaService` só LÊ, via `MetaRepository.somar_transacoes_pagas`, para
calcular o progresso. Verificado no código final que não existe nenhum import de
`TransacaoService`/`TransacaoRepository` em `meta_service.py` — a composição é
unidirecional (`TransacaoService` conhece `MetaRepository` para validar posse, `MetaService`
não conhece `TransacaoService` para nada). Isso é o comportamento correto pedido pelo
domínio, não uma lacuna: o usuário decide lançar um aporte como qualquer outra transação, e a
meta só observa o resultado.

## Nome único com reativação: mesmo padrão de Tag/Cartão, sem desvio

`MetaService.criar()`/`atualizar()` reaproveitam exatamente a mesma tensão já resolvida em
`TagService`/`CartaoService`: `UniqueConstraint(usuario_id, descricao)` não distingue ativo de
inativo, então criar uma meta com descrição igual a uma meta desativada REATIVA a linha
existente (sobrescrevendo todos os campos do payload novo) em vez de tentar inserir uma
duplicata e estourar a constraint. Renomear (não criar) para uma descrição já usada por uma
meta inativa, ao contrário, NÃO reativa/mescla automaticamente — levanta `ConflictError`,
mesma decisão deliberada de `TagService`/`CartaoService.atualizar()`. Ambos os caminhos têm
teste unitário e de integração dedicados; nenhum comportamento divergente encontrado.

## Migração: sem drift, sem incidentes

`alembic upgrade head` → `downgrade -1` → `upgrade head` → `alembic check` validado limpo
contra dois bancos SQLite descartáveis distintos (verificação intermediária e verificação
final pós-suíte-completa). A migração (`e91ffcf3761c`) adiciona
`UniqueConstraint(usuario_id, descricao)` em `Meta` via `batch_alter_table` — mesma
estratégia manual já necessária em toda migração anterior deste projeto que adiciona
constraint a uma tabela SQLite (autogenerate nunca usa batch mode por padrão, falha com
`NotImplementedError` se não for corrigido manualmente). `alembic check` confirma "No new
upgrade operations detected" contra o head atual.

## Corrupção de arquivo por mount: mais frequente e mais severa nesta etapa — dois achados novos

O bug de corrupção de arquivo já documentado em revisões anteriores (edições que passam no
`Edit`/`Write` mas cujo conteúdo visível via bash diverge do que o Read tool mostra) ocorreu
com frequência maior que em qualquer etapa anterior, atingindo `app/models/meta.py`,
`app/main.py`, a migration `e91ffcf3761c`, `app/api/deps.py`,
`tests/unit/test_transacao_service.py` (duas vezes), `app/services/transacao_service.py` e
`app/api/routes/transacao.py`. Todos os casos foram detectados pela verificação obrigatória
pós-edição e corrigidos reescrevendo o arquivo inteiro via heredoc a partir do conteúdo
autoritativo do Read tool. Nenhum caso ficou sem resolução.

Dois padrões novos, não observados em etapas anteriores, valem registro para sessões futuras:

**Corrupção tardia (lazy).** `app/services/transacao_service.py` foi editado com sucesso em
7 edições separadas, cada uma verificada individualmente via `ast.parse` logo em seguida —
todas passaram. Só depois, após rodar `pytest` várias vezes para outros fins, uma nova
checagem revelou que o arquivo havia truncado silenciosamente `_validar_tags()` no meio,
removendo o `return tags` final. Como Python permite uma função cair no `return None`
implícito, isso não quebrou `ast.parse` (a truncagem caiu numa fronteira sintaticamente
válida) — só apareceu como `TypeError` ao rodar os testes, 74 de 104 falhando. Diagnosticado
via `inspect.getsource()` mostrando o método truncado, confirmado via Read tool mostrando o
conteúdo verdadeiro completo. **Implicação prática:** a verificação pós-edição imediata não é
suficiente sozinha — uma reverificação final, próxima do fim da sessão e depois de outras
operações de bash terem rodado, é necessária antes de declarar qualquer arquivo como
definitivamente correto.

**Limite de truncagem em torno de 40KB por escrita única.** Tentar reescrever o arquivo
completo de `tests/unit/test_transacao_service.py` (~44KB) num único `cat > arquivo << EOF`
truncou silenciosamente em exatamente 40.662 bytes, duas vezes seguidas. Resolvido dividindo
a escrita em duas chamadas bash sequenciais (`cat >` para a primeira metade, `cat >>` para
completar) — cada uma comfortavelmente abaixo do limite observado. Recomendação para sessões
futuras: qualquer reescrita de arquivo grande (~35KB+) neste ambiente deve ser dividida em
múltiplos heredocs por precaução, em vez de assumir que uma escrita única é confiável.

Em nenhum dos dois casos o problema é de lógica de código — é puramente uma limitação
mecânica do ambiente desta sessão, mitigada com sucesso pelo procedimento de verificação já
estabelecido, agora refinado com esses dois achados.

## O que foi deliberadamente NÃO implementado

Confirmado por leitura do código final: nenhuma menção a notificações, automações, integração
com `Alerta`, scheduler, IA ou histórico de progresso ao longo do tempo — exatamente a lista
de exclusões pedida explicitamente pelo usuário. `Meta` não tem nenhuma tabela ou coluna de
snapshot histórico; o progresso é sempre uma foto do estado atual das transações, recalculada
a cada leitura.

## Conclusão

A implementação segue a arquitetura aprovada sem desvio: `Router → Service → Repository`
estrito, regra de negócio inteiramente no Service, Repository sem nenhuma decisão de negócio
além da agregação SQL pura. O único ponto genuinamente ambíguo do domínio foi identificado e
resolvido com o usuário antes do código, não depois — o processo funcionou como pretendido.
Nenhum problema de arquitetura, regra de negócio ou segurança foi encontrado no código de
`Meta` propriamente dito: a independência de `conta_id` no cálculo foi verificada na query
real (não só na intenção declarada), a ausência de guarda contra divisão por zero é segura
porque depende de uma constraint de schema verificada, e o fechamento da última lacuna YAGNI
de `meta_id` em `TransacaoService` não reintroduziu complexidade desnecessária (sem faixa,
sem duplicidade — corretamente, já que `Meta` não tem conceito de parcela). O achado real
desta etapa foi, de novo, externo ao domínio: dois padrões novos de corrupção de arquivo por
mount (truncagem tardia e limite de ~40KB por escrita), documentados em detalhe acima para
mitigação em sessões futuras. A migração está validada em ciclo completo sem drift. Suíte
completa: 709 testes passando (431 unitários + 278 de integração).
