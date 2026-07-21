# Metas: aportes e resgates viram transferências internas, não receita/despesa

Pedido do usuário (verbatim): "refatore o módulo de Metas para que os aportes e resgates sejam
tratados como transferências internas, e não como despesas ou receitas. Isso deixa o patrimônio
consistente, evita distorções nos relatórios e aproxima o sistema do funcionamento de aplicativos
financeiros mais robustos."

Duas decisões de produto confirmadas explicitamente com o usuário antes desta implementação:

1. **Cofrinho automático**: cada Meta ganha, automaticamente, uma Conta dedicada e oculta,
   criada pelo próprio sistema — aportes/resgates viram Transferências reais entre essa conta e
   qualquer outra conta do usuário. Reaproveita a infraestrutura de Transferência/saldo já
   existente; o dinheiro continua contando no patrimônio total.
2. **Congelar histórico**: os aportes antigos (`Transacao` com `meta_id`, RECEITA/DESPESA) ficam
   exatamente como estão — continuam contando em `valor_acumulado` — mas não é mais possível criar
   um aporte assim. Só o comportamento NOVO muda; nenhum dado existente é reescrito ou migrado.

## 0. Por que isso é uma transferência, e não uma transação

O raciocínio é idêntico ao que já justifica `Transferencia` existir como entidade separada de
`Transacao` (ver docstring do model `Transferencia`): um aporte para uma Meta não é dinheiro que
sai do patrimônio do usuário (como uma DESPESA de verdade) nem dinheiro que entra de fora (como uma
RECEITA de verdade) — é dinheiro que só troca de lugar, da conta corrente para o "cofre" da Meta.
Modelar isso como uma `Transacao` DESPESA (o que o sistema fazia até agora) infla artificialmente
os relatórios de gasto do mês com dinheiro que o usuário só guardou, não gastou — exatamente a
distorção que o pedido do usuário identifica.

A infraestrutura para resolver isso **já existe por completo**: `Transferencia` já move dinheiro
entre duas `Conta`s sem gerar `Transacao`, sem entrar em relatório de receita/despesa, e já soma
corretamente no patrimônio (`ContaRepository.somar_transferencias`, usado por
`ContaService._com_saldo`). O único motivo de Meta não usar isso desde o início é que
`Meta.conta_id` sempre foi opcional e puramente organizacional — a peça que falta é dar a toda
Meta uma Conta real e dedicada para ser o destino/origem dessas transferências.

## 1. Conta oculta (o "cofrinho" da Meta)

Novo campo: `Conta.oculta: bool = False`.

Marca uma Conta como gerenciada pelo próprio sistema — nunca aparece em listagens/pickers normais
(`ContasPage`, `AccountSelect`, `TransferenciaFormDialog`, resumo de Contas do Dashboard), mas
**continua contando no patrimônio total** (`saldo_consolidado`), porque o dinheiro nela é real e
pertence ao usuário.

### 1.1 Filtro nas listagens

`ContaRepository.listar_do_usuario` ganha um parâmetro `apenas_visiveis: bool = True`, que filtra
`Conta.oculta.is_(False)` quando `True`. `ContaService.listar` repassa o mesmo parâmetro.

- Toda chamada existente (`ContasPage`, `AccountSelect`, `CartaoFormDialog`'s conta de pagamento,
  `resumo_contas`, `indicadores_gerais.contas_ativas`) **não muda uma linha** — o novo parâmetro
  tem default `True`, então continuam automaticamente escondendo cofrinhos sem precisar saber que
  esse conceito existe.
- `CentralFinanceiraService.saldo_consolidado` é o ÚNICO ponto que passa `apenas_visiveis=False`
  explicitamente — é o cálculo de patrimônio total, que PRECISA somar o saldo de todo cofrinho.

Nenhuma alteração no Frontend é necessária para esconder cofrinhos de `AccountSelect`/
`TransferenciaFormDialog`/`ContasPage`: o backend nunca os inclui na resposta de `GET /contas`
(comportamento padrão), então o Frontend nunca chega a vê-los.

### 1.2 Por que um novo campo, e não um novo `TipoConta`

`TipoConta` (CORRENTE/POUPANCA/CARTEIRA/INVESTIMENTO) descreve a NATUREZA financeira de uma conta
— um cofrinho de Meta não tem uma natureza diferente dessas (o dinheiro está, na prática, guardado
em algum lugar real). `oculta` é ortogonal a isso: é sobre VISIBILIDADE na UI, não sobre natureza.
Um booleano simples evita introduzir um "tipo" que não descreve nada de único.

