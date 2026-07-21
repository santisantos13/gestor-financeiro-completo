# Análise arquitetural — CRUD de Anexo

Registro de conflitos e decisões de modelagem ANTES da implementação, mesmo processo já
seguido em todas as entidades anteriores (mais recentemente `docs/analise-arquitetural-meta.md`).

## O que já existe (não é código novo, mas MUDA de forma significativa nesta etapa)

`app/models/anexo.py` já existia desde o "modelo inicial do domínio financeiro"
(`f988db1c148b`, migração já aplicada — a tabela `anexos` existe de verdade no banco), mas
nunca teve Router/Service/Repository/testes. O desenho original era **especulativo**: mesma
estratégia polimórfica de `Alerta` (`entidade_tipo` + `entidade_id`, via o enum
`TipoEntidadeReferenciavel`), permitindo em tese anexar um arquivo a QUALQUER entidade
(Conta, Cartão, Fatura, Transação, Parcelamento, Financiamento, Empréstimo, ContaRecorrente,
Meta), com `usuario_id` como FK direta e sem soft delete (só `criado_em`, tratado como
essencialmente imutável).

## Conflito real: o desenho especulativo diverge das regras de domínio agora explícitas

O pedido desta etapa é explícito e **não ambíguo** em três pontos que contradizem o model
atual:

| Regra pedida agora | Model atual (especulativo) |
|---|---|
| "Anexo pertence sempre a uma Transação" | Polimórfico — pode apontar para qualquer entidade |
| "Nunca pertence diretamente ao usuário; posse é sempre transitiva via Transação" | `usuario_id` é FK direta |
| "Soft delete (ativo=False)" | Sem soft delete — só `criado_em`, sem coluna `ativo` |

Diferente do conflito resolvido em `Meta` (onde o pedido do usuário admitia duas leituras
honestas), aqui não há ambiguidade de leitura — a instrução é direta. A decisão é: **o model
`Anexo` é redesenhado nesta etapa**, substituindo `entidade_tipo`/`entidade_id`/`usuario_id`
por uma FK direta e obrigatória `transacao_id`, e adicionando `ativo`. Isso segue o mesmo
precedente já estabelecido neste projeto de que o "modelo inicial" é um placeholder amplo,
refinado para sua forma real quando a entidade ganha seu CRUD explícito com regras de domínio
dadas pelo usuário — o exemplo mais próximo é a redução de escopo de `Parcelamento` (etapa
21), que também partiu de um desenho inicial mais amplo do que o pedido real.

**`TipoEntidadeReferenciavel` permanece intacto, sem alteração.** É infraestrutura
compartilhada pensada também para `Alerta` (ainda não implementado), que plausivelmente
continua precisando de referência polimórfica de verdade — um alerta de vencimento de
`Fatura` ou de limite de `Cartão` não tem como ser "sempre uma Transação". `Anexo` só deixa
de usar esse enum; nada nele é removido ou renomeado, para não antecipar decisão de uma
entidade que ainda não teve suas regras de domínio definidas pelo usuário.

**`Usuario.anexos` (relationship direta) é removida.** Já que a posse deixa de ser direta,
não faz sentido manter uma FK/relationship direta de `Usuario` para `Anexo`. Uma consulta
"todos os anexos do usuário, de todas as transações" não está no escopo pedido (o pedido fala
em anexar a UMA transação, nunca em uma visão agregada cross-transação) — se vier a ser
necessária no futuro, é uma extensão aditiva (`AnexoRepository` ganhando um método que faz
JOIN com `Transacao`), não uma mudança estrutural. YAGNI por ora.

**Nomes de campo alinhados ao vocabulário do pedido:** `nome_arquivo` → `nome_original`,
`tipo_mime` → `mime_type`, `criado_em` → `data_upload` (mesmo dado, nome que corresponde
exatamente à lista de metadados pedida). `caminho_arquivo`/`tamanho_bytes` mantidos como já
estavam — já correspondiam ao pedido.

## Reaproveitamento obrigatório de `TransacaoService`: como a posse transitiva é validada

