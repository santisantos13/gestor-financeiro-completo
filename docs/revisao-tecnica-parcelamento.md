# Revisão técnica — CRUD de Parcelamento

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada, com um problema real encontrado e
corrigido durante a própria revisão** (ver seção dedicada) — fora esse ponto, a
implementação segue a arquitetura validada em `docs/analise-arquitetural-parcelamento.md`,
incluindo os sete ajustes de modelagem aprovados antes da implementação.

## Resumo

Segue `Router → Service → Repository`. `ParcelamentoService` nunca constrói uma `Transacao`
nem fala com `TransacaoRepository` para escrever — cada parcela nasce e morre através de
`TransacaoService.criar()`/`excluir()`, o mesmo padrão de composição Service→Service já
usado por `TransacaoService`→`FaturaService`. A geração de parcelas é eager (todas as N de
uma vez, na criação), incluindo as Faturas futuras correspondentes, uma exceção deliberada e
já justificada ao princípio "fatura futura nunca é gerada com antecedência" (um Parcelamento
é um compromisso determinístico, diferente de um ciclo mensal que ninguém se comprometeu a
preencher). 394 testes passam no total (27 unitários novos de `ParcelamentoService`, 6
unitários novos de `TransacaoService` — posse/faixa/duplicidade de `parcelamento_id` — 17 de
integração novos de Parcelamento, 2 de integração novos de Transação para o achado desta
revisão, mais os pré-existentes).

## Achado real: duplicidade de `numero_parcela` derrubava um 500 cru

Este é o problema que a revisão foi pedida explicitamente para caçar, e que os testes
originais não cobriam. `ParcelamentoService` sempre gera `numero_parcela` únicos por
construção (1..N, sem lacunas nem repetição) — mas nada impedia um `POST /transacoes`
manual, fora do fluxo de `ParcelamentoService`, de reivindicar um `numero_parcela` já usado
por outra transação do mesmo parcelamento. `TransacaoService._validar_parcelamento()`
validava posse e faixa, mas não duplicidade — a única barreira contra isso era o
`UniqueConstraint(parcelamento_id, numero_parcela)` do banco, e `main.py` não tem nenhum
exception handler genérico para `IntegrityError`. Na prática: `POST /transacoes` com um
`numero_parcela` colidente derrubava um `500 Internal Server Error` cru, sem tradução para
uma resposta de domínio.

Confirmado empiricamente antes de corrigir (criando um parcelamento e tentando reivindicar
manualmente a parcela 1 de novo): resposta `500`, corpo genérico do Starlette, nada
informativo para quem chama a API. Corrigido em `TransacaoService._validar_parcelamento()`:
antes de criar/atualizar, busca as parcelas existentes do parcelamento
(`transacao_repo.listar_do_usuario(..., parcelamento_id=...)`) e levanta `ConflictError`
(409) se outra transação já usa aquele `numero_parcela` — mesmo raciocínio já usado em
`FaturaService.criar()` para o par cartão+mês. `atualizar()` passa
`transacao_id_excluir=transacao.id` para a própria transação não colidir consigo mesma
(permite, por exemplo, um `PATCH` que só muda a descrição de uma parcela sem mexer no
número). Testado em três camadas: unitário
(`test_criar_com_numero_parcela_ja_usada_no_mesmo_parcelamento_levanta_conflict_error`,
`test_atualizar_numero_parcela_para_uma_ja_usada_por_outra_transacao_levanta_conflict_error`,
`test_atualizar_numero_parcela_mantendo_o_mesmo_valor_nao_conflita_consigo_mesma`) e
integração (`test_criar_transacao_com_numero_parcela_ja_usada_no_mesmo_parcelamento_retorna_409`,
`test_atualizar_numero_parcela_para_uma_ja_usada_por_outra_transacao_retorna_409`).

Achado colateral, também corrigido: o router `GET /transacoes` nunca expunha
`parcelamento_id` como query param, mesmo `TransacaoService.listar()` já aceitando o filtro
— a listagem de parcelas de um parcelamento (`GET /transacoes?parcelamento_id=X`), usada
tanto pelos testes de integração de Parcelamento quanto por qualquer cliente real da API,
simplesmente não funcionava via HTTP antes desta correção.

