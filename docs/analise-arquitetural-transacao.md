# Análise arquitetural — Transação

Análise de modelagem prévia à implementação do CRUD de `Transacao`, seguindo o mesmo rigor
de `docs/analise-arquitetural-fatura.md`. Diferente das entidades anteriores, `Transacao` é
o registro central do domínio: praticamente todo cálculo financeiro do sistema (`saldo_atual`,
`limite_disponivel`, `valor_total`/`valor_pago` de Fatura) já depende dela, mesmo sem seu
próprio CRUD existir ainda. **Status: aprovada**, com os três ajustes abaixo incorporados após
a primeira rodada: (1) nenhum Repository de Parcelamento/Financiamento/Empréstimo/Meta/Conta
Recorrente nasce nesta etapa — YAGNI, cada um nasce junto do CRUD da própria entidade; (2) o
novo `CheckConstraint` de `numero_parcela` é mantido; (3) o significado duplo de
`StatusTransacao` é documentado explicitamente, tanto aqui quanto em `app/models/enums.py`.

## Transação ↔ Conta

Já modelado (`conta_id` nullable, `CheckConstraint` XOR com `cartao_id`). Posse: `conta_id`
precisa pertencer ao mesmo usuário da transação — `TransacaoService` recebe `ContaRepository`
só para essa validação cruzada, mesmo padrão de `CartaoService`/`ContaRepository`. Uma conta
`ativo=False` bloqueia **novo** lançamento (`BusinessRuleError`); nunca bloqueia edição de uma
transação antiga cuja conta foi desativada depois — mesmo raciocínio de soft delete já usado
em Categoria/Cartão (desativação não apaga histórico).

`status` (`PENDENTE`/`PAGO`) é, para transação de conta, o campo para o qual foi originalmente
desenhado: livremente editável pelo cliente, sem endpoint de ação dedicado — é exatamente o
que `ContaRepository.somar_transacoes_pagas` já consulta hoje (só soma `PAGO`).

**Transação de conta nunca é travada.** `Conta.saldo_atual` é sempre recalculado ao vivo,
nunca congelado — corrigir `valor`/`data` de um lançamento antigo apenas atualiza a soma, sem
nenhum "documento fechado" a proteger. Isso contrasta diretamente com a próxima seção.

## Transação ↔ Cartão

A relação mais delicada desta análise, com três decisões:

**Resolução de fatura é uma peça que ainda não existe.** Toda a arquitetura de Fatura já foi
desenhada em torno de "resolver, ou criar, a fatura aberta para esta data" (ver
`docs/analise-arquitetural-fatura.md`, seção "Geração automática das próximas faturas"), mas
esse método foi deliberadamente adiado durante o CRUD de Fatura. Implementar transação de
cartão sem essa peça é impossível de fazer corretamente. Decisão: esse método nasce agora,
como extensão pontual de `FaturaService` (`resolver_fatura_aberta(cartao_id, data,
usuario_id)`, find-or-create, reaproveitando `_calcular_datas_ciclo`/`buscar_por_cartao_e_mes`
já implementados) — não é a geração em lote/scheduler que foi de fato adiada, é a resolução
lazy por transação que sempre foi parte do desenho. `TransacaoService` apenas chama esse
método; nunca reimplementa resolução de ciclo por conta própria, para não duplicar a regra.

**Imutabilidade de fatura fechada.** `docs/analise-arquitetural-fatura.md` já prometeu esta
regra; é aqui que ela é cumprida: uma vez que `Transacao.fatura_id` aponta para uma fatura
cujo status persistido não é mais `ABERTA`, os campos `valor`, `data`, `cartao_id` e
`parcelamento_id` dessa transação não podem mais ser alterados nem a transação pode ser
excluída — `TransacaoService.atualizar()`/`excluir()` consultam `Fatura.status` (leitura, via
`FaturaRepository`) antes de aplicar a mudança. Campos descritivos (`categoria_id`,
`descricao`, `tags`) continuam livres mesmo com a fatura fechada.

**`status` não é autoridade de cobrança para transação de cartão** (ver seção dedicada abaixo)
— `TransacaoService` força `status = PAGO` na criação, ignorando qualquer valor enviado pelo
cliente para uma transação com `cartao_id` preenchido, em vez de expor um campo que parece
controlar algo mas não controla nada.

## Transação ↔ Categoria

Precisa de checagem de visibilidade (sistema OU própria do usuário — reusa a lógica de
`CategoriaService._buscar_visivel`, então `TransacaoService` recebe `CategoriaRepository`).
Categoria inativa: bloqueada para nova atribuição, nunca desfeita retroativamente numa
transação antiga (mesmo comportamento já garantido pelo soft delete de Categoria).

