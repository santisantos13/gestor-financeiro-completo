# Revisão técnica — backend (estado atual: arquitetura-base, zero CRUDs)

Revisão como se este fosse um Pull Request numa fintech: o código ainda não expõe
nenhuma regra de negócio real (nenhum Service/Repository concreto existe, só a base
genérica), então o foco aqui é arquitetura, contratos entre camadas e riscos que vão se
multiplicar assim que os CRUDs forem escritos em cima dessa fundação. Melhor pegar agora
do que depois de 13 entidades replicarem o mesmo padrão.

## Resumo executivo

A separação de camadas está correta e bem justificada (SRP, DIP via `Protocol`,
ISP explícito na ausência de um `BaseService`). O uso de `Numeric`/`Decimal` para
dinheiro e o `CHECK` constraint no banco para `Transacao` são acertos que muita fintech
madura não tem. Os dois problemas que **precisam** ser resolvidos antes do primeiro
endpoint real: (1) o `Repository` genérico não isola por usuário — hoje, `get()`/`list()`
buscam por qualquer linha do banco, de qualquer usuário; (2) não existe nenhum mecanismo
de autenticação/autorização ainda. Combinados, esses dois pontos são um vazamento de
dados entre usuários esperando para acontecer assim que o primeiro endpoint for exposto.

---

## P0 — Bloqueadores antes do primeiro CRUD

**1. `SQLAlchemyRepository.get()`/`list()` não têm isolamento multi-tenant.**
`get(self, id)` faz `self.db.get(self.model, id)` — busca por PK, sem filtro nenhum de
`usuario_id`. `list()` retorna literalmente todas as linhas da tabela. Se um
`ContaService.buscar_conta(id)` só chamar `self.repo.get(id)`, o usuário A consegue ler
(e, num `update`/`delete`, modificar) dados do usuário B bastando adivinhar/incrementar
um ID sequencial. Isso é o tipo de bug que em fintech vira incidente de vazamento de
dados financeiros, não só um bug funcional. Antes de escrever o primeiro
Repository/Service concreto, vale decidir explicitamente a estratégia: cada Repository
concreto sobrescreve `get`/`list` exigindo `usuario_id`; ou o Service sempre revalida
`objeto.usuario_id == usuario_atual.id` depois de qualquer `get()` antes de devolver ou
mutar (defesa em profundidade); idealmente as duas coisas juntas, não uma ou outra.

**2. Não existe autenticação nem contexto de "usuário atual".**
`Usuario.senha_hash` existe no model, mas não há endpoint de login, geração/validação de
token, nem uma dependency tipo `get_usuario_atual()` em `app/api/deps.py`. Sem isso, o
ponto 1 acima não tem nem como ser corrigido de forma real (não dá pra filtrar por
"usuário atual" se não existe um jeito de saber quem é o usuário atual). Isso deveria ser
a próxima etapa antes de qualquer CRUD de domínio, não depois.

