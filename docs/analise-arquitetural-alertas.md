# Alertas — backend (2026-07-26)

## 1. Escopo desta entrega

Só o **backend** (CRUD + avaliação em tempo real). O frontend (sino de notificações
+ lista, item `t139` do roadmap) é uma entrega separada — este documento cobre
exclusivamente `AlertaRepository`/`AlertaService`/`schemas/alerta.py`/
`api/routes/alerta.py`, que já existiam escritos (de uma etapa anterior, nunca
conectados) e foram finalizados, testados e conectados nesta sessão.

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

## 7. Fora de escopo desta entrega

- Frontend (sino + lista) — próxima entrega, `t139`.
- Envio de notificação de verdade (push/e-mail) — `Alerta` hoje só é avaliado
  quando alguém faz uma requisição HTTP (`GET /alertas`); não existe nenhum
  worker/scheduler rodando em background. Isso significa que o usuário só "vê"
  um alerta disparado quando abre o sino no frontend — não há push proativo.
  Fica registrado como próximo passo em aberto, fora do pedido original.
- `SALDO_BAIXO` agregando todas as contas (`entidade_id=None`) — toda regra
  criada hoje aponta para uma conta específica. `entidade_id` é `nullable` no
  model só porque esse modo agregado é um recorte futuro em aberto.
