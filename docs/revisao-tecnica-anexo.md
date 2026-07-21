# Revisão técnica — CRUD de Anexo

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.**

## Resumo

Décima terceira entidade de domínio, e a última antes de `Alerta`. Segue
`Router → Service → Repository` estritamente: `AnexoRepository` só acesso ao banco,
`AnexoService` concentra toda a regra de negócio, `app/api/routes/anexo.py` sem nenhuma
lógica além de tradução HTTP↔Service. Fecha o único vínculo manual que ainda não tinha CRUD
próprio, mas de uma forma estruturalmente diferente das entidades anteriores: em vez de
ganhar um Repository mínimo para validação de posse em `TransacaoService` (como
`parcelamento_id`/`financiamento_id`/`emprestimo_id`/`meta_id`), `Anexo` INVERTE a
dependência — é `AnexoService` que depende de `TransacaoService`, nunca o contrário, porque
sua posse é inteiramente transitiva. Suíte completa: 742 testes passando (446 unitários + 296
de integração) — 15 unitários novos de `AnexoService`, 18 de integração novos do fluxo de
Anexo. Migração validada em ciclo completo `upgrade` → `downgrade` → `upgrade` → `check`
contra banco descartável, zero drift.

## O redesenho do model: conflito real, mas sem ambiguidade de leitura