## Migração e modelo: sem drift, ciclo completo validado

`alembic upgrade head` → `downgrade -1` → `upgrade head` executado limpo num banco
descartável. `alembic revision --autogenerate` rodado contra o schema pós-migração não
detectou nenhuma diferença (arquivo gerado vazio, `pass`/`pass`) — modelo e migração estão
exatamente em sincronia, nenhuma mudança em `Parcelamento`/`Transacao` ficou de fora da
migração `fe8c7c77dbbf`. `IntegrityError` disparado manualmente confirma os dois novos
constraints em runtime: `ck_parcelamento_cartao_xor_conta` (cartão e conta simultâneos, ou
nenhum dos dois, ambos rejeitados) e `uq_transacao_parcelamento_numero_parcela` (duplicata
rejeitada mesmo contornando `TransacaoService`, hipoteticamente, via acesso direto ao
banco) — o `ConflictError` da seção anterior é a camada de aplicação; o `UniqueConstraint`
continua sendo a rede de segurança final, como pretendido desde a análise arquitetural.

## Atomicidade da geração eager: rollback cobre tudo, inclusive o cabeçalho

`ParcelamentoService.criar()` faz `parcelamento_repo.create()` (flush, não commit) e só
depois gera as N parcelas via `TransacaoService.criar()`. Se qualquer parcela falhar no meio
(categoria incompatível, cartão inativo etc.), a exceção sobe até `get_db()`, que faz
`db.rollback()` antes de propagar — o `Parcelamento` já flushado também é desfeito, nunca
fica um cabeçalho órfão sem parcelas. Confirmado por leitura de `app/db/session.py` (não
apenas assumido): a mesma sessão é a unidade de trabalho do request inteiro, commit só no
fim, sem tratamento de erro parcial necessário em `ParcelamentoService`.

## Cancelamento: reaproveita `TransacaoService.excluir()` sem reimplementar a trava

`cancelar()` não decide sozinho quais parcelas estão "travadas" — chama
`TransacaoService.excluir()` para cada uma e ignora silenciosamente o `BusinessRuleError`
das que têm fatura fechada. Isso significa herdar, sem introduzir, uma limitação que já
existe em `TransacaoService`: uma fatura `ABERTA` mas já paga (pagamento parcial ou total
registrado, porém ainda não fechada explicitamente via `POST /faturas/{id}/fechar`) não
bloqueia a exclusão de uma transação de compra vinculada a ela. Não é um problema novo
introduzido por Parcelamento — é o mesmo comportamento que qualquer `DELETE /transacoes/{id}`
manual já tinha antes desta etapa, e corrigi-lo aqui duplicaria a lógica de trava em vez de
reaproveitá-la (contrariando a instrução explícita de "reaproveite TransacaoService").
Registrado aqui como limitação conhecida, não como pendência desta entrega.

## `_dividir_valor`: resto sempre absorvido pela última parcela, nos dois sentidos

Testado com resto positivo (`R$ 100,00 / 3 = 33,33 + 33,33 + 33,34`) e resto negativo
(`R$ 10,01 / 3`, onde a primeira aproximação por parcela ficaria alta demais e a última
parcela precisa ser a MENOR das três, não a maior) — os dois casos batem exatamente com
`valor_total`, sem perder nem sobrar centavo por arredondamento.

## Conclusão

Um problema real de arquitetura foi encontrado (falta de tradução de `IntegrityError` para
uma resposta HTTP de domínio em `TransacaoService`, mais um gap de roteamento em
`GET /transacoes`) e corrigido antes de fechar esta etapa, com teste de regressão nas três
camadas. Fora esse ponto, a composição `ParcelamentoService` → `TransacaoService` está
implementada exatamente como planejado: nenhuma duplicação de regra de posse/validação de
Conta, Cartão, Categoria ou resolução de Fatura; migração e modelo em sincronia perfeita;
atomicidade de request confirmada por leitura direta de `app/db/session.py`, não apenas
assumida. O CRUD de Parcelamento está encerrado (dentro do escopo combinado: sem exclusão
física, sem `PATCH` genérico, cancelamento sempre parcial) e segue o mesmo padrão de
qualidade dos CRUDs anteriores.