## 2. `Meta.conta_id` passa a ser obrigatório e 100% automático

Antes: `conta_id` era opcional, escolhido manualmente pelo usuário, e puramente organizacional
("não participa de nenhum cálculo" — decisão documentada em `docs/analise-arquitetural-meta.md`).

Agora: toda Meta tem, sempre, uma Conta dedicada (o cofrinho), criada automaticamente pelo próprio
sistema no momento da criação da Meta — o usuário nunca escolhe nem vê essa conta diretamente.

- `MetaCreate`/`MetaUpdate` **perdem o campo `conta_id`** — não é mais algo que o cliente envia.
  Vincular uma Meta a uma Conta deixou de ser uma decisão do usuário: é uma decisão do sistema, e
  dar ao usuário a impressão de que ele "escolhe" a conta destruiria a garantia central deste
  desenho ("o cofrinho é exclusivo desta Meta, nada mais o usa").
- `MetaRead.conta_id` continua exposto (agora sempre preenchido) — o Frontend usa esse id para
  montar o payload de `POST /transferencias` do aporte/resgate (seção 4), mesmo sem nunca mostrar
  a conta em si ao usuário.
- `MetaService.criar`: ao criar uma Meta nova (não uma reativação), cria também uma `Conta`
  (`nome=f"Cofrinho — {descricao}"`, `saldo_inicial=0`, `oculta=True`, `ativo=True`,
  `tipo=TipoConta.CARTEIRA` — natureza mais próxima de "dinheiro guardado", sem outro efeito) e
  atribui `meta.conta_id` a ela antes de persistir. Reativar uma Meta desativada (mesma descrição)
  **reaproveita o cofrinho que ela já tinha** — não cria um segundo, preservando o progresso já
  acumulado (o mesmo raciocínio que já preservava o histórico de aportes antigos ao reativar).

### 2.1 Exclusão definitiva (hard delete) orquestra o cofrinho também

`MetaService.excluir` (hard delete, nunca bloqueado por aportes vinculados) agora também decide o
que fazer com o cofrinho:

```
se o cofrinho NÃO tem nenhuma Transferencia vinculada (existe_vinculo == False):
    apaga o cofrinho de verdade (ContaRepository.delete) — nunca foi usado, nada a preservar.
senão:
    oculta = False, ativo = False (ContaRepository.update) — o cofrinho vira uma Conta comum,
    desativada, visível em /contas — o usuário nunca perde acesso a um saldo real que já existia.
```

Isso reaproveita EXATAMENTE a mesma checagem que `ContaService.excluir` já usa
(`ContaRepository.existe_vinculo`) — nenhuma lógica nova de "pode apagar ou não", só orquestração.
A alternativa (apagar sempre, ou nunca apagar) foi descartada: apagar sempre um cofrinho com saldo
real destruiria dinheiro do patrimônio silenciosamente; nunca apagar deixaria lixo acumulando para
todo teste/Meta criada e descartada sem nunca ser usada.

### 2.2 Migração de dados: Metas já existentes

Toda Meta já cadastrada (ativa ou desativada, com ou sem `conta_id` organizacional anterior)
precisa ganhar um cofrinho antes de poder receber aportes pelo novo mecanismo. Migração Alembic
de DADO (mesmo padrão de `7544876ab513_seed_categorias_padrao_do_sistema.py`): para cada linha de
`metas`, insere uma nova `Conta` (`oculta=True`, `saldo_inicial=0`) e faz
`UPDATE metas SET conta_id = <novo id>` — **sempre**, mesmo que a Meta já tivesse um `conta_id`
organizacional anterior (esse vínculo antigo nunca teve nenhum efeito em cálculo, então não há
saldo a preservar nele; ver decisão original em `docs/analise-arquitetural-meta.md`). Só depois
disso a coluna `metas.conta_id` vira `NOT NULL`.

## 3. Cálculo de `valor_acumulado`: soma legada + saldo do cofrinho

```python
valor_acumulado = meta_repo.somar_transacoes_pagas(meta.id)       # legado, CONGELADO, inalterado
                + conta_repo.somar_transferencias(meta.conta_id)  # novo, aportes/resgates de verdade
```

