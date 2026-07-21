# Revisão técnica — Central Financeira

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.**

## Resumo

Última camada funcional do backend antes do frontend, e a primeira deste projeto que não é
uma entidade de domínio: `CentralFinanceiraService` é uma camada de orquestração e
agregação 100% somente-leitura sobre os 8 Services já existentes (`ContaService`,
`CartaoService`, `FaturaService`, `TransacaoService`, `FinanciamentoService`,
`EmprestimoService`, `ParcelamentoService`, `MetaService`), sem Repository próprio, sem SQL
direto e sem nenhuma regra de negócio nova — exatamente o contrato pedido antes de escrever
qualquer código (`docs/analise-arquitetural-central-financeira.md`). 11 endpoints
agregadores sob `/central-financeira/*`, todos `GET`. Duas extensões mecânicas em
`TransacaoService`/`TransacaoRepository` (filtro `status`, `somar_por_periodo` como `SUM`
no banco) foram as únicas mudanças fora da Central em si. Zero migration nova (`alembic
check` confirma). Suíte completa: 788 testes passando (471 unitários + 317 de integração) —
25 unitários novos de `CentralFinanceiraService` (fakes dos 8 Services injetados), 21 de
integração novos do fluxo da Central (18 do fluxo funcional + 3 do achado de validação de
query descrito abaixo).

## As três regras estruturais foram verificadas no código final, não só no design

O docstring de `central_financeira_service.py` declara três invariantes (nunca Repository,
nunca duplicar cálculo, soma/contagem só sobre listas já pequenas e limitadas). Verificado
por leitura linha a linha do arquivo final que as três se sustentam:

1. **Nenhum import de Repository.** `central_financeira_service.py` só importa os 8
   Services de domínio, `app.models` (para type hints de `Cartao`/`Fatura`) e
   `app.models.enums`. Nenhum `from app.repositories import ...` em lugar nenhum do arquivo.
2. **Nenhum valor recalculado.** `saldo_atual`, `limite_disponivel`,
   `valor_total_calculado`/`status_calculado`, `valor_acumulado`/`percentual`,
   `saldo_devedor` são sempre lidos de um atributo do objeto devolvido por outro Service
   (`c.saldo_atual`, `fatura.valor_total_calculado`, `contrato.saldo_devedor`) — nenhuma
   fórmula desses cálculos aparece reescrita aqui.
3. **Toda soma em Python é sobre N pequeno e limitado por natureza** (parcelas de UM
   contrato via `_metricas_de_parcelas`, cartões de UM usuário via `_total_faturas_em_aberto`,
   metas de UM usuário via `percentual_medio`) — a única agregação sobre a tabela inteira de
   `Transacao` (`entradas_mes`/`saidas_mes`) é delegada a
   `TransacaoService.somar_por_periodo`, que roda como `SUM` no banco, exatamente a diretriz
   de `docs/decisao-performance-saldo.md` que a análise arquitetural desta etapa invocou
   antes de implementar.

## Achado real desta etapa: `mes`/`ano` fora de faixa devolvia 500, não 422

Este é o achado central da revisão, encontrado por inspeção deliberada dos parâmetros de
query não validados (`ano: int | None`, `mes: int | None` em `/resumo` e `/visao-mensal`,
`dias: int` em `/agenda`) — o mesmo tipo de exercício que encontrou o bug silencioso de
migration na revisão de `Anexo`.

**O que acontecia.** `CentralFinanceiraService.resumo_financeiro`/`visao_mensal` passam
`ano`/`mes` direto para `_limites_do_mes`, que chama `calendar.monthrange(ano, mes)`. Para
`mes` fora de `1..12`, isso levanta `calendar.IllegalMonthError` (subclasse de
`ValueError`); para `ano` fora do intervalo suportado por `datetime.date`, `date(ano, mes,
dia)` levanta `ValueError: year out of range`. Nenhum dos dois é uma exceção de domínio
(`BusinessRuleError`/`NotFoundError`/etc.) — não existe handler registrado para `ValueError`
em `app/main.py` — então FastAPI deixava a exceção subir crua, virando um 500 Internal
Server Error genérico em vez de um 422 informativo. `GET
/central-financeira/resumo?mes=13` ou `?ano=99999` reproduziam isso de forma determinística
antes da correção.

