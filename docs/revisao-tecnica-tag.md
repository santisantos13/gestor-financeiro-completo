# Revisão técnica — CRUD de Tag

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada** — nenhum problema de arquitetura,
segurança ou regra de negócio ausente foi encontrado; os pontos abaixo são esclarecimentos
de comportamento intencional, não bugs.

## Resumo

Segue o padrão `Router → Service → Repository` estabelecido em `Conta`/`Categoria`, com uma
única regra de negócio central: nome único por usuário coexistindo com soft delete. 153
testes passam (24 unitários com repository falso, 24 de integração via `TestClient`, mais os
105 pré-existentes de outras camadas).

`Tag` é a entidade mais simples das três CRUDs implementadas até aqui — sem hierarquia
(Categoria), sem valor calculado (Conta) — mas a interação entre `UniqueConstraint` e soft
delete introduz uma sutileza que não existia nas entidades anteriores.

## Decisão de modelagem: reativar em vez de bloquear no nome

`UniqueConstraint(usuario_id, nome)` não sabe distinguir uma tag ativa de uma desativada.
Sem tratamento especial, soft-deletar uma tag chamada "viagem" "queimaria" esse nome
permanentemente para o usuário — ele nunca conseguiria criar outra tag "viagem", porque o
banco rejeitaria por violação de unicidade, mesmo a original estando invisível em todas as
listagens (`apenas_ativas=True` por padrão).

**Correção adotada:** `criar()` busca por nome antes de inserir; se encontrar uma tag
inativa com o mesmo nome, reativa essa linha em vez de tentar inserir uma nova. Alternativas
consideradas e descartadas: índice único parcial (`WHERE ativo = true`) resolveria de forma
mais "pura" a nível de banco, mas SQLite tem suporte limitado a índices parciais e isso
criaria um mecanismo fora do padrão usado no resto do projeto (nenhuma outra tabela usa
índice parcial); simplesmente impedir a duplicata sem reativar deixaria o usuário preso
sem conseguir recriar uma tag que ele mesmo apagou, o que é pior do ponto de vista de UX
do que qualquer custo de manutenção da solução escolhida.

## Três pontos de comportamento esclarecidos nesta revisão

Identificados por autorrevisão (mesmo hábito que pegou o gap de PATCH em Categoria) — não
são bugs, mas comportamentos que exigiam ficar explícitos em comentário e cobertos por
teste, para não virarem surpresa depois.

### 1. Reativação via `criar()` sobrescreve a cor antiga

Se o payload de criação não enviar `cor`, o valor default (`None`) é aplicado à tag
reativada, apagando a cor que ela tinha antes de ser desativada. Isso é intencional:
`TagCreate` não tem o `exclude_unset` que `TagUpdate` usa para saber "o cliente não
mencionou esse campo" — do ponto de vista da API, um `POST` é sempre "aqui está o estado
completo que eu quero", então tratar a reativação como uma criação normal (o que foi
enviado é o estado final) é mais previsível do que magicamente preservar atributos antigos
que o cliente não pediu para preservar. Coberto por
`test_reativar_tag_sem_enviar_cor_substitui_cor_antiga_por_none`.

### 2. Renomear para o nome de uma tag inativa NÃO reativa/mescla — bloqueia com 409

`atualizar()` (rename) e `criar()` (reativação) resolvem a mesma colisão de nome de formas
diferentes, de propósito. `criar()` reativa porque a intenção do usuário é inequívoca ("crie
uma tag chamada X" — se X já existe inativa, restaurá-la é o que ele quer). Já um `PATCH`
que renomeia a tag B para o nome de uma tag A inativa é ambíguo: o usuário quer fundir B com
o histórico de A, ou só está tentando usar um nome que "parecia livre"? Fundir
silenciosamente mudaria a identidade de B (e qualquer vínculo N:N que B já tivesse) sem
confirmação explícita — arriscado demais para ser implícito. Por isso `atualizar()`
simplesmente rejeita com `ConflictError`, mesmo comportamento de "nome já em uso" que teria
para colisão com uma tag ativa. Coberto por
`test_atualizar_renomeando_para_nome_de_tag_inativa_levanta_conflict_error` (unitário) e
`test_atualizar_renomeando_para_nome_de_tag_inativa_retorna_409` (integração).

### 3. Duas rotas para reativar, e ambas são válidas

Além da reativação implícita em `criar()`, `PATCH /tags/{id} {"ativo": true}` também
reativa uma tag diretamente pelo id — caminho direto, sem depender de colisão de nome. Os
dois caminhos coexistem por servirem casos de uso diferentes: reativar por nome (sem saber
ou lembrar o id) vs. reativar por id (ex.: uma tela de "lixeira" que lista tags inativas e
oferece um botão "restaurar"). Nenhum conflito entre eles — `atualizar()` não tem a lógica
de reativação por nome, só `criar()` tem. Coberto por
`test_atualizar_ativo_true_reativa_tag_diretamente` (unitário e integração).

## Comparação deliberada com Categoria: sem bloqueio de "em uso"

Categoria bloqueia exclusão quando há subcategoria ativa (regra de hierarquia). Tag não tem
hierarquia, então essa classe de regra não se aplica — mas vale registrar explicitamente
por que Tag também **não** bloqueia exclusão por estar "em uso" em alguma transação: por
design, o vínculo N:N entre `Tag` e `Transacao` (a ser criado na migration de `Transacao`)
não é afetado por soft delete — a tag some das listas de novas seleções, mas transações que
já a referenciam mantêm o vínculo intacto. Diferente de Categoria (onde `TODO` já registra
a checagem futura de "em uso" antes de excluir), aqui não há necessidade equivalente: uma
tag desativada em uma transação antiga não deixa nenhum dado órfão ou inconsistente, então
não há razão de negócio para impedir a exclusão. Se essa decisão precisar mudar quando
`Transacao` existir de fato, é um ajuste pontual em `desativar()`, não uma falha de design
atual.

## Observações registradas, não implementadas

- **Sem índice composto em `(usuario_id, nome)` além do que a `UniqueConstraint` já cria
  implicitamente.** SQLite cria um índice automaticamente para toda `UniqueConstraint`, então
  `buscar_por_nome()` já é uma busca indexada — nenhuma ação necessária.
- **Relacionamento N:N com `Transacao` ainda não existe** (tabela de associação
  `transacao_tags` fica para a migration de `Transacao`) — o modelo `Tag` já está pronto
  para receber essa `relationship`, mas nenhuma tabela de junção foi criada agora, por não
  haver `Transacao` ainda para associar.

## Conclusão

Sem problema de arquitetura, segurança, duplicação ou regra de negócio ausente identificado
nesta revisão. Os três pontos de comportamento acima já eram o design pretendido desde a
implementação, apenas tornados explícitos (comentário + teste) durante a autorrevisão. O
CRUD de Tag está encerrado e segue o mesmo padrão de qualidade dos CRUDs de Conta e
Categoria.
