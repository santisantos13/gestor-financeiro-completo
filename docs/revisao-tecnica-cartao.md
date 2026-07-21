# Revisão técnica — CRUD de Cartão

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada** — nenhum problema de arquitetura,
segurança ou regra de negócio ausente foi encontrado nesta revisão.

## Resumo

Segue o padrão `Router → Service → Repository` estabelecido em `Conta`/`Categoria`/`Tag`,
reaproveitando dois padrões já validados (nome único com soft delete, de `Tag`; posse
verificada com resposta 404 uniforme, de todos os anteriores) e introduzindo um padrão
novo: validação cruzada de posse entre duas entidades diferentes. 200 testes passam (23
unitários com repositories falsos, 24 de integração via `TestClient`, mais os 153
pré-existentes de outras camadas).

## Decisão nova: Service validando posse de uma entidade que não é a sua

Até `Tag`, todo Service só precisava verificar posse da própria entidade
(`cartao.usuario_id == usuario_id`). `Cartao` introduz o primeiro caso em que um campo do
payload (`conta_pagamento_id`) referencia outra entidade de domínio (`Conta`), e essa
referência precisa ser validada como pertencente ao mesmo usuário — sem essa checagem, um
usuário malicioso poderia criar um cartão apontando para a conta de outro usuário
(inconsistência explicitamente vetada pelo pedido: "não permitir inconsistências entre
Conta e Usuário").

**Decisão:** `CartaoService` recebe `ContaRepository` por injeção, além do seu próprio
`CartaoRepository` (`get_cartao_service` em `deps.py` monta os dois). `_validar_conta_do_usuario()`
usa só `ContaRepository.get()` (leitura simples) — não `ContaService` inteiro, que traria
consigo a responsabilidade de calcular `saldo_atual`, desnecessária aqui (Interface
Segregation: o Service só depende do que efetivamente usa). Mesma resposta (404) para
"conta não existe" e "conta é de outro usuário", pelo mesmo raciocínio anti-enumeração já
aplicado em `CategoriaService._resolver_pai` — um usuário não pode descobrir, testando
IDs no payload de criação de cartão, quais contas outros usuários têm.

Essa validação roda tanto em `criar()` (obrigatória, `conta_pagamento_id` é campo
obrigatório) quanto em `atualizar()` (só quando o cliente de fato envia
`conta_pagamento_id` no PATCH).

## Nome único + soft delete: mesmo padrão de Tag, reaplicado sem modificações

`Cartao` já tinha `ativo` desde o model original (soft delete preparado desde o início),
mas nunca teve unicidade de nome. Adicionar `UniqueConstraint(usuario_id, nome)` reabre
exatamente a mesma tensão já resolvida em `TagService`: a constraint não distingue cartão
ativo de desativado. Resolvido com o idêntico mecanismo de reativação-por-colisão-de-nome
em `criar()`, incluindo a mesma assimetria proposital entre `criar()` (reativa) e
`atualizar()` (bloqueia com 409 em vez de mesclar) — ver docstrings em `CartaoService` e
`docs/revisao-tecnica-tag.md` para o raciocínio completo, que não precisou ser
redescoberto aqui.

## `limite_disponivel`: calculado, nunca armazenado — mesma decisão de `Conta.saldo_atual`

Fórmula: `limite - Σ(despesas do cartão cuja fatura ainda não foi paga, incluindo as que
ainda não pertencem a nenhuma fatura)`. Implementada como `CartaoRepository.somar_gastos_nao_pagos()`,
um `LEFT JOIN` entre `Transacao` e `Fatura` filtrando `Fatura.status != PAGA OR Fatura.id IS NULL`.

Como `Transacao` e `Fatura` ainda não têm CRUD/geração automática nesta etapa (fora de
escopo explícito deste pedido), a query roda hoje sobre tabelas vazias na prática e
devolve sempre `limite_disponivel = limite`. Isso não é uma limitação da implementação:
é exatamente a mesma situação já documentada para `ContaRepository.somar_transacoes_pagas`
em `docs/decisao-performance-saldo.md` — o cálculo real-time via SQL é a decisão
definitiva, não uma query provisória esperando ser substituída depois. Os dois testes de
integração que inserem `Transacao`/`Fatura` diretamente via `db_session` (contornando a
ausência de CRUD dessas entidades) confirmam que a fórmula já está correta e pronta para
quando esses CRUDs existirem — nenhum ajuste será necessário em `CartaoService` nesse
momento, só a query passará a encontrar linhas de verdade.

**Não é limitado (clamp) em zero.** Um cartão "estourado" (gastos maiores que o limite)
mostra `limite_disponivel` negativo — de propósito, mesmo raciocínio de não esconder saldo
negativo em `Conta`: exibir o estouro real é mais correto do que mascará-lo com zero.

## Validações de payload

`dia_fechamento`/`dia_vencimento` restritos a `1..31` via `Field(ge=1, le=31)` no Schema —
nenhuma ordem relativa entre os dois é exigida (`vencimento < fechamento` numericamente é
um caso real e comum, quando o vencimento cai no mês seguinte ao fechamento). `limite`
restrito a `>= 0` via `Field(ge=0)`, tanto em `CartaoCreate` quanto em `CartaoUpdate`.
`ultimos_quatro_digitos` validado por regex (`^\d{4}$`) — só os 4 dígitos, nunca o número
completo do cartão, que não é coletado em nenhum campo do sistema. `instituicao`,
`bandeira` e `ultimos_quatro_digitos` são obrigatórios em `CartaoCreate` (diferente de
`Conta.instituicao`, que é opcional) — tratados como atributos identificadores do cartão
físico, não metadados incidentais.

## Observações registradas, não implementadas

- **Dia 29/30/31 pode não existir em todo mês** (fevereiro, meses de 30 dias). A validação
  atual (`1..31`) aceita esses valores como "dia do mês" no sentido recorrente/genérico
  (prática comum em sistemas de cobrança: dia 31 interpretado como "último dia do mês"
  quando o mês tem menos dias). Nenhuma lógica de ajuste foi implementada, porque ainda não
  há geração de fatura para consumir esse valor de fato — decisão de resolução (ajustar
  para o último dia válido vs. rejeitar) fica para quando o CRUD de `Fatura` existir.
- **Nenhuma checagem de "cartão em uso" bloqueia a desativação.** Diferente de `Categoria`
  (bloqueia exclusão com subcategoria ativa), `Cartao.desativar()` não verifica faturas
  em aberto antes de desativar. Não implementado agora porque ainda não há geração de
  fatura nem qualquer fatura real no sistema — quando essa geração existir, vale avaliar se
  desativar um cartão com fatura `ABERTA`/`FECHADA` (ainda não paga) deveria ser bloqueado,
  seguindo o mesmo princípio já registrado como `# TODO(categoria-em-uso)` em
  `CategoriaService`.
- **`Transacao.cartao_id` não tem índice.** Mesma classe de achado já registrada para
  `Transacao.conta_id` em `docs/decisao-performance-saldo.md`: a query de
  `somar_gastos_nao_pagos()` filtra por essa coluna sem índice dedicado. Mesmo raciocínio
  de não urgência (poucas transações por cartão comparado ao volume total do sistema) e
  mesma decisão de resolver isso numa migration dedicada quando o CRUD de `Transacao`
  nascer, não como correção isolada agora.
- **Trocar `conta_pagamento_id` de um cartão com faturas antigas não tem tratamento
  especial.** O PATCH simplesmente atualiza o vínculo; faturas passadas continuam
  associadas ao cartão (não à conta), então não há inconsistência de dado, só uma mudança
  de "para onde o próximo pagamento vai sair" - comportamento correto sem exigir nenhuma
  lógica adicional.

## Conclusão

Sem problema de arquitetura, segurança, duplicação ou regra de negócio ausente
identificado nesta revisão. O padrão de validação cruzada entre Services (`CartaoService`
lendo `ContaRepository`) é novo neste projeto, mas segue estritamente os mesmos princípios
já estabelecidos (injeção explícita, checagem mínima necessária, resposta anti-enumeração
uniforme) — não foi necessário desviar do padrão em nenhum ponto. O CRUD de Cartão está
encerrado e segue o mesmo padrão de qualidade dos CRUDs de Conta, Categoria e Tag.
