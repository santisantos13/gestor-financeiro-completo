# Revisão técnica — CRUD de Empréstimo

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.**

## Resumo

Segue `Router → Service → Repository`, compondo `TransacaoService` exatamente como
`FinanciamentoService` — nunca `TransacaoRepository` diretamente para escrita. Reaproveita
`ContratoCreditoMixin` sem alteração. O domínio é estruturalmente idêntico ao de
`Financiamento`, exatamente como pedido: a única diferença de negócio real é que
`valor_liberado` é obrigatório e gera SEMPRE uma `Transacao` de RECEITA avulsa (o
desembolso), nunca condicional — contra a entrada opcional/DESPESA de `Financiamento`. O
cronograma PRICE/SAC, antes duplicado dentro de `FinanciamentoService`, foi extraído para
`app/core/amortizacao.py` e passou a ser reaproveitado por ambos os Services. 644 testes
passam no total (393 unitários, 251 de integração) — 29 unitários novos de
`EmprestimoService`, mais os acréscimos em `TransacaoService` (posse/faixa/duplicidade de
`emprestimo_id`, regression test do guard de estado mesclado) e 20 de integração novos do
fluxo de Empréstimo. Migração validada em ciclo completo `upgrade` → `downgrade` →
`upgrade` → `check` contra banco descartável, zero drift.

O achado mais significativo desta etapa não é um bug introduzido pelo `Emprestimo` em si,
mas um bug pré-existente e sério que o trabalho de migração acabou expondo — ver seção
dedicada abaixo.

## Achado central: bug pré-existente do SQLAlchemy bloqueando toda a suíte e o Alembic

Ao tentar gerar a migration do `Emprestimo` (`alembic revision --autogenerate`), a
inicialização do mapeamento de models falhou com:

```
sqlalchemy.exc.ArgumentError: Could not resolve all types within mapped annotation:
"sqlalchemy.orm.base.Mapped[ForwardRef('Meta | None')]"
```

Isso não é um erro cosmético — `configure_mappers()` falhar bloqueia literalmente qualquer
uso real do ORM: toda a suíte de testes (unitária, via import de `app.models` nos fakes; e
de integração, via `conftest.py`) e o próprio Alembic pararam de funcionar. Reproduzido de
forma 100% consistente, inclusive num processo Python novo com bytecode cache limpo — não
era o problema intermitente de corrupção de arquivo já conhecido deste ambiente.

**Investigação.** `Transacao.meta: Mapped["Meta | None"]` é um forward-ref do tipo *string
com union* (`ClassName | None`). Diferente de um forward-ref simples (`Mapped["ClassName"]`,
que o SQLAlchemy resolve via um fallback baseado no registro de mappers), uma expressão de
união composta precisa ser avaliada como código Python de verdade
(`eval()`) contra o namespace do módulo que declara a annotation — neste caso,
`app/models/transacao.py`. As outras relações da mesma classe
(`Mapped["Parcelamento | None"]`, `Mapped["Financiamento | None"]`, `Mapped["Emprestimo |
None"]`, `Mapped["ContaRecorrente | None"]`) resolviam normalmente sem nenhum import direto
— o que tornou a investigação mais difícil, já que a assinatura é estruturalmente idêntica
à do campo `meta`. Reordenar os imports em `app/models/__init__.py` (colocando `Meta` antes
de `Transacao`) NÃO resolveu — o registro de import de um módulo externo não afeta o
namespace interno de `transacao.py`, que é o que o `eval()` de fato consulta.

**Correção aplicada.** Import direto em `app/models/transacao.py`:

```python
from app.models.meta import Meta  # noqa: F401 - necessario para resolver o forward ref "Meta | None" abaixo
```

Confirmado sem risco de import circular (`app/models/meta.py` não importa `Transacao`).
Após a correção, `configure_mappers()` passa, e a suíte completa (393 + 251) roda verde.