**3. SQLite como banco de um sistema financeiro real.**
Isso já foi decidido lá no início do projeto e não é para reabrir sem necessidade, mas
como o pedido aqui é uma revisão "como fintech": SQLite trava em nível de arquivo, tem um
único escritor por vez, não replica, não tem point-in-time recovery, e o próprio
`use_alter`/modo batch que usamos na migration existe só por causa de limitações do
SQLite. Para uso pessoal/local, não é um problema. Para qualquer cenário com mais de um
usuário simultâneo escrevendo (o multi-user já foi decidido!) ou qualquer ambição de
produção real, é o tipo de decisão que vale documentar explicitamente como débito técnico
aceito, com um gatilho definido para quando migrar (ex: "se algum dia isso for hospedado
para vários usuários reais ao mesmo tempo, trocar para Postgres antes").

---

## P1 — Alto risco

**4. `Alerta`/`Anexo` usam referência polimórfica sem integridade referencial no banco.**
Já foi uma decisão consciente (documentada nos comentários dos models), mas o preço dela
é real: apagar uma `Transacao` não vai apagar (nem impedir) `Alerta`/`Anexo` que
apontavam pra ela via `entidade_tipo`/`entidade_id` — eles ficam órfãos silenciosamente,
sem erro nenhum. Isso precisa virar responsabilidade explícita do Service de cada
entidade referenciável (ex: `TransacaoService.deletar` também precisa limpar
`Alerta`/`Anexo` órfãos), ou vai vazar registros lixo no banco aos poucos.

**5. Cascade delete de `Usuario` apaga todo o histórico financeiro para sempre.**
`cascade="all, delete-orphan"` em todos os relacionamentos de `Usuario` significa que
excluir um usuário apaga irreversivelmente todas as transações, faturas, etc. Pra maioria
dos sistemas financeiros isso é o oposto do que se quer — o normal é desativar a conta
(`ativo=False`, que já existe no model) e reter o histórico por razões de auditoria/
compliance, com exclusão definitiva sendo uma operação separada, deliberada e talvez
sujeita a prazo de retenção legal. Vale decidir isso antes de implementar
`UsuarioService.deletar`, porque uma vez que o comportamento cascade estiver em produção
com dados reais, corrigir é bem mais caro.

**6. Paginação sem `ORDER BY` e sem limite máximo.**
`list(skip, limit)` não define nenhuma ordenação. Sem `ORDER BY`, a ordem de retorno do
SQL não é garantida entre chamadas — paginar "página 1, página 2" pode repetir ou pular
linhas de verdade, não é só um detalhe cosmético. Além disso, `limit` não tem teto: nada
impede um client de pedir `limit=1000000` e forçar uma query pesada. Isso deveria ganhar
uma ordenação padrão (ex: por `id` ou `criado_em`) e um `MAX_LIMIT` no Repository genérico.

**7. Nenhum logging nem trilha de auditoria.**
Zero chamadas de log em todo o backend. Hoje, se um 500 acontecer em produção, isso é
invisível — não tem como saber que aconteceu, muito menos depurar. Para um sistema
financeiro, isso é ainda mais crítico: mudanças de saldo, criação/edição de transação,
tentativas de acesso negado deveriam deixar rastro (quem, quando, o quê), tanto para
depuração quanto para eventual necessidade de auditoria. Não precisa ser sofisticado
agora, mas a ausência total é um risco que cresce a cada CRUD novo sem isso.

**8. Nenhum CI configurado.**
`pytest` roda localmente, mas não há `.github/workflows` (ou equivalente) garantindo que
os testes rodam a cada mudança. Numa fintech de verdade, um PR sem CI verde não seria
sequer revisado.

---

## P2 — Médio

**9. `IRepository` (Protocol) ainda não é consumido em lugar nenhum.**
A abstração está correta em teoria (Dependency Inversion), mas como nenhum Service
concreto existe ainda, é uma abstração especulativa até prova em contrário. Não é
necessariamente um problema — só vale confirmar, quando o primeiro Service concreto for
escrito, que ele de fato depende de `IRepository` e não importa `SQLAlchemyRepository`
diretamente, senão a interface vira documentação morta.

**10. `atualizado_em` só é preenchido pelo SQLAlchemy (client-side), não pelo banco.**
`onupdate=func.now()` só dispara quando o UPDATE passa pelo ORM. Qualquer alteração feita
fora dele (um script de correção de dado, uma migration de dado, um `UPDATE` manual) não
atualiza esse campo, e ninguém vai perceber porque não há nada acusando a divergência.
Se `atualizado_em` for usado pra alguma decisão de negócio no futuro (ex: "essa fatura foi
editada depois de fechada?"), vale lembrar dessa limitação.

**11. Cobertura de teste é só do Repository genérico.**
Os testes atuais provam que `get/list/create/update/delete` funcionam mecanicamente — o
que é o correto para esta etapa, mas vale nomear o que ainda não está coberto: nenhum
teste hoje verifica as constraints do banco (`CHECK` de conta_id/cartao_id,
`UniqueConstraint` de fatura ou tag), nem a migration em si (upgrade/downgrade) roda de
forma automatizada — isso hoje só foi validado manualmente por fora do pytest.

**12. Arquitetura síncrona (SQLAlchemy sync) sob FastAPI.**
Funciona corretamente e é a escolha certa para começar, mas cada chamada de banco ocupa
uma thread do threadpool do FastAPI (rotas `def`, não `async def`). Para o volume de uso
pessoal/multi-usuário pequeno isso não é problema; só registrar que não escala
indefinidamente sem repensar (SQLAlchemy async + driver async) se o throughput crescer.

**13. `BusinessRuleError` mapeado para HTTP 422.**
422 já é o status que o próprio FastAPI/Pydantic usa automaticamente para erro de
validação de schema. Reusar 422 para regra de negócio ("saldo insuficiente", por
exemplo) faz o frontend não conseguir distinguir "seu JSON está malformado" de "sua
requisição é válida mas violou uma regra" só pelo status code — só pelo corpo da
resposta. Vale considerar 400 para `BusinessRuleError` e reservar 422 exclusivamente para
erro de schema.

**14. CORS com `allow_methods=["*"]` e `allow_headers=["*"]`.**
Combinado com `allow_origins` explícito (não é `"*"`) isso não é uma vulnerabilidade
imediata, mas é mais permissivo do que precisa ser hoje (só GET é usado). Vale reduzir ao
conjunto real de métodos/headers conforme os endpoints forem existindo, em vez de deixar
wildcard por padrão até o fim do projeto.

---

## P3 — Observações menores

- **Cascade delete de subcategoria:** apagar uma `Categoria` pai apaga (`ondelete="CASCADE"`)
  todas as subcategorias silenciosamente. Pode ser surpreendente numa tela de "excluir
  categoria" sem aviso explícito de quantos filhos serão levados junto.
- **`Alerta.condicao` como `String(500)` livre** guardando JSON serializado manualmente,
  em vez de um tipo `JSON` nativo do SQLAlchemy. Funciona, mas perde a possibilidade de
  consultar/validar o conteúdo no nível do banco.
- **`taxa_juros` como `Numeric(6,4)`** limita a menos de 100% — correto para taxas
  mensais, mas se algum dia for usado para taxa anual isso estoura silenciosamente sem
  erro (SQLAlchemy só trunca/erra na gravação, vale confirmar comportamento).
- **`/health` não verifica conectividade com o banco** — hoje só confirma que o processo
  FastAPI está de pé, não que a aplicação está de fato operacional (útil para readiness
  probes no futuro).
- **Mensagens de exceção de domínio vazam texto cru para o cliente** (`str(exc)` direto
  no `detail`). Enquanto as exceções forem só as três de domínio, tudo bem — mas vale
  garantir que nenhuma delas um dia carregue detalhe interno (nome de tabela, etc.) sem
  querer.

---

## O que já está bem feito (vale manter)

- Separação Router → Service → Repository é real, não só nominal: cada camada só conhece
  a de baixo, e a decisão de não ter `BaseService` genérico é bem justificada (ISP) em vez
  de copiada de tutorial.
- `Decimal`/`Numeric` para todo valor monetário, nunca `float` — erro clássico que este
  projeto não cometeu.
- `CheckConstraint` de `conta_id XOR cartao_id` garantido no banco, não só validado na
  aplicação — sobrevive a um `INSERT` feito por qualquer via, não só pela API.
- Unit of Work implícita bem desenhada: `get_db()` comita só no sucesso do request
  inteiro e reverte tudo em qualquer exceção, sem precisar de uma classe `UnitOfWork`
  separada nesta escala de projeto.
- Testes já cobrem não só o caminho feliz, mas uma invariante de arquitetura
  (`test_create_nao_chama_commit`) — é o tipo de teste que evita regressão silenciosa de
  design, não só de comportamento.

## Ordem sugerida de resolução

1. Decidir e implementar autenticação mínima + `get_usuario_atual()` (bloqueia tudo o
   resto).
2. Resolver isolamento multi-tenant no Repository/Service antes do primeiro CRUD real.
3. Definir a política de exclusão (`Usuario` e cascades em geral): soft-delete vs. hard
   delete, antes que existam dados reais para migrar depois.
4. Adicionar logging mínimo (nem que seja só request/response + erros não tratados).
5. Configurar CI rodando `pytest` a cada push.
6. Os itens P2/P3 podem ser resolvidos à medida que cada CRUD for escrito, não precisam
   de uma etapa dedicada.
