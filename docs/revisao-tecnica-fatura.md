# Revisão técnica — CRUD de Fatura

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada** — implementação segue exatamente a
arquitetura validada em `docs/analise-arquitetural-fatura.md`; nenhum desvio não
documentado foi identificado nesta revisão.

## Resumo

Segue `Router → Service → Repository`, reaproveitando os padrões já validados
(posse via anti-enumeração 404, soft-delete-vs-unicidade quando aplicável) e introduzindo
três coisas novas ao projeto: posse **transitiva** (Fatura não tem `usuario_id` próprio),
um CRUD sem PATCH genérico (ações de negócio explícitas em vez disso), e um Repository
mínimo de Transação criado só para dar suporte ao pagamento de fatura. 253 testes passam
(31 unitários com repositories falsos, 22 de integração via `TestClient`, mais os 200
pré-existentes de outras camadas).

## Mudanças de modelagem (conforme `docs/analise-arquitetural-fatura.md`)

`Fatura.transacao_pagamento_id` (FK singular, exigia `use_alter=True` pela dependência
cíclica) foi removido; `Transacao.fatura_paga_id` (nullable, mesma forma de `fatura_id`)
assumiu seu lugar, permitindo N transações de pagamento por fatura (pagamento parcial) e
eliminando a dependência cíclica (as duas FKs agora apontam na mesma direção,
`Transacao → Fatura`). Novo `CheckConstraint` (`ck_transacao_fatura_compra_xor_pagamento`)
garante no nível do banco que uma transação nunca é simultaneamente compra e pagamento.
`StatusFatura` ganhou `PARCIALMENTE_PAGA`; o `CHECK` da coluna `status` foi ampliado para
incluir esse valor só para manter `alembic check` limpo — não porque ele algum dia seja
gravado ali (ver próxima seção). Migration validada com o ciclo completo
(upgrade/downgrade/upgrade/check/current), usando `batch_alter_table` em todas as operações
(SQLite não suporta `DROP`/`ADD CONSTRAINT` fora de modo batch).

## `status` e `valor_total`: derivados sem tocar a coluna real

O risco técnico mais delicado desta implementação: `Fatura.status` e `Fatura.valor_total`
são colunas REAIS mapeadas pelo SQLAlchemy. Fazer `setattr(fatura, "status", valor_derivado)`
marcaria o objeto como sujo (`dirty`) na sessão, com risco real de um valor que nunca deveria
ser persistido (ex: `PARCIALMENTE_PAGA`) ser commitado por acidente num `flush()` posterior
na mesma request. Resolvido anexando os valores derivados em atributos **transientes com
nomes diferentes** (`status_calculado`, `valor_total_calculado`) — nunca sobrescrevendo o
atributo mapeado. `FaturaRead` usa `Field(validation_alias=...)` para expor esses atributos
sob os nomes `status`/`valor_total` na API, sem qualquer colisão com a leitura da coluna
real. Testado explicitamente (`test_valor_total_fechada_e_o_snapshot_congelado_nao_a_soma_atual`)
que uma "compra hipotética" registrada depois do fechamento não muda o valor exibido.

## Posse transitiva: primeira entidade sem `usuario_id` próprio

`Fatura` não tem `usuario_id` — a posse é sempre via `Fatura.cartao.usuario_id`.
`FaturaService._buscar_fatura_do_usuario()` busca a fatura, depois valida o cartão,
devolvendo a MESMA mensagem 404 (`"Fatura não encontrada."`) tanto para "não existe" quanto
para "existe mas o cartão é de outro usuário" — mesmo raciocínio anti-enumeração de sempre,
com um cuidado extra de mensagem: reusar a validação genérica de cartão
(`_validar_cartao_do_usuario`, que devolve `"Cartão não encontrado."`) para esse caso
vazaria a entidade errada na mensagem de erro. As duas validações foram mantidas
deliberadamente separadas por esse motivo, mesmo sendo parecidas.

## CRUD sem PATCH genérico

Diferente de Conta/Categoria/Tag/Cartão, `Fatura` não expõe `PATCH /faturas/{id}`. Datas e
`cartao_id` são imutáveis por design (derivadas na criação); as únicas transições válidas de
estado (fechar ciclo, registrar pagamento) são ações de negócio com efeitos colaterais
próprios (congelar `valor_total`, criar uma `Transacao`) — modelar isso como um PATCH
genérico de `status` seria tanto inexpressivo (o cliente não escolhe o valor, o Service
calcula) quanto perigoso (abriria brecha para setar `status` diretamente, contornando as
regras de `fechar()`/`registrar_pagamento()`). Por isso `POST /faturas/{id}/fechar` e
`POST /faturas/{id}/pagamentos` existem como endpoints de ação dedicados — decisão
já antecipada na arquitetura aprovada, aqui apenas confirmada como correta na prática.