O pedido é explícito: "Toda validação de autorização deve reutilizar TransacaoService/
Repository quando apropriado, nunca duplicar regras." `TransacaoService.obter(transacao_id,
usuario_id)` já implementa exatamente a checagem necessária — 404 uniforme tanto para
"transação não existe" quanto para "transação é de outro usuário" (mesmo padrão anti-BOLA já
usado em toda validação de posse cruzada deste projeto). `AnexoService` injeta
`TransacaoService` (não `TransacaoRepository` diretamente) e chama `.obter()` em todo ponto
que precisa confirmar posse — nunca reimplementa a checagem "transacao.usuario_id ==
usuario_id" por conta própria.

Isso é um terceiro padrão de composição com `TransacaoService`, distinto dos dois já
existentes no projeto: `Parcelamento`/`ContaRecorrente`/`Financiamento`/`Empréstimo` chamam
`TransacaoService` para ESCREVER (gerar parcelas/ocorrências); `MetaService` não chama
`TransacaoService` — só lê `Transacao` via `MetaRepository` (agregação SQL própria).
`AnexoService` não escreve NEM agrega `Transacao` — chama `TransacaoService.obter()` apenas
para validação de posse (leitura pontual, delegada, nunca duplicada).

## `ondelete="CASCADE"` em `transacao_id`: consequência direta de Transação não ter soft delete

`Transacao` é removida de verdade (`DELETE /transacoes/{id}` faz hard delete — ver
docs/analise-arquitetural-transacao.md), diferente de toda outra entidade deste domínio, que
usa soft delete. Se um `Anexo` aponta para uma `Transacao` que é fisicamente removida, o
`Anexo` órfão não faz sentido (não há como reanexar a um lançamento que não existe mais).
`transacao_id` usa `ForeignKey(..., ondelete="CASCADE")` e o lado `Transacao.anexos` usa
`cascade="all, delete-orphan"` — mesmo padrão já usado em `Usuario` para os relacionamentos
que ele possui exclusivamente, aplicado aqui porque `Transacao` "possui" seus anexos da mesma
forma exclusiva (um Anexo nunca faz sentido sem a Transação que ele documenta).

## Decisão de escopo pendente de confirmação: PATCH está incluído?

O pedido diz "CRUD completo" (o que sugere update) e lista soft delete explicitamente para
DELETE, mas as regras de domínio não mencionam PATCH em nenhum momento — diferente de `Meta`,
que teve "PATCH permitido" como regra explícita. O docstring original do model (herdado do
desenho especulativo) já registrava a hipótese de que "anexo é essencialmente imutável (não
faz sentido editar um comprovante já enviado)", e as duas entidades mais parecidas em
natureza — `Financiamento`/`Empréstimo`, ambas com registros que não fazem sentido editar
livremente após criados — não têm `PATCH` por decisão explícita anterior.

**Decisão confirmada pelo usuário (via pergunta direta antes do código): SEM PATCH.** Anexo é
create + read + soft-delete apenas — mesma decisão de `Financiamento`/`Empréstimo`, mesmo
racional do docstring original do model. Não existe `AnexoUpdate`; nenhuma rota
`PATCH /anexos/{id}`.

## Escopo explicitamente fora (confirmado, sem ambiguidade)

Upload para cloud, OCR, thumbnails, compressão, antivírus, versionamento, compartilhamento,
criptografia de arquivo, download autenticado especial. `AnexoService`/`AnexoRepository`
nunca tocam o conteúdo do arquivo em si — `caminho_arquivo` é só uma referência de string;
onde/como o arquivo é fisicamente armazenado é responsabilidade de uma camada de
infraestrutura que não faz parte desta etapa (mesmo racional já registrado no docstring
original do model).

## Resumo do que muda em cada camada

- **Model**: `Anexo` perde `entidade_tipo`/`entidade_id`/`usuario_id`, ganha `transacao_id`
  (FK obrigatória, `ondelete="CASCADE"`) e `ativo`. Campos renomeados para o vocabulário do
  pedido. `Usuario.anexos` removido. `Transacao.anexos` adicionado
  (`cascade="all, delete-orphan"`).
- **Migration**: `ALTER TABLE anexos` via `batch_alter_table` (SQLite) — remove 3 colunas,
  adiciona 2, mais o `ForeignKey`/índice de `transacao_id`.
- **Repository**: `AnexoRepository` — CRUD genérico + `listar_por_transacao`.
- **Service**: `AnexoService` injeta `TransacaoService` (não grava `Transacao`, só valida
  posse via `.obter()`).
- **Router**: `app/api/routes/anexo.py`, sem lógica de negócio.
- **Schemas**: `AnexoCreate` (inclui `transacao_id`), `AnexoRead`. Sem `AnexoUpdate` — decisão
  confirmada pelo usuário: sem PATCH.
