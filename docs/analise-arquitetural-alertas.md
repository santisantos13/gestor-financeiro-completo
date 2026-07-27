# Alertas — backend + frontend (2026-07-26)

## 1. Escopo desta entrega

Duas entregas na mesma sessão, documentadas no mesmo arquivo (seções 1-7:
backend; seção 8: frontend). Backend: CRUD + avaliação em tempo real
(`AlertaRepository`/`AlertaService`/`schemas/alerta.py`/`api/routes/alerta.py`,
que já existiam escritos de uma etapa anterior, nunca conectados, finalizados
e testados nesta sessão). Frontend (item `t139` do roadmap, entrega seguinte
na mesma sessão): sino de notificações no `Header`, drawer de lista
(pausar/reativar/editar/excluir) e formulário de criação/edição.

## 2. O que já existia vs. o que faltava

`app/models/alerta.py` (model + migração inicial já criava a tabela `alertas`),
`app/repositories/alerta_repository.py`, `app/schemas/alerta.py` e
`app/services/alerta_service.py` já estavam escritos, com um design coerente e
bem documentado — mas nunca conectados: sem entrada em `app/api/deps.py`, sem
router, sem registro em `main.py`, sem nenhum teste. Ficaram como arquivos
`untracked` no git por várias sessões seguidas.

Faltava: `get_alerta_repository`/`get_alerta_service` em `deps.py`,
`app/api/routes/alerta.py` (CRUD REST), `app.include_router(alerta_router)` em
`main.py`, suíte de testes (unitário + integração) e — descoberto só ao rodar o
primeiro teste de integração real — uma correção genuína de um bug no schema
(seção 4).

## 3. Modelo de domínio: Alerta é a REGRA, não um log de notificações