**Avaliação.** Este é quase certamente um bug pré-existente, não introduzido pelo
`Emprestimo` — o relacionamento `Transacao.meta` e a ausência do import direto já existiam
antes desta etapa. A hipótese mais provável é que `configure_mappers()` nunca havia sido
exercitado "a frio" (sem bytecode cache já favorável) nas sessões anteriores; este projeto já
precisou lidar repetidamente com cache de bytecode desatualizado mascarando comportamento
real neste ambiente específico, e é plausível que o mesmo mecanismo tenha escondido este
problema até agora. A causa raiz exata de por que só `Meta` — e nenhuma das outras quatro
relações análogas na mesma classe — precisa do import direto não foi totalmente explicada
mesmo após inspecionar o código-fonte interno do SQLAlchemy
(`sqlalchemy.util.typing.de_stringify_annotation`, `RelationshipProperty.declarative_scan`);
um reprodutor minimalista isolado (classes `Base`/`Meta`/`Transacao` fake) sugeriu que o
fallback via registro DEVERIA ter funcionado sem o import direto, o que não bateu com o
comportamento observado na aplicação real. A correção é empírica, verificada e sem efeitos
colaterais — mas a explicação completa do "por que só agora" fica em aberto.

## Zero mudanças necessárias no mecanismo de pagamento já existente

Diferente de `Financiamento`, que precisou introduzir o guard de `status` e o método
`marcar_parcela_de_contrato_paga()` do zero, `Emprestimo` não exigiu nenhuma alteração de
lógica nesses dois pontos:

- `TransacaoService.marcar_parcela_de_contrato_paga()` já era genérico o suficiente
  (`if transacao.financiamento_id is None and transacao.emprestimo_id is None: raise ...`) —
  a checagem contra `emprestimo_id` já existia, provavelmente escrita de forma
  antecipadamente genérica durante a implementação de `Financiamento`.
- O guard de estado mesclado em `TransacaoService.atualizar()` (o bug mais sério encontrado
  na revisão de `Financiamento`, que bloqueia `PATCH` de `status` combinado com vínculo de
  contrato de crédito) já checava `emprestimo_id is not None` ao lado de
  `financiamento_id is not None`.

O único trabalho necessário em `TransacaoService` foi adicionar `emprestimo_repo` ao
construtor, o parâmetro `emprestimo_id` em `listar()`, e o novo método `_validar_emprestimo`
(espelho exato de `_validar_financiamento`) chamado em `criar()` e `atualizar()` para
posse/faixa/duplicidade — a mesma validação que `financiamento_id` já tinha. Coberto por um
regression test dedicado,
`test_atualizar_vinculando_emprestimo_e_status_pago_na_mesma_chamada_levanta_business_rule_error`,
que reproduz o mesmo payload malicioso do bug de `Financiamento`
(`{"emprestimo_id": X, "numero_parcela": Y, "status": "PAGO"}` numa transação sem vínculo
prévio) e confirma `BusinessRuleError`. Isso é uma validação forte de que a arquitetura
desenhada durante `Financiamento` estava correta e genérica o suficiente desde o início —
nenhum problema de segurança/consistência análogo foi reencontrado aqui.

## Cronograma PRICE/SAC: extraído, não reescrito

`app/core/amortizacao.py` (`gerar_cronograma()`) contém a mesma matemática que já existia em
`FinanciamentoService._gerar_cronograma_price`/`_gerar_cronograma_sac`, movida sem alteração
de comportamento. Verificado que os 37 testes unitários pré-existentes de
`FinanciamentoService` continuam passando sem nenhuma modificação depois do refactor — a
função pública `FinanciamentoService._gerar_cronograma()` foi mantida como
`staticmethod` que apenas delega, preservando a assinatura que os testes já usavam.
`EmprestimoService` chama `gerar_cronograma()` diretamente, sem staticmethod intermediária —
não havia teste pré-existente para preservar assinatura nesse caso. Os testes unitários de
`EmprestimoService` fazem uma checagem leve (parcela fixa em PRICE, decrescente em SAC),
sem duplicar as invariantes matemáticas exaustivas (soma exata do principal, degeneração
com `taxa_juros=0`, comparação SAC-paga-menos-juros-que-PRICE) já cobertas contra a mesma
função em `test_financiamento_service.py`.

## Desembolso: sempre RECEITA, nunca condicional — verificado que não corrompe a contagem de parcelas

`EmprestimoService.criar()` chama `_gerar_transacao_de_desembolso()` incondicionalmente
(diferente de `Financiamento`, onde a entrada só é gerada `if dados.valor_entrada`), usando
a mesma `conta_id`/`categoria_id` do contrato, sem `emprestimo_id`/`numero_parcela`. Testado
que a transação de desembolso nunca aparece na listagem filtrada por `emprestimo_id`, que
`saldo_devedor` inicial é igual a `valor_liberado` (sem desconto de entrada — não existe
esse conceito aqui), e que `valor_liberado` ausente no payload de criação é rejeitado pelo
schema (422) antes de qualquer escrita no banco — diferente de `Financiamento`, onde o
equivalente era a validação `valor_entrada >= valor_financiado`, que não se aplica aqui.

