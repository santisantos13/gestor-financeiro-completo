# Revisão técnica — CRUD de Categoria

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada** — o único problema real
encontrado foi corrigido e coberto por teste de regressão antes deste documento ser
escrito.

## Resumo

Segue o padrão `Router → Service → Repository` estabelecido em `Conta`, com a
complexidade adicional que a entidade exige: visibilidade em três níveis (sistema/
própria/de outro usuário), validação de hierarquia (pai válido, sem ciclo, sem
auto-referência) e bloqueio de exclusão com subcategoria ativa. 116 testes passam (21
unitários com repository falso, 21 de integração via `TestClient`, mais os 74
pré-existentes de outras camadas).

## Problema encontrado e corrigido

### PATCH `ativo=false` contornava o bloqueio de subcategoria ativa

`atualizar()` aplicava todo o payload (via `exclude_unset` + `setattr`) sem rodar a
mesma checagem de `desativar()`. Como `CategoriaUpdate` expõe `ativo` (necessário para
permitir reativação via PATCH), `DELETE /categorias/{id}` e
`PATCH /categorias/{id} {"ativo": false}` produzem exatamente o mesmo efeito no banco —
mas só o primeiro caminho verificava subcategoria ativa. Um cliente conseguiria desativar
uma categoria com filhos ativos só trocando de verbo HTTP, violando diretamente a regra
de negócio pedida ("não permitir excluir categorias que ainda possuam subcategorias
ativas").

**Correção:** a checagem foi extraída para `_impedir_desativacao_com_subcategoria_ativa()`
e passou a ser chamada nos dois caminhos — em `atualizar()`, só quando a alteração de
fato desliga `ativo` (`alteracoes.get("ativo") is False and categoria.ativo is True`;
reenviar `ativo=true`, ou `ativo=false` numa categoria já inativa, não dispara a
checagem, evitando um efeito colateral desnecessário). Coberto por
`test_atualizar_ativo_false_com_subcategoria_ativa_levanta_business_rule_error` (unitário)
e `test_patch_ativo_false_nao_contorna_bloqueio_de_subcategoria_ativa` (integração via
HTTP real).

Esse tipo de gap — uma regra de negócio implementada só num dos caminhos que produzem o
mesmo efeito — é exatamente o que a revisão técnica pós-implementação existe para pegar;
vale manter o hábito de perguntar "que outro caminho leva ao mesmo estado final?" para
cada regra nova.

## Decisões de modelagem tomadas nesta etapa

**Três níveis de visibilidade, não dois.** Diferente de `Conta` (onde "não existe" e "é
de outro usuário" sempre viram 404), aqui existe um terceiro caso: categoria do sistema.
Ela é publicamente visível (aparece em toda listagem, `GET` por id sempre funciona para
qualquer usuário autenticado), mas não é editável por ninguém. Esconder essa
inexistência com 404 seria enganoso — o usuário literalmente vê a categoria na tela.
Por isso: não encontrada → 404, do sistema → 403 explícito, de outro usuário → 404 (aqui
sim, mesmo raciocínio anti-BOLA do `Conta`, porque é dado privado). `_buscar_editavel()`
constrói sobre `_buscar_visivel()` para não duplicar a lógica de "não encontrada".

**Vínculo de hierarquia entre usuários é tratado como um caso do mesmo problema.**
`_resolver_pai()` reusa `_buscar_visivel()` — a mesma checagem que impede ler a categoria
privada de outro usuário também impede apontar `categoria_pai_id` para ela, com a mesma
resposta (404). Um único ponto de validação para os dois usos.

**Ciclo e auto-referência são o mesmo mecanismo com uma mensagem mais específica no caso
trivial.** `_cria_ciclo()` sobe a cadeia de ancestrais a partir do pai proposto; se
`categoria_id` aparecer nessa cadeia, o novo vínculo criaria um ciclo — auto-referência
(pai = si mesma) é o caso de profundidade zero desse mesmo problema, mas ganha uma
verificação e mensagem própria (`"Uma categoria não pode ser pai dela mesma."`) por
clareza, antes de cair no caso geral. A função tem proteção contra loop infinito
(`visitados`) caso uma hierarquia já corrompida no banco seja encontrada — não deveria
acontecer dado que toda escrita passa por esta validação, mas é uma rede de segurança
barata.

**Exclusão é soft delete, mesmo padrão do `Conta`**, apesar de `Transacao.categoria_id`
usar `ondelete=SET NULL` (não `CASCADE` como em `Conta`) — ou seja, um DELETE físico não
quebraria integridade referencial aqui. Mantido soft delete mesmo assim, por consistência
e para que transações antigas não percam o rótulo da categoria silenciosamente quando ela
sai das listas de escolha ativas.

## Observações registradas, não implementadas

- **Sem validação de consistência de `tipo` entre categoria pai e filha** (ex:
  subcategoria `RECEITA` sob pai `DESPESA`). Não foi pedido, e a semântica correta é
  ambígua (o que fazer com uma filha `AMBOS` sob um pai `DESPESA`?) — decisão deixada em
  aberto até haver um caso de uso real que force a resposta.
- **`Categoria.categoria_pai_id` não tem índice.** Mesma classe de achado já registrada
  para `Transacao.conta_id` em `docs/decisao-performance-saldo.md`: a query de
  `existe_subcategoria_ativa()` filtra por essa coluna sem índice, o que em volume viraria
  *table scan*. Não é urgente (hierarquias de categoria são tipicamente rasas e poucas
  por usuário — nada como o volume de transações), mas seguindo o mesmo princípio já
  estabelecido, o lugar natural para resolver isso é numa migration dedicada, não como
  correção isolada agora.
- **`_resolver_pai()` e `_buscar_editavel()` fazem buscas independentes** quando os dois
  são chamados dentro de `atualizar()` (uma para a própria categoria, outra para o pai
  proposto) — nenhuma duplicação de query para a MESMA linha, só uma consulta a mais que
  seria inevitável de qualquer forma (categoria e pai são linhas diferentes). Não é uma
  ineficiência real, só uma observação de leitura do código.
- **Categorias do sistema não têm mecanismo de seed** nesta etapa — hoje só existem se
  inseridas manualmente (como os testes de integração fazem, direto via `db_session`). Um
  script/migration de seed fica para quando fizer sentido ter um conjunto padrão definido.

## Conclusão

Com o gap de PATCH corrigido e testado, e sem outro problema de arquitetura, segurança,
duplicação ou regra de negócio ausente identificado nesta revisão, o CRUD de Categoria
está encerrado e segue o mesmo padrão de qualidade do CRUD de Conta.
