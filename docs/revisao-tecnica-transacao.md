# Revisão técnica — CRUD de Transação

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada** — implementação segue exatamente a
arquitetura validada em `docs/analise-arquitetural-transacao.md` (incluindo os três ajustes
aprovados antes da implementação: YAGNI nos Repositories de contrato, manutenção do
`CheckConstraint` de `numero_parcela`, documentação explícita do significado duplo de
`StatusTransacao`); nenhum desvio não documentado foi identificado nesta revisão.

## Resumo

Segue `Router → Service → Repository`, reaproveitando todos os padrões já validados
(posse via anti-enumeração 404, soft-delete-vs-unicidade quando aplicável — aqui
deliberadamente ausente, ver seção própria) e introduzindo duas peças novas: a resolução
lazy de fatura (`FaturaService.resolver_fatura_aberta`, extensão do Service de Fatura, não
de Transação) e o `TransacaoService`, o Service com mais dependências injetadas do projeto
até agora — reflexo real do fan-out da entidade, não acidente de design. 339 testes passam
no total (49 unitários novos de `TransacaoService`, 6 unitários novos de
`FaturaService.resolver_fatura_aberta`, 31 de integração novos, mais os 253 pré-existentes).

## `resolver_fatura_aberta`: a peça que faltava, onde ela deveria estar

A arquitetura de Fatura sempre previu essa resolução lazy (find-or-create do ciclo aberto
que cobre uma data), mas adiou a implementação por falta de um chamador real. Implementada
agora em `FaturaService`, não em `TransacaoService` — reaproveita
`_calcular_datas_ciclo`/`buscar_por_cartao_e_mes` já existentes, e mantém a regra "quem
sabe calcular ciclo de Fatura" num único lugar, evitando a duplicação que a análise
arquitetural pediu explicitamente para evitar. `_mes_referencia_do_ciclo()` é o único
método novo: dado `cartao.dia_fechamento` e uma data, decide se ela cai no ciclo do mês
corrente (data ≤ fechamento) ou no seguinte (data > fechamento), usando o mesmo
`_dia_valido`/`_proximo_mes` já testados. Se o ciclo resolvido já existir mas não estiver
mais `ABERTA` (fechado manualmente antes da nova transação chegar), rejeita
explicitamente em vez de redirecionar para outro ciclo silenciosamente — mesmo raciocínio
de "nunca mascarar um provável erro de data" já usado na análise de estornos.

## Validação estrutural: Schema faz formato, Service faz estrutura

Decisão deliberada, registrada no próprio docstring de `app/schemas/transacao.py`: conta
XOR cartão, no máximo um contrato, e `numero_parcela` condizente com o contrato **não**
são validados em `field_validator`/`model_validator` do Pydantic — moram inteiramente em
`TransacaoService._validar_estrutura()`. Motivo: a mesma regra precisa valer tanto na
criação (payload completo, `TransacaoCreate`) quanto no `PATCH` (payload parcial,
`TransacaoUpdate` com `exclude_unset`), e só o Service consegue montar o estado FINAL
mesclado nos dois casos — duplicar a regra num `model_validator` do `Create` teria
resolvido só metade do problema, e duplicá-la também no Service para o `Update` violaria a
"evitar duplicação de regras" que a própria análise arquitetural pediu. Um único método
estático, chamado nos dois fluxos, com as mesmas três checagens que existem como
`CheckConstraint` no banco — o Service existe para devolver um `BusinessRuleError` (422)
legível antes que o banco precisasse rejeitar com um `IntegrityError` cru.

## `StatusTransacao`: documentado em três lugares, nunca dois dizendo coisas diferentes

O ajuste pedido explicitamente antes da implementação. O significado duplo (autoritativo
para conta, não-autoritativo para cartão — a Fatura manda) está documentado: (1) na
análise arquitetural, seção dedicada; (2) no docstring do próprio enum
`StatusTransacao` em `app/models/enums.py`, com a mesma explicação; (3) no docstring de
`TransacaoService`, no ponto exato onde `status = StatusTransacao.PAGO` é forçado em
`criar()` e onde `alteracoes.pop("status", None)` descarta silenciosamente qualquer valor
enviado pelo cliente em `atualizar()` para uma transação de cartão. Testado nos dois
sentidos: `test_criar_transacao_de_cartao_forca_status_pago_ignorando_payload` e
`test_atualizar_status_em_transacao_de_cartao_e_ignorado` (unitários), replicados como
`test_criar_transacao_ignora_status_enviado_para_cartao` e
`test_atualizar_status_em_transacao_de_cartao_e_ignorado` (integração).

## Sem soft delete: primeira entidade "de verdade" sem `ativo`

Diferente de Conta/Categoria/Tag/Cartão, `Transacao` não ganhou coluna `ativo`. Justificativa
já registrada na análise arquitetural, confirmada na implementação: nenhuma das agregações
existentes (`ContaRepository.somar_transacoes_pagas`, `CartaoRepository.somar_gastos_nao_pagos`,
`FaturaRepository.somar_transacoes`/`somar_pagamentos`) filtra por um campo `ativo` — introduzir
soft delete agora exigiria retrofitar três Repositories já shippados e testados, só para um
tipo de recurso (lançamento de livro-razão) que semanticamente deveria ser removido de
verdade quando incorreto, não escondido. Exclusão é real (`transacao_repo.delete`), com uma
única restrição: uma transação de COMPRA (`fatura_id` preenchido) vinculada a uma fatura
não-`ABERTA` não pode ser excluída — mesma trava de imutabilidade da próxima seção, aplicada
ao caso extremo. Transação de PAGAMENTO (`fatura_paga_id`) nunca é travada: `valor_pago` é
sempre recalculado ao vivo, não existe snapshot de pagamento a proteger.