## `conta_id` obrigatório: decisão consolidada, não uma pendência nova

A análise arquitetural (`docs/analise-arquitetural-emprestimo.md`) formalizou a decisão já
implícita desde `Financiamento`: `ContratoCreditoMixin.conta_id` permanece `nullable=True`
no banco, e a obrigatoriedade continua sendo validada redundantemente em cada Service
(`EmprestimoService._validar_conta_obrigatoria()`, espelho exato do equivalente em
`FinanciamentoService`) — não uma migration que endurece a coluna. Testado que omitir
`conta_id` devolve 422 com mensagem clara, e que nenhuma `Transacao` (nem o desembolso) é
criada quando essa validação falha.

## Migração: sem drift, sem incidentes

`alembic upgrade head` → `downgrade -1` → `upgrade head` → `alembic check` validado limpo
contra um banco SQLite descartável. A migração real (`8411c7918413`) adiciona
`UniqueConstraint(emprestimo_id, numero_parcela)` em `Transacao` via `batch_alter_table`,
quarta aplicação da mesma estratégia proativa (`Parcelamento` → `ContaRecorrente` →
`Financiamento` → `Emprestimo`) — nenhuma das quatro esperou descobrir o bug de duplicidade
de novo para adicionar a constraint. `alembic check` confirma "No new upgrade operations
detected" contra o head atual. Diferente da migração de `Financiamento`, esta não foi
afetada pelos arquivos-placeholder residuais do ambiente (`aaaa0000dummy`,
`0fecbf64f7db`, `8b100b274a2e`) além de encadear corretamente por cima deles via
`down_revision`.

## Corrupção de arquivo por mount: recorrente, sem incidentes não resolvidos

O bug de corrupção de arquivo já documentado em revisões anteriores (edições que passam no
`Edit`/`Write` mas cujo conteúdo via bash aparece divergente do que o Read tool mostra)
atingiu, nesta etapa, `app/services/transacao_service.py` (duas vezes),
`app/repositories/transacao_repository.py`, `app/models/transacao.py` (duas vezes — uma ao
adicionar a `UniqueConstraint`, outra ao adicionar o import de `Meta`), a migration
`8411c7918413` e `tests/unit/test_transacao_service.py`. Todos os casos foram detectados
pela verificação obrigatória pós-edição (`ast.parse`/contagem de bytes via bash) e corrigidos
reescrevendo o arquivo inteiro via heredoc a partir do conteúdo autoritativo do Read tool.
Nenhum caso ficou sem resolução ou exigiu retrabalho de lógica — é puramente uma limitação
mecânica do ambiente desta sessão, não um problema de código.

## O que foi deliberadamente NÃO implementado

Confirmado por leitura do código final: nenhuma menção a renegociação, refinanciamento,
amortização extraordinária, juros variáveis, seguros, multas ou inadimplência.
`permite_quitacao_antecipada` existe no model e no schema, mas não é lido em nenhuma regra
de negócio — persistido e devolvido, YAGNI respeitado, mesmo padrão de `cet` em
`Financiamento`. `INADIMPLENTE` e qualquer ação de cancelamento não têm nenhum caminho de
código que os produza; a única transição de status implementada é `ATIVO → QUITADO`,
automática, disparada dentro de `pagar_parcela()`.

## Conclusão

A implementação segue a arquitetura aprovada e reaproveita `ContratoCreditoMixin` e
`TransacaoService` quase integralmente, sem duplicar nenhuma regra de negócio — o único
código genuinamente novo do domínio é a geração incondicional do desembolso como RECEITA.
Nenhum problema de arquitetura, regra de negócio ou segurança foi encontrado no código do
próprio `Emprestimo`: o guard de estado mesclado que havia sido o achado mais sério da
revisão de `Financiamento` já cobria `emprestimo_id` desde o início, confirmado por
regression test dedicado. O achado real desta etapa foi externo ao domínio de Empréstimo —
um bug pré-existente do SQLAlchemy (forward ref `Mapped["Meta | None"]` não resolvendo)
que bloqueava toda a suíte de testes e o Alembic, corrigido com um import direto e
documentado em detalhe acima, incluindo a lacuna de entendimento sobre por que só esse
campo específico exigia a correção. A migração está validada em ciclo completo sem drift.
Suíte completa: 644 testes passando (393 unitários + 251 de integração).