**Por que isso é uma falha real, não só um detalhe cosmético.** Todo o resto do projeto trata
entrada inválida de cliente como 422 (`BusinessRuleError`) ou erro de schema Pydantic — nunca
um 500 cru. Um 500 vaza potencialmente detalhes de implementação (traceback, dependendo da
configuração de debug) e quebra o contrato implícito da API ("toda entrada malformada
devolve 4xx"). A Central, sendo a única camada que aceita parâmetros de query numéricos
livres (`ano`, `mes`, `dias` — nenhuma outra entidade do projeto tem um endpoint `GET` com
parâmetro numérico sem `Query(...)` já validado), era a primeira superfície nova onde esse
gap podia se manifestar.

**Correção.** Validação de formato — não de regra de negócio — pertence ao Router, não ao
Service (`CentralFinanceiraService` não pode levantar `BusinessRuleError`, ver docstring do
arquivo: "são sempre leituras, nunca haveria uma regra de negócio para violar"). Adicionado
`Query(ge=1900, le=2200)` para `ano`, `Query(ge=1, le=12)` para `mes` (ambos via os aliases
`AnoQuery`/`MesQuery` em `app/api/routes/central_financeira.py`) e `Query(ge=0, le=3650)`
para `dias` em `/agenda` (que antes aceitava qualquer inteiro, incluindo negativos — não
quebrava, mas devolvia silenciosamente uma lista vazia em vez de sinalizar entrada inválida,
já que uma janela de dias negativa produz `data_fim < data_inicio`). FastAPI valida esses
bounds antes do corpo da função rodar, devolvendo 422 com o corpo padrão de erro de
validação Pydantic — nenhuma mudança em `CentralFinanceiraService`, a regra estrutural de
"a Central nunca levanta exceção de domínio" continua intacta. Três testes de integração
novos cobrem os três parâmetros (`test_resumo_financeiro_com_mes_fora_de_faixa_devolve_422`,
`test_visao_mensal_com_ano_fora_de_faixa_devolve_422`,
`test_agenda_financeira_com_dias_negativo_devolve_422`).

**Escopo da correção.** Isso é validação de formato de entrada HTTP (Router), não uma regra
de negócio nova (vedada nesta etapa pelo pedido original) — o mesmo tipo de constraint já
usado em `UsuarioCreate.senha` (`max_length=72`) e em toda paginação (`skip`/`limit`) do
projeto. Nenhum Service, Repository ou Model foi tocado.

## Observações registradas, sem mudança de código

**`_metricas_de_parcelas` usa `limit=num_parcelas` exato; `FinanciamentoService._buscar_parcela`
usa `num_parcelas + 1`.** Pequena assimetria entre os dois pontos que consultam parcelas de
um contrato por `financiamento_id`. Verificado que não é um bug: a transação de entrada
nunca carrega `financiamento_id` (comentário explícito em
`FinanciamentoService.criar()`: "se carregasse `financiamento_id` corromperia a contagem de
parcelas"), e `numero_parcela` é único por contrato — então o número de linhas com um dado
`financiamento_id` é sempre exatamente `num_parcelas`, nunca mais. O `+ 1` em
`_buscar_parcela` é uma margem defensiva sem necessidade demonstrada; `limit=num_parcelas`
na Central é o valor correto. Não fica um item de ação — registrado aqui só para quem for
mexer numa das duas funções não assumir que a diferença é intencional.

**Limite implícito de 100 itens herdado de `listar()` em várias chamadas.** `saldo_consolidado`,
`indicadores_gerais`, `resumo_financiamentos`/`emprestimos` etc. chamam
`conta_service.listar(usuario_id, apenas_ativas=True)` (e equivalentes) sem especificar
`limit`, herdando o default `limit=100` de cada Service de domínio. Para um usuário com mais
de 100 contas/cartões/financiamentos ativos simultaneamente, a Central sub-representaria o
total silenciosamente (sem erro, sem indicação de truncamento) — mas esse limite já existe
em todo `GET /contas`, `/cartoes` etc. hoje, não é algo introduzido por esta camada, e o
projeto é declaradamente de uso pessoal/uma única pessoa (ver `## 📊 Status` do README) —
100 contas ativas simultâneas não é um cenário real para o usuário-alvo. Registrado como
limitação conhecida e herdada, não como falha desta etapa; se o projeto algum dia justificar
suporte a esse volume, a mudança pertence aos Services de domínio (que já decidem o
`limit`), não à Central.

**`_fatura_aberta_do_cartao` depende de `Fatura.mes_referencia.desc()` ser a ordenação
padrão do Repository.** Confirmado em `fatura_repository.py:32`
(`.order_by(Fatura.mes_referencia.desc())`) que essa é de fato a ordenação usada por
`FaturaService.listar()` sem parâmetro de ordenação explícito — `limit=1` correto e
documentado no comentário do método. Se a ordenação padrão do Repository mudasse por outro
motivo no futuro, esse método quebraria silenciosamente (voltaria a fatura errada em vez de
lançar erro); não há teste que trave especificamente essa premissa de ordenação (os testes
de integração cobrem o resultado observável — fatura correta devolvida — mas não a
ordenação do Repository isoladamente). Risco baixo (mudar a ordenação padrão de um
Repository usado por múltiplos Services teria efeitos muito mais amplos que só quebrar a
Central), não gerou ação.

**`indicadores_gerais.faturas_em_aberto` é N+1 por natureza** (uma chamada a
`_fatura_aberta_do_cartao` por cartão do usuário). Aceitável e consistente com a regra
explícita da etapa ("nada de cache, nada de materialized view") — N é o número de cartões de
uma pessoa, não um valor que cresce com a base de usuários. Documentado, não corrigido.

## Corrupção de arquivo por mount: recorrente, todos os casos resolvidos

O bug já documentado extensivamente em revisões anteriores (divergência entre o conteúdo
autoritativo do Read/Edit tool e o que o mount Linux/bash serve) atingiu novamente
`app/api/routes/central_financeira.py` e `tests/integration/test_central_financeira_flow.py`
durante a correção de validação de `mes`/`ano`/`dias` desta revisão — em ambos os casos o
arquivo truncava de forma silenciosa em pontos diferentes a cada tentativa (uma vez cortando
uma instrução no meio de `.json()`, outra vez perdendo os últimos parâmetros de uma função).
Detectado pela verificação obrigatória pós-edição (`py_compile.compile`, contagem de linhas
via `pytest --collect-only` comparada à contagem esperada de `grep -c "^def test_"`) e
corrigido reescrevendo o arquivo inteiro via heredoc bash a partir do conteúdo autoritativo
do Read tool, em ambos os casos. Um detalhe novo desta etapa: a primeira tentativa de
correção via `sed -i` (para trocar `Query(default=None, ...)` por `Query(...)`, depois que o
FastAPI rejeitou `default=` dentro de `Annotated`) corrompeu o arquivo com bytes nulos —
`sed -i` neste ambiente de mount não é uma alternativa segura ao heredoc completo mesmo para
uma substituição de uma linha; abandonado em favor de reescrever o arquivo inteiro de novo.
Nenhum caso ficou sem resolução ou exigiu retrabalho de lógica.

## O que foi deliberadamente NÃO implementado nesta etapa

Confirmado por leitura do código final e por `docs/analise-arquitetural-central-financeira.md`
(seção 4): `Alerta`/insights ficam de fora (fora da lista de 11 endpoints pedida
explicitamente, e exigiriam uma regra de negócio nova — vedado pelo pedido original). A
Agenda Financeira (`/agenda`) lista só ocorrências já materializadas (`Transacao`s
`PENDENTE` reais e faturas com vencimento futuro) — não projeta ocorrências futuras ainda
não geradas de `ContaRecorrente`, que são lazy por design (só passam a existir quando
`gerar-ocorrencias-pendentes` é chamado). Isso é um gap consciente, documentado antes da
implementação, não um esquecimento: implementar a projeção exigiria ou reescrever a lógica
de datas do `ContaRecorrenteService` dentro da Central (duplicação de regra, vedada) ou
`ContaRecorrenteService` expor um novo método de "próximas N datas sem persistir" (mudança
de escopo além do que foi pedido nesta etapa).

## Conclusão

A implementação segue a arquitetura aprovada na análise prévia sem nenhum desvio: zero
Repository próprio, zero SQL direto, zero regra de negócio nova, zero duplicação de cálculo
— as três invariantes declaradas no docstring do Service foram verificadas linha a linha no
código final, não só assumidas do design. O achado real desta etapa (validação ausente de
`mes`/`ano`/`dias`, causando 500 em vez de 422) foi corrigido dentro do escopo permitido —
validação de formato de entrada é responsabilidade do Router, não uma regra de negócio nova,
e a correção não tocou `CentralFinanceiraService`, `Repository` ou `Model` algum. As demais
observações (margem defensiva assimétrica em `FinanciamentoService`, limite implícito de 100
itens herdado dos Services de domínio, N+1 aceitável em `indicadores_gerais`, dependência de
ordenação padrão do Repository de Fatura) são registradas para contexto futuro, nenhuma
exige ação nesta etapa. Suíte completa: 788 testes passando (471 unitários + 317 de
integração). `alembic check` confirma zero migration pendente após a correção de validação
(mudança restrita ao Router, sem impacto de schema).
