# Decisão arquitetural — performance do cálculo de saldo

## Contexto

`Conta.saldo_atual` é sempre calculado (`ContaService._com_saldo`), nunca armazenado —
via duas queries de agregação SQL (`SUM`) em `ContaRepository`: uma soma líquida de
`Transacao` PAGA, outra de `Transferencia`. Pergunta: isso aguenta uma conta com dezenas
de milhares de transações, ou vai exigir view materializada / saldo em cache?

## Decisão

Manter agregação SQL em tempo real como estratégia **padrão e definitiva** para
`Conta.saldo_atual` — não é um placeholder "por enquanto", é a escolha certa para este
domínio, pelos motivos abaixo. Nenhuma otimização (índice, cache, materialização) é
implementada nesta etapa; este documento registra só a decisão e o gatilho de revisão.

### Por que `SUM` real-time é a estratégia certa aqui, não um atalho

Um `SELECT SUM(valor) WHERE conta_id = ? AND status = 'PAGO'` com um índice em
`conta_id` é um *index range scan*: o banco vai direto às linhas daquela conta e soma só
elas — o custo escala com o número de transações **daquela conta**, não com o tamanho da
tabela inteira. Nessa condição, "dezenas de milhares" de transações somadas giram em
poucos milissegundos tanto em SQLite quanto em Postgres — não é o volume que doeria
primeiro.

Isso é consistente com o princípio já adotado no resto do domínio (`Conta.saldo`,
`Meta.progresso`): nunca armazenar um valor barato de recalcular. A única exceção
documentada é `Financiamento/Emprestimo.saldo_devedor`, guardado porque PRICE/SAC **não**
é uma soma simples (precisa de estado). `SUM` de transações é o caso oposto: barato,
determinístico, sempre correto — guardar e ter que invalidar em toda escrita trocaria uma
leitura de poucos ms por complexidade de consistência (o clássico problema de cache
desatualizado, que numa tela de saldo bancário é particularmente ruim: o usuário não pode
ver um número que já não é verdade).

### O gargalo real hoje não é volume, é a ausência de índice

`Transacao.conta_id` (e `cartao_id`) **não têm `index=True`** no model atual — só
`usuario_id` e `data` são indexados. Sem índice em `conta_id`, a mesma query vira um
*full table scan*: o banco lê TODAS as transações da tabela (de todos os usuários, já que
o sistema é multi-tenant) para achar as de uma conta. Esse é o fator que realmente
degrada com o tempo, e degrada bem antes de "dezenas de milhares" de linhas na conta
específica — degrada com o tamanho da tabela inteira.

**Isso não é a otimização que este documento está adiando** — é higiene de schema comum
que deveria nascer junto com a migration de `Transacao`, quando esse CRUD for
implementado (`index=True` em `conta_id` e `cartao_id`, e possivelmente um índice
composto `(conta_id, status)` já que toda leitura de saldo filtra por status = PAGO). Vale
resolver ali, no momento natural, e não como uma "otimização futura" separada.

### O que NÃO fazer agora (e por quê)

- **View materializada**: exigiria refresh (por trigger ou periódico) para não mentir o
  saldo ao usuário — trade-off ruim para uma tela de saldo bancário, que deve ser exata,
  não "eventualmente consistente". SQLite também não suporta materialized view
  nativamente (existiria só se o projeto um dia migrar para Postgres).
- **Cache do saldo com TTL**: mesma objeção — abre uma janela onde o número exibido pode
  estar errado. Só faria sentido se o *volume de leitura* (não de dados) virasse o
  gargalo, o que não é o caso aqui.
- **Coluna de saldo armazenada + invalidação em toda escrita**: reintroduz exatamente o
  padrão que o domínio evita (ver `Conta.saldo`/`Meta.progresso`), trocando uma leitura
  barata por um novo ponto de inconsistência possível (esquecer de invalidar em algum
  caminho de escrita).

## Gatilho de revisão

Não é um número fixo de linhas — é uma condição observável. Revisitar esta decisão
quando (e só quando) uma destas acontecer de verdade, medida, não estimada:

1. **Índice em `conta_id` já existe e mesmo assim** uma consulta de saldo de uma única
   conta passa de ~50ms em dado real (não sintético) — sinal de que o padrão de acesso
   mudou de um jeito que `SUM` indexado não cobre mais.
2. **Frequência de leitura**, não volume de dado, vira o custo dominante — ex: uma tela
   tipo "Central Financeira" (já especificada em `docs/central-financeira-especificacao.md`)
   recalculando saldo de todas as contas a cada poucos segundos. Nesse caso a resposta
   provável é um *checkpoint* (snapshot periódico do saldo + soma só das transações
   posteriores ao checkpoint), não um cache solto — mantém exatidão e limita o custo pelo
   tamanho da janela, não pelo histórico total.
3. **O projeto deixa de ser uso pessoal** (múltiplos usuários simultâneos reais) — muda o
   perfil de carga por completo e merece nova análise, não só um ajuste incremental.

Ordem de resposta, do mais barato ao mais caro, se algum gatilho acima disparar: (1)
índice em `conta_id`/`cartao_id` (se ainda não existir), (2) combinar as duas queries de
soma em uma só, (3) estratégia de checkpoint/snapshot, (4) só then considerar cache ou
coluna armazenada — e mesmo assim com invalidação síncrona na mesma transação de escrita,
nunca um TTL solto.

## Nota lateral (não é sobre performance, mas relevante em volume)

SQLite não tem tipo `DECIMAL` nativo — `Numeric(12,2)` do SQLAlchemy é convertido pelo
driver. Ao somar dezenas de milhares de linhas, vale confirmar que não há *drift* de
arredondamento por armazenamento em ponto flutuante (mitigável migrando para Postgres,
que tem `NUMERIC` exato, se este projeto um dia sair do SQLite). Não é um problema hoje;
é só algo a verificar se o volume real crescer muito.