## `TransacaoRepository`: mínimo, deliberadamente incompleto

`registrar_pagamento()` precisa persistir uma `Transacao` (a linha de pagamento), mas o CRUD
de Transação está fora de escopo desta etapa. Criado `app/repositories/transacao_repository.py`
com só `model = Transacao` (nada além do CRUD genérico herdado) — não é o Repository final
de Transação, é o mínimo necessário para Fatura funcionar. Documentado explicitamente no
docstring do arquivo para não ser confundido com uma implementação completa quando o CRUD de
Transação for feito de verdade.

## Validações e regras de negócio

`FaturaCreate` só aceita `cartao_id` e `mes_referencia` — `data_fechamento`/`data_vencimento`
nunca vêm do cliente, sempre derivadas de `Cartao.dia_fechamento`/`dia_vencimento` por
`_calcular_datas_ciclo()`. Dia inexistente no mês (ex: 31 em fevereiro) usa o último dia
válido (`calendar.monthrange`); vencimento numericamente menor ou igual ao fechamento vira
mês seguinte (caso comum: fecha dia 28, vence dia 5). `mes_referencia` é validado como
primeiro dia do mês no Schema (`field_validator`, rejeita com 422 em vez de normalizar
silenciosamente — evita mascarar um provável erro de digitação do cliente).

`registrar_pagamento()` bloqueia fatura `ABERTA` (`BusinessRuleError`) — o valor emitido
ainda não existe de forma definitiva para "pagar". `excluir()` só permite fatura `ABERTA` E
sem nenhuma transação vinculada (compra ou pagamento) — qualquer histórico real torna a
exclusão permanente-e-bloqueada; Fatura não tem soft delete porque não é um cadastro que se
"desativa", é um registro histórico de ciclo.

`_derivar_status()` prioriza `PAGA` > `ATRASADA` > `PARCIALMENTE_PAGA` > `FECHADA` — uma
fatura vencida com saldo devedor é tratada como atrasada mesmo tendo recebido pagamento
parcial (o risco importa mais que o progresso). Testado explicitamente
(`test_status_atrasada_tem_prioridade_sobre_parcialmente_paga`).

## Observações registradas, não implementadas

- **Geração automática de próximos ciclos e resolução lazy por data** — explicitamente fora
  de escopo por pedido do usuário; `criar()` é hoje a única forma de instanciar uma Fatura.
  Quando o CRUD de Transação existir, o método de resolução por data descrito na análise
  arquitetural deve reaproveitar `_calcular_datas_ciclo`/`buscar_por_cartao_e_mes` já
  implementados aqui, não recriá-los.
- **Imutabilidade de Transação de fatura fechada** (valor/data/cartão/parcelamento
  travados) — regra pertence ao futuro `TransacaoService`, não pode ser implementada agora
  (não há `TransacaoService`). `FaturaRepository.existe_transacao_vinculada` já dá a
  `TransacaoService` futuro a query que ele vai precisar para essa checagem.
- **Resolução de estorno por data** — mesma situação: depende de `TransacaoService`
  existir. A arquitetura já está pronta para isso (estorno é só uma `Transacao` comum tipo
  `RECEITA`); nada a ajustar em `Fatura` quando chegar a hora.
- **Fatura com `valor_total = 0` no fechamento não é classificada como `PAGA`** — fica
  `FECHADA` (ver guarda `valor_total > 0` em `_derivar_status`). Caso de borda raro (ciclo
  fechado sem nenhuma compra); decisão de exibição, não uma regra crítica.

## Conclusão

Sem problema de arquitetura, segurança, duplicação ou regra de negócio ausente identificado
nesta revisão. As três decisões mais delicadas da arquitetura aprovada — snapshot no
fechamento, pagamento parcial via FK invertida, e status majoritariamente derivado — foram
implementadas exatamente como especificado em `docs/analise-arquitetural-fatura.md`, com
cobertura de teste direta para cada uma. O CRUD de Fatura está encerrado (dentro do escopo
combinado: sem geração automática, sem integração com Parcelamento/Financiamento) e segue o
mesmo padrão de qualidade dos CRUDs de Conta, Categoria, Tag e Cartão.