`meta_repo.somar_transacoes_pagas` (soma de `Transacao.meta_id`, RECEITA soma/DESPESA subtrai) é
usado **sem nenhuma alteração** — é exatamente o "congelar histórico" pedido: continua somando as
transações antigas para sempre, do jeito que sempre somou.

`conta_repo.somar_transferencias(meta.conta_id)` também é reaproveitado **sem nenhuma alteração**
— já soma "recebido − enviado" de qualquer Transferência ativa envolvendo essa conta (a mesma
função que `ContaService._com_saldo` usa para calcular o saldo de qualquer Conta comum). Como o
cofrinho nunca recebe `Transacao` (está oculto de todo picker de conta/cartão), essa soma É, na
prática, "aportes − resgates" — exatamente o progresso novo da Meta.

Nenhuma fórmula nova foi escrita para isto — as duas somas já existiam, cada uma no Repository da
entidade que a possui; `MetaService` só passou a somar as duas.

## 4. Aporte/Resgate reaproveitam 100% o CRUD de Transferência — nenhuma rota nova

Um "aporte" é, literalmente, `POST /transferencias` com `conta_destino_id = meta.conta_id`. Um
"resgate" é o mesmo endpoint com `conta_origem_id = meta.conta_id`. **Nenhum endpoint novo,
nenhum método novo em `MetaService`/`TransferenciaService`** — o Frontend monta o payload usando o
`conta_id` que já vem em `MetaRead` e chama exatamente o mesmo `useCriarTransferencia` que
`TransferenciaFormDialog` já usa.

Isso significa que todas as validações de `TransferenciaService.criar` (contas distintas, posse,
conta ativa) já protegem aporte/resgate de graça — inclusive o caso "a Meta está desativada": como
uma Meta desativada continua com seu cofrinho `ativo=True` (só a Meta em si está inativa, não a
Conta), aportar numa Meta desativada continua tecnicamente possível pelo endpoint genérico. Isso é
aceito deliberadamente: bloquear exigiria uma validação nova cruzando Transferência↔Meta que não
existe hoje, e o Frontend já não oferece a ação "Aportar"/"Resgatar" numa Meta desativada (mesmo
padrão de qualquer ação que só aparece para entidades ativas no resto do projeto).

### 4.1 Por que não um `AporteMeta`/endpoint dedicado

Um endpoint `POST /metas/{id}/aportar` foi considerado e descartado: ele só faria, por baixo, o
mesmo `TransferenciaService.criar` acima, adicionando uma segunda forma de chegar ao mesmo
resultado (mais superfície de API, mais um lugar para manter em sincronia) sem nenhum ganho de
validação real. A única vantagem seria devolver a `MetaRead` já atualizada numa única resposta —
troca-se isso por uma invalidação de cache no Frontend (`useCriarTransferencia` já invalida
`queryKeys.contas.all`; o hook de aporte/resgate do Frontend invalida `queryKeys.metas.all`
também, mesmo padrão de toda outra mutation que afeta Meta indiretamente).

### 4.2 Filtro novo em `GET /transferencias`: `conta_id`

Necessário para o Frontend conseguir buscar "só as transferências desta Meta" (histórico, seção 5)
sem trazer todas as transferências do usuário para filtrar client-side (que cresceria sem limite
conforme o usuário usa mais o app). `TransferenciaRepository.listar_do_usuario` ganha
`conta_id: int | None = None` (`WHERE conta_origem_id = :conta_id OR conta_destino_id = :conta_id`
quando informado) — mesmo padrão de filtro opcional que `TransacaoRepository.listar_do_usuario`
já tem para `conta_id`/`cartao_id`/etc. `TransferenciaService.listar` e
`GET /transferencias?conta_id=` repassam o parâmetro. Um filtro genericamente útil (não específico
de Meta), reaproveitável por qualquer tela futura que precise do extrato de uma conta.

## 5. Histórico de aportes (`MetaResumoCard`, seção expandida)

Passa a combinar DUAS fontes, já que "congelar" preserva o passado:

- **Legado**: `GET /transacoes?meta_id={id}` (comportamento inalterado, `useAportesDaMeta`
  continua existindo do jeito que está) — aportes antigos, DESPESA/RECEITA, congelados.
- **Novo**: `GET /transferencias?conta_id={meta.conta_id}` — aportes (Transferencia recebida pelo
  cofrinho) e resgates (Transferencia enviada pelo cofrinho) de verdade.