`Alerta` é a regra configurada pelo usuário (ex: "avise quando o cartão passar de
90% do limite"), **não** um histórico de notificações já disparadas. Não existe
uma tabela de "notificações enviadas" — `ultima_disparada_em` é um único
timestamp, sobrescrito a cada avaliação, nunca uma lista.

`disparado`/`mensagem` em `AlertaRead` são **campos calculados em tempo real**
(nunca persistidos), mesmo padrão de `limite_disponivel` (Cartão) e `saldo_atual`
(Conta): toda leitura de um Alerta (`criar`/`obter`/`listar`/`atualizar`) reavalia
a condição contra o estado atual da entidade referenciada, via `_com_avaliacao`.
Um alerta desativado (`ativo=False`) nunca é avaliado — `disparado`/`mensagem`
ficam `None`, evitando gastar uma leitura à toa e evitando marcar
`ultima_disparada_em` de uma regra que o usuário pausou.

5 tipos suportados (`TipoAlerta`, já existente em `enums.py` desde o início do
projeto): `LIMITE_CARTAO`, `VENCIMENTO_FATURA`, `VENCIMENTO_CONTA_RECORRENTE`,
`META_ATINGIDA`, `SALDO_BAIXO`. Cada um mapeia para exatamente uma entidade
referenciada (`_ENTIDADE_DO_TIPO`), nunca aceita do cliente — sempre derivado do
`tipo`, eliminando a possibilidade de um par `tipo`/`entidade_tipo` inconsistente
vindo da borda da API.

`AlertaService` nunca acessa Repository de outra entidade — reaproveita
`CartaoService.obter()`/`FaturaService.listar_recentes()`/
`ContaRecorrenteService.obter()`/`MetaService.obter()`/`ContaService.obter()`,
cada um já validando posse (404 uniforme) e expondo os campos calculados que a
avaliação precisa (`limite_disponivel`, `status_calculado`, `proxima_execucao`,
`concluida_em`, `saldo_atual`) — nenhum desses cálculos é duplicado aqui.

## 4. Bug real encontrado ao escrever o primeiro teste de integração

`Alerta.condicao` é uma coluna `String(500)` — guarda o parâmetro do gatilho
como JSON serializado (ex: `'{"limite_percentual": 90}'`). `AlertaService.
_normalizar_condicao` já serializava corretamente na escrita (`criar`/
`atualizar`), e `_com_avaliacao` já desserializava para uso interno na avaliação
— mas **nunca escrevia esse valor desserializado de volta para
`AlertaRead.condicao`**. O primeiro teste de integração real (`POST /alertas`)
quebrou com um erro de validação Pydantic: `condicao` chegava como a string JSON
crua no lugar de um `dict`.

Correção: **não** mutar o atributo mapeado `alerta.condicao` diretamente (isso
arriscaria o SQLAlchemy tentar persistir um `dict` como coluna `String` na
próxima `flush()`, quebrando silenciosamente ou incorretamente dependendo do
backend). Em vez disso, um `field_validator(mode="before")` em
`AlertaRead.condicao` (`schemas/alerta.py`) desserializa a string para `dict` na
borda do schema — mesmo mecanismo (`field_validator`) já usado em outros
schemas do projeto (`TagCreate`, `MetaCreate`, `AnexoCreate`), só que aplicado no
lado de SAÍDA em vez de entrada.

## 5. Router — sem soft delete separado

Diferente de Meta/Financiamento (que têm uma rota `DELETE` soft + uma
`/permanente` hard), Alerta só tem uma rota `DELETE` — sempre exclusão
definitiva. Motivo: `ativo` já é um campo comum de `AlertaUpdate` (pausar/
reativar é só um `PATCH {"ativo": false}`), então não existe um "estado
intermediário" que uma segunda rota de soft-delete precisaria representar.

`tipo`/`entidade_id` são imutáveis após a criação — só `condicao`/`ativo` são
aceitos em `AlertaUpdate`. Retargetar um alerta para outra entidade é, na
prática, um alerta diferente: o cliente exclui e cria outro.

## 6. Testes

Unitário (`tests/unit/test_alerta_service.py`, 20 testes): mesmo nível de
isolamento de `test_central_financeira_service.py` — fakeia os Services de
domínio (não o Repository de cada um), já que `AlertaService` só orquestra
`obter()` deles. Cobre: derivação de `entidade_tipo`, validação de posse (404
cross-usuário), validação/normalização de `condicao` por tipo, avaliação dos 5
tipos de gatilho (dispara/não dispara), alerta desativado nunca avaliado,
entidade referenciada excluída não quebra a listagem (defensivo), e a
desserialização de `condicao` (regressão do bug da seção 4).

Integração (`tests/integration/test_alerta_flow.py`, 12 testes): TestClient +
SQLite real. Cobre autenticação obrigatória em todas as rotas, isolamento entre
usuários (criar/listar/obter/excluir), validação 422 de `condicao` malformada, e
um teste ponta-a-ponta real de `LIMITE_CARTAO` (cria cartão, confirma que não
dispara sem compra, lança uma `Transacao` de cartão via `POST /transacoes`,
confirma que dispara depois).

Suíte completa (655 testes unitários + toda a integração, arquivo por arquivo)
revalidada depois da mudança — nenhuma regressão.

## 7. Fora de escopo do backend

- Envio de notificação de verdade (push/e-mail) — `Alerta` hoje só é avaliado
  quando alguém faz uma requisição HTTP (`GET /alertas`); não existe nenhum
  worker/scheduler rodando em background. Isso significa que o usuário só "vê"
  um alerta disparado quando abre o sino no frontend — não há push proativo.
  Fica registrado como próximo passo em aberto, fora do pedido original.
- `SALDO_BAIXO` agregando todas as contas (`entidade_id=None`) — toda regra
  criada hoje aponta para uma conta específica. `entidade_id` é `nullable` no
  model só porque esse modo agregado é um recorte futuro em aberto.

## 8. Frontend — sino + lista + criar (escopo completo, item `t139`)

O item do roadmap dizia só "sino + lista", mas isso, ao pé da letra, entregaria
um sino permanentemente vazio: sem uma UI de criação, nenhum alerta jamais
existiria para aparecer na lista. Apresentado ao usuário como uma decisão
explícita (`AskUserQuestion`) — escolhida a opção completa: sino + lista +
criação/edição.

### 8.1. Peças novas

- `types/alerta.ts` — espelha `AlertaCreate`/`AlertaUpdate`/`AlertaRead` 1:1.
  `TipoAlerta` é reaproveitado de `types/enums.ts` (já existia, criado junto
  com `TipoEntidadeReferenciavel` na etapa de Anexo). `condicao` é tipado como
  união discriminada por chave presente (`CondicaoLimiteCartao |
  CondicaoDiasAntes | CondicaoSaldoMinimo | null`) em vez de um `dict` genérico
  — o formulário e a lista sempre sabem qual campo esperar olhando só para
  `tipo`.
- `services/alertaService.ts` + `hooks/useAlertaQueries.ts` — um hook por
  endpoint, mesmo molde de `tagService`/`useTagQueries`. Sem
  `useDesativarAlerta`/`useReativarAlerta` dedicados: pausar/reativar é só
  `useAtualizarAlerta({ ativo })`, mesmo `PATCH` usado para editar `condicao`
  (não existe rota separada no backend).
- `lib/alertaDescricao.ts` — vocabulário de exibição centralizado
  (`TIPO_ALERTA_LABEL`, ícone por tipo via `ICONE_POR_ORIGEM` já existente, e
  `descreverCondicaoAlerta` — descreve a REGRA em si, não o resultado da
  avaliação). Usado tanto pela lista (para alertas pausados/não disparados,
  que não têm `mensagem`) quanto pelo formulário (preview ao vivo).
- `schemas/alerta.ts` — um único `zodResolver` cobre os 5 `tipo` via
  `superRefine` condicional, em vez de 5 schemas separados: `AlertaFormDialog`
  é um único modal que troca de "modo" conforme o `tipo` escolhido.
- `components/domain/alerta/AlertaFormDialog.tsx` — `tipo`/`entidade_id` só
  são editáveis na CRIAÇÃO; em modo edição aparecem desabilitados (imutáveis
  no backend, ver seção 5). O picker de entidade (`EntidadeField`) troca de
  fonte conforme `tipo`: `useCartoes`/`useContas`/`useMetas`/
  `useContasRecorrentes` (os hooks de CRUD real, não os agregadores de
  `central-financeira`) — os 4 hooks sempre rodam, mas só o do `tipo` atual
  importa para o usuário (cache compartilhado com o resto do app, sem custo
  de rede extra perceptível). Trocar `tipo` na criação esvazia
  `entidade_id` (a lista de opções muda, o id antigo quase certamente não
  existe na nova).
- `components/domain/alerta/AlertasDrawer.tsx` — lista TODOS os alertas
  (`apenas_ativos=false`, precisa dos pausados para oferecer "Reativar"). Um
  alerta disparado mostra `alerta.mensagem` (já pronta, calculada pelo
  backend); um alerta pausado ou ainda não disparado mostra a regra via
  `descreverCondicaoAlerta` (não há `mensagem` nesse caso). Nomes de entidade
  (Cartão/Conta/Meta/Conta Recorrente) são resolvidos aqui via as mesmas 4
  listagens do formulário — `AlertaRead` nunca traz o nome, só `entidade_id`.
- `Header.tsx` — novo botão de sino (`Bell`), mesmo padrão do botão de
  Central de Atividades já existente (`ListTree`/`AtividadesRecentesDrawer`).
  Contador (badge vermelho) mostra quantos alertas estão `disparado=true`
  agora — reavaliado a cada vez que a query de alertas roda (sem polling
  novo, sem push: mesma limitação documentada na seção 7, "avaliado só sob
  demanda").

### 8.2. Por que não reaproveitar os hooks de `central-financeira`

`useContasQuery`/`useCartoesQuery`/`useMetasQuery` (de
`useCentralFinanceiraQueries.ts`) existem, mas são endpoints agregadores
somente-leitura do Dashboard — não é o mesmo contrato de dado que o picker de
entidade precisa (ex.: já vêm formatados para cards, alguns hard-codam
`apenas_ativos=True`). O picker usa os hooks de CRUD real
(`useCartaoQueries`/`useContaQueries`/`useMetaQueries`/
`useContaRecorrenteQueries`), a mesma fonte de verdade que as páginas
`/cartoes`, `/contas`, `/metas` e `/recorrentes` usam.

### 8.3. Testes

`AlertaFormDialog.test.tsx` (3 testes): criação bem-sucedida de um alerta
LIMITE_CARTAO (picker de cartão + campo de percentual), validação client-side
quando nenhuma entidade é selecionada, e a imutabilidade de `tipo`/
`entidade_id` em modo edição (campos desabilitados, `atualizar` só manda
`condicao`). `AlertasDrawer.test.tsx` (3 testes): exibição da `mensagem` já
pronta para um alerta disparado, pausar (`PATCH { ativo: false }`) e excluir
após confirmação (`ConfirmAction`).