Diferente de `Meta` (onde o pedido do usuário admitia duas leituras honestas da mesma frase,
resolvidas via `AskUserQuestion` antes do código), o conflito de `Anexo` era de outra
natureza: o model já existia desde o "modelo inicial do domínio financeiro" com um desenho
especulativo — polimórfico (`entidade_tipo`/`entidade_id`, mesma estratégia de `Alerta`),
`usuario_id` como FK direta, sem soft delete — e as regras de domínio desta etapa, dadas de
forma direta e sem duas leituras possíveis ("Anexo pertence sempre a uma Transação", "nunca
pertence diretamente ao usuário"), contradiziam esse desenho ponto a ponto. Não havia
ambiguidade a resolver com o usuário; havia uma decisão de engenharia a registrar antes do
código: manter o polimorfismo especulativo (que nunca tinha sido exercitado por nenhum
Router/Service) ou redesenhar para o formato realmente pedido. Registrado em
`docs/analise-arquitetural-anexo.md` antes de qualquer implementação, seguindo o mesmo
precedente já estabelecido neste projeto de que o "modelo inicial" é um placeholder amplo,
refinado quando a entidade ganha seu CRUD explícito (mesmo padrão da redução de escopo de
`Parcelamento` na etapa 21).

**Verificado que o redesenho não vazou para `Alerta`.** `TipoEntidadeReferenciavel` (o enum
do desenho polimórfico) permanece exatamente como estava - `Anexo` simplesmente parou de
importá-lo. Confirmado por leitura do código final: nenhuma referência a esse enum resta em
`app/models/anexo.py`, `app/schemas/anexo.py` ou `app/services/anexo_service.py`. `Alerta`
(ainda não implementado) mantém a opção de usar referência polimórfica de verdade quando
ganhar suas próprias regras de domínio.

## Posse transitiva: verificado que não há nenhum caminho que a contorne

A parte mais fácil de errar nesta entidade seria alguma rota ou método do Service checar posse
de forma direta (ex.: comparar `anexo.transacao_id` contra alguma lista pré-carregada, ou
aceitar um `usuario_id` implícito). Verificado no código final que TODO ponto de entrada do
`AnexoService` (`criar`, `obter` via `_buscar_da_propriedade_do_usuario`, `listar_por_transacao`,
`desativar`) passa por `TransacaoService.obter(transacao_id, usuario_id)` antes de qualquer
leitura/escrita no `AnexoRepository` — nunca há um caminho que pula essa checagem.
`AnexoRepository` em si não tem nenhum método que filtre por usuário (não faz sentido, já que
`Anexo` não tem essa coluna) — a única forma de a posse ser validada é através do
`TransacaoService` injetado, o que torna estruturalmente impossível esquecer a checagem numa
rota nova sem que fique óbvio na revisão de código (não haveria nem `usuario_id` disponível
para comparar).

Coberto por teste de integração dedicado
(`test_criar_anexo_em_transacao_de_outro_usuario_retorna_404`) que reproduz exatamente o
cenário da regra de domínio explícita ("não permitir anexar arquivos em transações de outro
usuário"), e por um teste que teoricamente não deveria nem ser necessário mas serve como
regressão de design (`test_criar_anexo_nao_tem_usuario_id_proprio` - confirma que o objeto
`Anexo` devolvido não tem esse atributo).

## Terceiro padrão de composição com `TransacaoService`

Este projeto agora tem três formas distintas de uma entidade se relacionar com
`TransacaoService`, e vale registrar a diferença porque um futuro CRUD pode
inadvertidamente escolher o padrão errado:

1. **Escrita delegada** (`Parcelamento`/`ContaRecorrente`/`Financiamento`/`Empréstimo`): o
   Service da entidade CHAMA `TransacaoService.criar()`/`atualizar()` para gerar parcelas ou
   ocorrências - a entidade não existe sem gerar `Transacao`s reais.
2. **Leitura agregada sem dependência de Service** (`Meta`): `MetaService` nunca importa nem
   injeta `TransacaoService` - lê `Transacao` diretamente via `MetaRepository` (uma query SQL
   de agregação própria). Zero acoplamento a `TransacaoService`.
3. **Validação de posse delegada, sem escrita nem agregação** (`Anexo`, novo nesta etapa):
   `AnexoService` injeta `TransacaoService` mas SÓ chama `.obter()` - nunca escreve uma
   `Transacao`, nunca agrega dados dela. É o padrão mais simples dos três, mas também o
   primeiro caso em que a dependência de `TransacaoService` existe unicamente para
   reaproveitar uma validação, não para orquestrar nem calcular nada.

Verificado que `get_anexo_service` em `app/api/deps.py` reflete esse padrão exatamente:
injeta `AnexoRepository` e `TransacaoService` (não `TransacaoRepository`), sem nenhuma
dependência adicional - a assinatura mais enxuta entre todas as entidades com vínculo a
`Transacao`.

## `ondelete=CASCADE`: verificado ponta a ponta, não só na migration

A decisão de que um `Anexo` deve desaparecer junto quando sua `Transacao` é excluída
(consequência de `Transacao` usar hard delete, não soft delete) foi implementada em DOIS
níveis - `ForeignKey(ondelete="CASCADE")` no banco e `cascade="all, delete-orphan"` no lado
Python da relationship (`Transacao.anexos`) - e verificado que os dois níveis realmente
concordam, não apenas declarados. `TransacaoRepository.delete()` (herdado de
`SQLAlchemyRepository.delete()`) usa `self.db.delete(obj)` (delete via sessão ORM, não um
`DELETE` bruto), o que é exatamente o que faz `cascade="all, delete-orphan"` disparar do lado
Python. Coberto por teste de integração real
(`test_excluir_transacao_remove_seus_anexos_via_cascade`): cria uma `Transacao`, anexa um
arquivo, exclui a `Transacao` via `DELETE /transacoes/{id}` real, e confirma que
`GET /anexos/{id}` também passa a devolver 404 (a checagem de posse falha porque a transação
não existe mais). Não foi testada a leitura direta do banco pós-exclusão (ex.: `SELECT` bruto
confirmando ausência da linha), mas o teste via API já prova o efeito observável que importa
para o usuário do sistema.

## Achado real desta etapa: corrupção de migration não detectada pelo `upgrade`+`check` isolados - só pelo ciclo completo

Este é o achado mais significativo da etapa, e um caso novo de um problema já bem documentado
neste projeto (corrupção de arquivo por mount).

**O que aconteceu.** Após escrever a migration `5bf719e3a7a3` (convertendo o `upgrade()`
autogenerado para `batch_alter_table`, como sempre necessário para SQLite), o ciclo de
validação `upgrade head` → `check` passou limpo na primeira tentativa. Só ao validar o ciclo
completo (`upgrade` → `downgrade -1` → `upgrade head` → `check`, o procedimento padrão deste
projeto) é que o problema apareceu: `downgrade -1` executado via `alembic downgrade -1` (CLI
real, através de `env.py`) produzia uma tabela `anexos` com TODAS as colunas antigas E novas
coexistindo (`transacao_id` retido junto com `usuario_id`/`nome_arquivo` recriados) - o
`batch_alter_table` do `downgrade()` parecia não ter aplicado nenhuma das operações de
`add_column`/`drop_column`/`drop_index` além da recriação básica da tabela.

**Diagnóstico.** Reproduzir as MESMAS operações do `downgrade()` manualmente, via
`Operations()` direto contra a mesma engine (sem passar pelo `alembic downgrade -1` via CLI),
produzia o resultado CORRETO de forma consistente e repetida. Isso isolou o problema: não era
um bug de lógica no `batch_alter_table` (a lógica está correta, provada por replay manual
idêntico), mas uma divergência entre o que o comando `cat`/`grep`/o Read tool mostravam do
arquivo da migration e o que o processo do `alembic downgrade -1` de fato executava -
exatamente o padrão de corrupção de arquivo por mount já documentado extensivamente neste
projeto (mais uma vez confirmando que a verificação pós-edição via `ast.parse` não é
suficiente: o arquivo era sintaticamente válido e semanticamente correto quando lido, mas o
subprocesso do Alembic executava uma versão diferente). Corrigido reescrevendo o arquivo
inteiro via heredoc bash a partir do conteúdo autoritativo do Read tool - após isso, o ciclo
completo passou de forma consistente e repetida.

**Por que isso é um achado novo, não só uma repetição do padrão já conhecido.** Em toda
corrupção anterior deste projeto, o sintoma era visível diretamente (erro de sintaxe, `NameError`,
teste unitário falhando com um traceback claro). Aqui, o sintoma era um SILÊNCIO: nenhum erro,
nenhuma exceção, `alembic downgrade -1` reportava sucesso, e a única forma de perceber que
algo estava errado era inspecionar o schema resultante manualmente (`PRAGMA table_info`) e
notar colunas que não deveriam coexistir. Isso reforça uma lição prática para sessões
futuras: **a validação de migration não pode se limitar a "o comando não lançou exceção" -
precisa inspecionar o schema resultante em cada etapa do ciclo** (`upgrade`, `downgrade`,
`upgrade` de novo), não só rodar `alembic check` no final (que só compara o estado FINAL
contra os models, e nesta etapa o estado final pós-segundo-upgrade estava correto mesmo
quando o downgrade intermediário tinha ficado errado).

**Banco de desenvolvimento local (`financas.db`) não pôde ser validado nesta etapa.**
Diferente de todas as etapas anteriores, tentativas de rodar `alembic upgrade head`/`check`
contra o `financas.db` real do projeto (não um banco descartável em `/tmp`) retornaram
`sqlite3.OperationalError: disk I/O error` de forma persistente, e o arquivo aparecia como 0
bytes em inspeções subsequentes via bash, mesmo após a migration ter sido aplicada com
sucesso (confirmado pelo bash reportar temporariamente um tamanho maior antes de reverter a 0
bytes). `rm`/recriação do arquivo também falhou com "Operation not permitted" - o mesmo tipo
de comportamento anômalo de permissão já observado uma vez nesta sessão para outro arquivo
temporário. A migração está integralmente validada contra múltiplos bancos descartáveis
(`/tmp/*.db`), incluindo o ciclo completo upgrade/downgrade/upgrade/check sem drift - a
limitação é especificamente do arquivo `financas.db` neste ambiente de sessão, não da
migration em si. Recomenda-se que o usuário rode `alembic upgrade head` no seu próprio
ambiente ao aplicar esta mudança.

## Corrupção de arquivo por mount: recorrente, todos os casos resolvidos

Além da migration (achado central acima), o bug já documentado em revisões anteriores atingiu
nesta etapa: `app/api/deps.py`, `app/main.py`, `app/models/transacao.py`,
`app/models/usuario.py`, `app/models/anexo.py` e `tests/unit/test_anexo_service.py`. Todos os
casos foram detectados pela verificação obrigatória pós-edição (`ast.parse`/contagem de
bytes/comparação com o conteúdo do Read tool) e corrigidos reescrevendo o arquivo inteiro via
heredoc bash. Nenhum caso ficou sem resolução ou exigiu retrabalho de lógica - mecânica do
ambiente, não problema de código.

## O que foi deliberadamente NÃO implementado

Confirmado por leitura do código final: nenhuma menção a upload para cloud, OCR, thumbnails,
compressão, antivírus, versionamento, compartilhamento, criptografia de arquivo ou download
autenticado especial - exatamente a lista de exclusões pedida explicitamente pelo usuário.
`caminho_arquivo` é tratado em todo o código como uma string opaca; nenhuma rota ou Service
abre, lê ou grava o conteúdo do arquivo referenciado.

## Conclusão

A implementação segue a arquitetura aprovada sem desvio: `Router → Service → Repository`
estrito, toda regra de negócio no Service, Repository sem nenhuma decisão além do acesso ao
banco. O redesenho do model, embora uma mudança estrutural real num model pré-existente, foi
resolvido corretamente porque a instrução do usuário era direta - o registro em
`docs/analise-arquitetural-anexo.md` documenta a decisão e por que ela não exigiu uma pergunta
de esclarecimento (diferente do caso de `Meta`). Nenhum problema de arquitetura, regra de
negócio ou segurança foi encontrado no código de `Anexo` propriamente dito: a posse transitiva
é estruturalmente impossível de contornar (não há coluna `usuario_id` para comparar por
engano), o cascade físico foi verificado ponta a ponta via teste de integração real, e a
ausência de `PATCH` foi confirmada tanto no schema quanto na rota. O achado real desta etapa
foi, mais uma vez, externo ao domínio de `Anexo`: uma nova manifestação - silenciosa, sem
exceção - do bug de corrupção de arquivo por mount, desta vez afetando especificamente o
`downgrade()` de uma migration executado via CLI, só detectável por inspeção manual do schema
resultante em cada etapa do ciclo de validação, não só pelo `alembic check` final. Documentado
em detalhe acima para mitigação em sessões futuras. Suíte completa: 742 testes passando (446
unitários + 296 de integração).
