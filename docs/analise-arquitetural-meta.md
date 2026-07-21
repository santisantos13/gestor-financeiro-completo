# Análise arquitetural — CRUD de Meta

Décima segunda entidade de domínio. Diferente de Financiamento/Empréstimo (onde o domínio já
vinha inteiramente especificado pelo usuário), Meta tem um ponto genuinamente ambíguo na
regra de cálculo — tratado como conflito real abaixo, com uma recomendação clara, mas
registrado para confirmação antes de qualquer código, como pedido.

## O que já existe (não é código novo)

`app/models/meta.py` já existe desde a modelagem inicial do domínio: `descricao`,
`valor_alvo`, `data_alvo` (opcional), `conta_id` (opcional, FK para `Conta`), `ativo`,
`usuario_id`. `Transacao.meta_id` também já existe (FK opcional, `ondelete=SET NULL`),
aceito e persistido por `TransacaoService.criar()`/`atualizar()` desde a implementação de
Transação — mas deliberadamente SEM validação de posse cruzada (decisão YAGNI, documentada
em `docs/analise-arquitetural-transacao.md`: "`meta_id` ganha a mesma validação quando o CRUD
da própria entidade for implementado"). É a última peça dessa dívida técnica intencional a
ser fechada — depois de Parcelamento, Conta Recorrente, Financiamento e Empréstimo já terem
fechado a mesma lacuna para seus respectivos vínculos.

O docstring do model já registra a intenção de cálculo dinâmico: *"Não guarda `valor_atual`
como coluna: o progresso é sempre calculado pela camada de serviço somando `Transacao.valor`
onde `meta_id` aponta pra essa Meta [...] a mesma lógica já usada no saldo de Conta."*

## Conflito real (resolvido, recomendação abaixo): qual é a fonte do cálculo de valor_acumulado?

O pedido do usuário diz: *"calculados dinamicamente a partir das transações relacionadas
(quando houver vínculo com Conta) ou conforme a regra já prevista no domínio."* Isso admite
duas leituras:

1. **Duas regras de cálculo diferentes**, escolhidas condicionalmente: se a Meta tem
   `conta_id`, o progresso viria do saldo/transações daquela Conta; se não tem, cairia numa
   regra alternativa (a de somar por `meta_id`).
2. **Uma única regra**, já prevista no domínio desde a modelagem original (o docstring do
   model, citado acima): soma de `Transacao.valor` filtrada por `meta_id`, e `conta_id` é só
   uma referência opcional/organizacional (o "cofrinho" dedicado à meta), sem participar do
   cálculo.

**Recomendação: opção 2.** Motivos:

- É a regra que já está documentada no próprio model, escrita antes desta etapa — "a regra já
  prevista no domínio" da frase do pedido bate exatamente com isso.
- A opção 1 criaria dois significados diferentes para "valor_acumulado" dependendo de um
  campo opcional estar preenchido ou não, quebrando a garantia que todo outro valor
  calculado deste projeto tem: uma fórmula determinística e única (`Conta.saldo_atual`,
  `Cartao.limite_disponivel`, `saldo_devedor` de Financiamento/Empréstimo — sempre uma regra
  só, nunca duas alternativas).
- Tecnicamente, "saldo de uma Conta" já é uma métrica que existe e é exposta por
  `GET /contas/{id}` — se a intenção fosse literalmente "usar o saldo da conta vinculada",
  isso duplicaria/confundiria com o saldo real da conta (que pode ser usada para muitas outras
  coisas além dessa meta específica), e a Meta deixaria de ter progresso próprio quando não
  tivesse `conta_id`, o que parece incompatível com `conta_id` ser explicitamente opcional.
- Mantém `meta_id` como o único vínculo que efetivamente conecta uma `Transacao` a uma Meta —
  o mesmo padrão de "aporte marcado" já ligado à Transação, sem exigir que o aporte também
  esteja necessariamente numa conta específica.

**Fórmula proposta**, espelhando exatamente `ContaRepository.somar_transacoes_pagas`:

```
valor_acumulado = SUM(Transacao.valor WHERE meta_id = meta.id AND status = PAGO,
                       RECEITA soma positivo, DESPESA soma negativo)
percentual = (valor_acumulado / valor_alvo) * 100, sem teto artificial (pode passar de 100%
             se a meta for superada - mesma filosofia de Cartao.limite_disponivel não ser
             artificialmente limitado)
```

RECEITA com `meta_id` = um aporte para a meta; DESPESA com `meta_id` = uma retirada da meta
(reduz o progresso) — mesma semântica de sinal já usada no saldo de Conta. Só transações
`PAGO` contam (mesmo raciocínio: `PENDENTE` ainda não moveu dinheiro de verdade).

Se essa leitura estiver errada e a intenção for de fato uma regra diferente quando há
`conta_id`, preciso de mais detalhe antes de codar (ex: "usar o saldo da conta vinculada" tem
pelo menos três variações possíveis: saldo total da conta, soma só das transações daquela
conta com `meta_id`, ou soma de todas as transações da conta desde a criação da meta) — sinalizando
aqui antes de qualquer implementação, como pedido.

## Decisões de modelagem menores (sem ambiguidade, só formalizando)

**Nome único por usuário, mesmo padrão de Tag/Cartão.** O campo já existente é `descricao`
(não `nome`) — `UniqueConstraint(usuario_id, descricao)` nova no model, com a mesma semântica
de reativação já usada em `TagService.criar()`/`CartaoService.criar()`: se a colisão é com
uma Meta desativada, reativa (payload sobrescreve por completo) em vez de bloquear; se é com
uma Meta ativa, `ConflictError` (409). Renomear (`PATCH descricao`) não funde/reativa com uma
Meta inativa de mesmo nome — mesma decisão de Tag/Cartão, bloqueia com 409.

**`conta_id` opcional: validação de posse quando informado, sem exigir conta ativa.** Mesmo
padrão de `CartaoService._validar_conta_do_usuario` (existência + mesmo usuário, 404
uniforme para "não existe" e "é de outro usuário") — mas sem a checagem extra de `ativo` que
`TransacaoService._validar_conta_ativa` tem, porque vincular uma Meta a uma Conta não move
dinheiro nem depende da conta estar operacional; é só uma referência.

**Soft delete, mesmo padrão de Tag/Cartão/Conta/Categoria.** `DELETE /metas/{id}` marca
`ativo=False`, sem apagar a linha. Transações que já têm `meta_id` apontando pra essa Meta
continuam intactas (o histórico de aportes não é afetado por soft delete, mesma lógica do
vínculo N-N de Tag). `MetaUpdate` também inclui `ativo: bool | None`, permitindo reativar via
`PATCH` além do `DELETE` dedicado — mesma forma de `TagUpdate`/`CartaoUpdate`.

**`meta_id` em `TransacaoService`: fecha a última lacuna YAGNI, sem faixa nem duplicidade.**
Diferente de `financiamento_id`/`emprestimo_id`/`parcelamento_id` (que têm `numero_parcela`
com faixa e unicidade), Meta não tem conceito de parcela — múltiplos aportes para a mesma
Meta são o comportamento normal e esperado, não um erro. A nova validação
(`_validar_meta_ativa`) é só posse (existe + pertence ao usuário) e bloqueio de meta
inativa (mesmo espírito de `_validar_conta_ativa`/`_validar_cartao_ativo`: não lançar uma
transação nova contra algo que o usuário já "arquivou"). Sem `UniqueConstraint` nova em
`Transacao` — não há nada a proteger de duplicidade aqui.

**Sem Repository próprio para a agregação.** `MetaRepository.somar_transacoes_pagas(meta_id)`
mora no próprio `MetaRepository` (não em `TransacaoRepository`) — mesmo raciocínio já usado em
`ContaRepository.somar_transacoes_pagas`: a query agrega sobre `Transacao`, mas a
responsabilidade conceitual ("progresso de uma Meta") pertence ao Repository da entidade que
está calculando o valor derivado, não ao Repository da tabela-fonte. `MetaService` não
compõe `TransacaoService` (diferente de Parcelamento/ContaRecorrente/Financiamento/
Empréstimo) — Meta nunca cria/edita/paga uma `Transacao` por conta própria, só lê.

## Escopo explicitamente fora (confirmado, mesmo pedido do usuário)

Notificações, automações, integração com `Alerta` (mesmo `TipoAlerta.META_ATINGIDA` já
existente em `enums.py` não ganha nenhuma lógica nova nesta etapa — só o enum, sem
Service/trigger), scheduler, IA, histórico de progresso (sem tabela de snapshot temporal —
o progresso é sempre o valor "ao vivo" no momento da consulta, nunca uma série histórica).

## Resumo do que muda em cada camada

- **Model** (`app/models/meta.py`): adicionar `UniqueConstraint(usuario_id, descricao)`.
- **Repository** (novo `MetaRepository`): CRUD genérico + `listar_do_usuario` (padrão
  Tag/Cartão) + `buscar_por_descricao` (posse de nome, padrão Tag/Cartão) +
  `somar_transacoes_pagas(meta_id)` (padrão `ContaRepository`).
- **Schemas** (novo `app/schemas/meta.py`): `MetaCreate`, `MetaUpdate` (todos os campos
  opcionais, inclui `ativo`), `MetaRead` (inclui `valor_acumulado`/`percentual` calculados,
  nunca colunas do model — mesmo padrão de `CartaoRead.limite_disponivel`).
- **Service** (novo `MetaService`): `criar` (com reativação por nome), `obter`, `listar`,
  `atualizar`, `desativar`, e o cálculo de progresso anexado como atributo transiente antes de
  devolver ao Router (mesmo padrão de `CartaoService._com_limite_disponivel`).
- **`TransacaoService`**: novo `meta_repo` no construtor, `_validar_meta_ativa` chamada em
  `criar()`/`atualizar()`, `meta_id` como novo filtro opcional em `listar()`/
  `TransacaoRepository.listar_do_usuario`.
- **Router** (novo `app/api/routes/meta.py`): `POST`/`GET`/`GET {id}`/`PATCH {id}`/
  `DELETE {id}` — CRUD completo, diferente de Financiamento/Empréstimo (que não têm PATCH).
- **`deps.py`/`main.py`**: wiring padrão (`get_meta_repository`, `get_meta_service`,
  `meta_repo` adicionado a `get_transacao_service`, router registrado).
- **Migration**: `UniqueConstraint(usuario_id, descricao)` em `metas` — não mexe em
  `Transacao` (nenhuma constraint nova lá, ver acima).