O Frontend mescla as duas listas por data (mais recente primeiro) na mesma seção "Aportes
recentes" — cada item já carrega informação suficiente (valor, data, e se é legado ou
transferência) para o usuário entender a origem sem precisar de um indicador visual elaborado; um
rótulo textual discreto ("via transferência" nos itens novos) é suficiente.

## 6. `Transacao.meta_id`: campo de escrita removido, leitura preservada

- `TransacaoCreate`/`TransacaoUpdate` **perdem o campo `meta_id`** — não é mais possível, pela API,
  marcar uma Transação nova (ou editar uma existente) com uma Meta. Isso fecha a única porta que
  permitia criar uma DESPESA/RECEITA "de aporte" — exatamente o que o pedido pede para eliminar.
- `Transacao.meta_id` (coluna do model), `TransacaoRead.meta_id` (leitura), `Meta.transacoes`
  (relationship) e `MetaRepository.somar_transacoes_pagas`/`desvincular_transacoes` **não mudam
  nada** — são exatamente o mecanismo que sustenta o histórico legado congelado (seção 3) e a
  exclusão definitiva de Meta (que ainda precisa desvincular transações antigas antes de apagar a
  linha). Migração de schema desnecessária: a coluna já existe e já é `nullable`.
- `TransacaoService.criar`/`atualizar` removem o bloco de validação `_validar_meta_ativa`
  (inclusive o método em si, que fica órfão) e param de passar `meta_id=dados.meta_id` ao
  construtor de `Transacao` — toda Transação nova nasce com `meta_id=None` (default do model),
  nunca mais setável.
- `meta_repo` continua no construtor de `TransacaoService` (decisão deliberada de baixo risco:
  removê-lo exigiria editar `app/api/deps.py` e 7 arquivos de teste que constroem
  `TransacaoService(...)` posicionalmente — puro custo de churn sem nenhum ganho funcional). Fica
  documentado no próprio construtor como "não usado para validar `meta_id` desde o Refinamento de
  Transferências de Metas".

## 7. Frontend

- **`MetaFormDialog`**: perde o `AccountSelect` "Conta dedicada (cofrinho)" — não existe mais
  escolha manual, o cofrinho é 100% automático. `metaFormSchema`/`MetaCreate`/`MetaUpdate` (tipos)
  perdem `conta_id`.
- **`TransacaoFormDialog`**: perde o `MetaSelect` — não é mais possível marcar uma transação com
  uma Meta. `metaSelect`/`MetaSelect.tsx` deixa de ser usado nesse formulário (o componente em si
  pode ser removido do projeto, já que não sobra nenhum outro consumidor).
- **Novo `MetaAporteDialog`**: dialog simplificado (mais leve que `TransferenciaFormDialog`) — um
  único `AccountSelect` ("De" para aporte, "Para" para resgate — a Meta em si nunca aparece como
  opção selecionável, é sempre o lado implícito), `CurrencyField`, `DateField`, `TextField`
  descrição opcional. Internamente monta `TransferenciaCreate` com `conta_destino_id`/
  `conta_origem_id = meta.conta_id` conforme o modo (aporte/resgate), chama
  `useCriarTransferencia` (mesmo hook de `TransferenciaFormDialog`, zero código novo de mutação) e
  invalida `queryKeys.metas.all` além do que a mutation já invalida.
- **`MetaActionBar`**: ganha dois botões novos, "Aportar" (ícone `PiggyBank` ou `ArrowDownToLine`)
  e "Resgatar" (`ArrowUpFromLine`) — só visíveis para Meta ativa (mesmo padrão condicional de
  Desativar/Reativar).
- **`MetaResumoCard`**: histórico combinado (seção 5); nenhuma mudança na matemática de
  planejamento (`contribuicao_sugerida_por_periodo` etc., Refinamento anterior) — todos esses
  campos continuam vindo prontos de `MetaRead`, agora só calculados sobre a soma legado+cofrinho.

## 8. O que NÃO muda

- Todo o Refinamento de Metas anterior (frequência de contribuição, planejado x realizado,
  previsão de conclusão, celebração, histórico de datas) — nenhuma fórmula muda, só a fonte de
  `valor_acumulado` que elas consomem.
- `Transferencia` em si — nenhuma regra de `TransferenciaService`/model muda; Meta só passa a ser
  mais um consumidor da mesma infraestrutura que Conta↔Conta já usava.
- Soft delete/reativação de Meta, unicidade de descrição — inalterados.
- Nenhuma Transação/Transferência histórica é apagada, editada ou re-rotulada — "congelar" é
  literal.