Achado novo: `docs/revisao-tecnica-categoria.md` deixou em aberto, de propósito, a validação
de `Categoria.tipo` vs. o tipo de quem a usa ("decisão deixada em aberto até haver um caso de
uso real"). Este é o caso de uso real — resolvido agora: `TransacaoService` rejeita
(`BusinessRuleError`) se `categoria.tipo not in (AMBOS, transacao.tipo)`. Revalidado sempre
que `tipo` OU `categoria_id` mudarem via `PATCH`.

## Transação ↔ Tag

N:N já modelado (`transacao_tag`). Mesma regra de Categoria: tags atribuídas precisam
pertencer ao usuário e estar ativas no momento da atribuição; uma tag desativada depois
permanece vinculada às transações antigas (comportamento já garantido pelo design de `Tag`,
nada novo aqui). Forma de implementação (não bloqueia a modelagem): um campo `tag_ids:
list[int]` no payload que substitui o conjunto inteiro é mais simples do que sub-endpoints de
adicionar/remover.

## Transação ↔ Fatura

Coberto nas seções de Cartão acima (compra via `fatura_id`, pagamento via `fatura_paga_id`,
já implementado no CRUD de Fatura). Um ponto que só fica confirmado agora que `Transacao` está
sendo implementada de verdade: **estorno** (já desenhado em
`docs/analise-arquitetural-fatura.md`, seção "Resolução de ciclo por data") é só uma
`Transacao` comum tipo `RECEITA` — a resolução por data (`resolver_fatura_aberta`) já cobre
sozinha o caso "estorno cai na fatura seguinte se a original já fechou". Nenhuma lógica nova
além do que já foi projetado.

## Transação ↔ Parcelamento

`Parcelamento` não tem Service/CRUD ainda — só o model. Duas responsabilidades bem separadas:
(a) **vincular** uma transação a um parcelamento já existente (`parcelamento_id` +
`numero_parcela` no payload) — isso `TransacaoService` faz agora, mas **sem** validar posse
via Repository dedicado (ver ajuste de escopo abaixo); (b) **gerar** as N parcelas
automaticamente ao criar um `Parcelamento` — responsabilidade do futuro `ParcelamentoService`,
fora de escopo aqui, mesma decisão já tomada para a geração automática de Fatura.
`TransacaoService` não valida consistência agregada (ex: "soma das parcelas bate com
`valor_total`") — isso pertence a `ParcelamentoService` quando existir, para não duplicar essa
regra em dois lugares.

## Transação ↔ Financiamento

Mesma estrutura de Parcelamento (vincular sim, gerar não), com um cuidado a mais:
`ContratoCreditoMixin.saldo_devedor` é armazenado e, segundo o próprio docstring do mixin,
"atualizado pelo Service a cada parcela paga" — um `FinanciamentoService`/`EmprestimoService`
que ainda não existe. Ponto que precisa ficar explícito para não ser antecipado por engano:
**`TransacaoService` nunca toca `saldo_devedor`**, mesmo criando uma transação com
`financiamento_id` preenchido. Vínculo permitido (`financiamento_id`, sem repository
dedicado), efeito colateral sobre o saldo do contrato não — antecipar essa regra de
amortização (PRICE/SAC) seria implementar funcionalidade fora do escopo pedido.

## Transação ↔ Transferência

Sem relação — e está correto que seja assim. `Transferencia` fica deliberadamente fora de
`Transacao` (não é receita nem despesa; já documentado no próprio model). O único ponto de
contato indireto é que as duas alimentam `Conta.saldo_atual` separadamente (já implementado,
inalterado por este CRUD). Nenhuma ação necessária.

## Transação ↔ Meta

`meta_id` nullable já modelado — um aporte é só uma `Transacao` marcada. Vínculo aceito sem
repository dedicado (mesmo ajuste de escopo das duas seções anteriores). Deliberadamente
**sem** restringir `meta_id` a transações `RECEITA`, nem impor teto de `valor_alvo` —
aportar além do alvo, ou "retirar" de uma meta via uma `DESPESA` marcada com `meta_id`, são
usos legítimos não pedidos como regra e não devem ser bloqueados por antecipação.

## Transação ↔ Conta Recorrente

Mesmo padrão de Parcelamento/Financiamento/Meta: `origem_recorrente_id` aceito como vínculo
manual (sem repository dedicado), mas a geração de transações a partir de um template ativo é
uma rotina explicitamente futura (o próprio model já documenta isso) — fora de escopo aqui.

## Transação ↔ Anexo

Nenhuma mudança necessária em `Transacao`. O vínculo é inteiramente polimórfico do lado de
`Anexo` (`entidade_tipo=TRANSACAO`, `entidade_id=<id>`), sem FK real — o design existe
justamente para não acoplar `Transacao` a `Anexo`. `TransacaoService` não precisa saber que
`Anexo` existe.

## `StatusTransacao`: dois significados, nunca confundidos

Ajuste explicitamente pedido: este ponto precisa ficar registrado sem ambiguidade, tanto aqui
quanto em comentário próximo ao código quando implementado (`app/models/enums.py` e
`TransacaoService`).

- **Transação de conta**: `status` é autoritativo — `PENDENTE` (ainda não aconteceu de
  verdade) vs. `PAGO` (já moveu dinheiro), livremente editável pelo cliente, consumido
  diretamente por `ContaRepository.somar_transacoes_pagas`.
- **Transação de cartão**: `status` **não é autoridade sobre pagamento da dívida** — essa
  autoridade é **sempre a Fatura** (`Fatura.status`/`valor_pago`, derivados a partir de
  `Transacao.fatura_paga_id`, conforme já documentado em
  `docs/analise-arquitetural-fatura.md`). Uma compra no cartão "aconteceu" no ato da compra,
  independente de quando a fatura correspondente é paga — por isso `TransacaoService` força
  `status = PAGO` para toda transação com `cartao_id` preenchido, ignorando o que o cliente
  enviar nesse campo. `CartaoRepository.somar_gastos_nao_pagos` já ignora `status` de
  propósito por este exato motivo (ver seu docstring) — este ajuste apenas formaliza, para
  `Transacao`, uma decisão que o Cartão já tomava implicitamente.

## Forma do CRUD: sem soft delete, `PATCH` genérico com uma trava condicional

**Sem soft delete.** Diferente de Conta/Categoria/Tag/Cartão, `Transacao` é lançamento de
livro-razão, não cadastro — uma transação errada deve ser removida de verdade, não
"desativada" (nenhuma das agregações existentes hoje filtra por um campo `ativo`, e
adicionar isso agora exigiria retrofitar três Repositories já testados e shippados). Exclusão
é real, com uma única restrição: bloqueada se vinculada a fatura fechada (regra de
imutabilidade acima). Excluir um *pagamento* de fatura (`fatura_paga_id` preenchido) é sempre
permitido — `valor_pago` é recalculado ao vivo, não há snapshot de pagamento a corromper.

**`PATCH` genérico, ao contrário de Fatura.** A maior parte dos campos de `Transacao` é
livremente editável — diferente de Fatura, que não tinha campo "livre" de verdade. A única
trava condicional é a imutabilidade de fatura fechada. `conta_id`/`cartao_id` são **imutáveis
após a criação** (mesmo tratamento de identidade estrutural de `Fatura.cartao_id`) — trocar de
conta para cartão no meio do caminho reabriria toda a resolução de fatura; mais simples exigir
excluir e recriar.

## Mudanças de modelagem necessárias antes da implementação

1. Novo `CheckConstraint` em `Transacao`: `numero_parcela` só pode ser não-nulo quando
   `parcelamento_id`, `financiamento_id` ou `emprestimo_id` estiver preenchido — hoje nada
   garante essa consistência (achado desta análise, mantido após revisão).
2. `FaturaService` ganha `resolver_fatura_aberta(cartao_id, data, usuario_id)` — extensão
   pontual, reaproveitando código já existente, não a geração em lote que foi adiada.
3. `StatusTransacao` ganha docstring explícita documentando o significado duplo (autoritativo
   para conta, não-autoritativo para cartão) em `app/models/enums.py`.
4. **Nenhum Repository novo de Parcelamento/Financiamento/Empréstimo/Meta/Conta Recorrente
   nesta etapa** (ajuste aprovado, YAGNI) — vínculos manuais opcionais (`parcelamento_id`,
   `financiamento_id`, `emprestimo_id`, `meta_id`, `origem_recorrente_id`) são aceitos no
   payload e persistidos, mas **sem validação de posse cruzada** até que o CRUD da entidade
   correspondente exista e traga seu próprio Repository. Documentado explicitamente no
   docstring de `TransacaoService` para não ser lido como omissão.
5. Nenhuma mudança em `Conta`, `Cartão`, `Categoria`, `Tag`, `Transferência`, `Anexo`.

## Conclusão

Arquitetura validada, com os três ajustes desta rodada incorporados. A peça que faltava para
tornar a implementação possível — `resolver_fatura_aberta` em `FaturaService` — foi
identificada e escopada como extensão mínima, não retrabalho. Pronta para servir de base à
implementação do CRUD de `Transacao`.