## Imutabilidade de fatura fechada: cumprida, não apenas prometida

`docs/analise-arquitetural-fatura.md` prometeu esta regra antes de `TransacaoService`
existir; `_impedir_escrita_em_fatura_fechada()` a cumpre agora. Só dispara quando
`_CAMPOS_TRAVADOS_EM_FATURA_FECHADA` (`valor`, `data`, `parcelamento_id`) aparece nas
alterações de um `PATCH`, ou incondicionalmente num `DELETE` — nos dois casos, só se a
transação tiver `fatura_id` preenchido (compra), nunca por `fatura_paga_id` (pagamento).
`cartao_id` não entra na checagem porque já é estruturalmente imutável — nem existe em
`TransacaoUpdate`, junto com `conta_id` (trocar de conta para cartão, ou vice-versa,
reabriria toda a resolução de fatura; mais simples excluir e recriar, mesma decisão já
tomada para `Fatura.cartao_id`). Campos descritivos (`categoria_id`, `descricao`, `tags`)
continuam editáveis mesmo com a fatura fechada — testado explicitamente
(`test_atualizar_descricao_em_transacao_de_cartao_com_fatura_fechada_e_permitido`,
unitário e de integração).

## Categoria: a validação de tipo que ficou pendente até agora

`docs/revisao-tecnica-categoria.md` deixou essa validação deliberadamente em aberto ("até
haver um caso de uso real"). `TransacaoService._validar_categoria()` resolve: rejeita
(`BusinessRuleError`) se `categoria.tipo not in (AMBOS, transacao.tipo)`. Revalidado tanto
na criação quanto no `PATCH`, sempre que `categoria_id` OU `tipo` mudar — trocar só o
`tipo` de uma transação que já tinha uma categoria incompatível também é bloqueado
(`test_atualizar_tipo_revalida_categoria_ja_atribuida`), não só o caminho óbvio de trocar
a categoria.

## Vínculos manuais sem Repository dedicado: YAGNI aplicado, não esquecido

`parcelamento_id`, `financiamento_id`, `emprestimo_id`, `meta_id`, `origem_recorrente_id`
são aceitos no payload e persistidos, mas sem nenhuma validação de posse cruzada — decisão
explicitamente pedida antes da implementação. Diferença importante em relação a
"esquecido": está documentada em três lugares (análise arquitetural, docstring de
`TransacaoService`, docstring de `TransacaoCreate`) precisamente para não ser lida como
omissão acidental numa revisão futura. Cada um ganha validação de posse quando o CRUD da
entidade correspondente existir e trouxer seu próprio Repository — o mesmo padrão que já
tirou `TransacaoRepository` de "mínimo, só para dar suporte a Fatura" para "completo,
listagem com filtros" nesta etapa.

## `TransacaoRepository`: de mínimo a completo

O Repository mínimo criado durante o CRUD de Fatura (só o CRUD genérico herdado, "não é o
Repository final de Transação" no próprio docstring) foi substituído pela versão completa:
`listar_do_usuario()` com filtros opcionais (`conta_id`, `cartao_id`, `categoria_id`,
`tipo`, intervalo de datas), ordenado por data decrescente (mesma convenção de
`FaturaRepository.listar_do_cartao`). `FaturaService` continua usando o CRUD genérico
herdado sem nenhuma mudança de contrato — a substituição foi transparente para o código já
existente, confirmado pelos 253 testes pré-existentes continuando a passar sem alteração.

## `TransacaoService`: sete dependências, cada uma estreita

`transacao_repo`, `conta_repo`, `cartao_repo`, `categoria_repo`, `tag_repo`, `fatura_repo`
(leitura direta, para a checagem de imutabilidade) e `fatura_service` (orquestração, para
`resolver_fatura_aberta`). É o Service com mais parâmetros no construtor até agora — número
alto, mas cada dependência continua cumprindo o Interface Segregation Principle: nenhuma
delas é usada para mais de uma responsabilidade (`fatura_repo` nunca cria/atualiza fatura,
só lê `status`; `fatura_service` nunca é usado para leitura direta). O padrão de "Repository
de outra entidade injetado para validação cruzada" já existia (`CartaoService`+
`ContaRepository`, `FaturaService`+`CartaoRepository`); o padrão novo aqui é "Service de
outra entidade injetado para orquestrar uma ação de negócio" (`fatura_service`), reservado
para quando a operação necessária é mais que uma leitura simples — reaproveitar a lógica de
resolução de ciclo em vez de duplicá-la valeu o acoplamento extra.

## Conclusão

Sem problema de arquitetura, segurança, duplicação ou regra de negócio ausente identificado
nesta revisão. As decisões mais delicadas da arquitetura aprovada — resolução lazy de
fatura vivendo em `FaturaService` (não em `TransacaoService`), validação estrutural
centralizada só no Service (não duplicada em Schema), significado duplo de
`StatusTransacao` documentado em três camadas, e ausência deliberada de soft delete — foram
implementadas exatamente como especificado em `docs/analise-arquitetural-transacao.md`, com
cobertura de teste direta para cada uma. O CRUD de Transação está encerrado (dentro do
escopo combinado: sem validação de posse para os cinco vínculos de contrato/meta/recorrência,
sem geração automática de parcelas/recorrências) e segue o mesmo padrão de qualidade dos
CRUDs de Conta, Categoria, Tag, Cartão e Fatura.
