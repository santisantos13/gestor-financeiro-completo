# Análise arquitetural — Parcelamento

Análise de modelagem prévia à implementação do CRUD de `Parcelamento`, seguindo o mesmo
rigor de `docs/analise-arquitetural-fatura.md` e `docs/analise-arquitetural-transacao.md`.
Diferente das entidades anteriores, `Parcelamento` não introduz nenhuma regra de posse ou
cálculo nova em si — o desenho inteiro gira em torno de **reaproveitar** `TransacaoService`
e `FaturaService` em vez de duplicar o que eles já resolvem. **Status: aprovada.**

## Parcelamento ↔ Transação

`Transacao.parcelamento_id` (nullable, `SET NULL`) + `numero_parcela` (1..N) já modelados.
Cada parcela concreta é uma linha em `Transacao`; `Parcelamento` é só o cabeçalho — não
duplica nenhum valor financeiro além do que já está no model (`valor_total`, `num_parcelas`,
`taxa_juros`, `data_inicio`). Categoria e tags de cada parcela são independentes, herdadas
do Parcelamento na geração mas livremente editáveis depois (mesmo princípio de "campo
descritivo sempre editável" da imutabilidade de fatura fechada). Toda parcela é `DESPESA`.

## Parcelamento ↔ Cartão

`Parcelamento.cartao_id`/`conta_id` são ambos nullable, mas **sem** `CheckConstraint` XOR
entre eles hoje — gap a corrigir (ver seção de mudanças). Cartão: cada parcela é uma
`Transacao` de cartão cuja `data` própria decide em qual `Fatura` ela cai (parcelas
diferentes podem cair em ciclos diferentes, exatamente como `docs/analise-arquitetural-fatura.md`
já previu). Conta: cada parcela é uma `Transacao` de conta comum, `status`
`PENDENTE`/`PAGO` normal.

## Parcelamento ↔ Fatura

Sem relação direta, por design (`CheckConstraint` de "no máximo um contrato" em `Transacao`
não inclui `fatura_id` — uma parcela tem os dois ao mesmo tempo). A geração de parcelas é
**eager** (todas as N de uma vez, na criação), o que implica criar as Faturas futuras
correspondentes também antecipadamente — uma exceção deliberada e justificada ao princípio
"fatura futura nunca é gerada com antecedência" de Fatura: aquele princípio trata de não
gerar ciclos que ninguém se comprometeu a preencher; um Parcelamento é exatamente um
compromisso determinístico com N lançamentos futuros já conhecidos no momento da compra.

## Representação da compra parcelada

`Parcelamento` = cabeçalho (`descricao`, `valor_total`, `num_parcelas`, `taxa_juros`
opcional, `data_inicio`, `cartao_id` XOR `conta_id`, `categoria_id`). `taxa_juros` é
puramente informativa — `valor_total` já é o valor final a pagar, sem fórmula de
amortização nenhuma por trás (é isso que distingue Parcelamento de
Financiamento/Emprestimo). `data_inicio` é a data da compra E da parcela 1/N; as demais
somam 1, 2... meses a partir daí, com o mesmo clamping de dia de mês já usado por
`FaturaService`.

## Geração das parcelas

Eager, no momento da criação — diferente da resolução lazy de Fatura, porque aqui todas as
N datas/valores já são 100% determinísticas de imediato. Divisão do valor: `valor_parcela =
round(valor_total / num_parcelas, 2)` para as primeiras N-1; a última absorve o resto
(`valor_total - valor_parcela × (N-1)`), garantindo que a soma bate exatamente com
`valor_total`.

**Sem duplicar regra de Transação**: `ParcelamentoService` nunca constrói uma `Transacao`
nem fala com `TransacaoRepository` — para cada parcela, chama `TransacaoService.criar()`.
Isso reaproveita de graça posse de conta/cartão, ativo/inativo, compatibilidade de
categoria, resolução de fatura e a validação estrutural XOR — nada disso é reimplementado
em `ParcelamentoService`. Mesmo padrão de composição Service→Service já usado por
`TransacaoService`→`FaturaService`. Todas as N chamadas na mesma sessão de request; falha no
meio já causa rollback atômico via a Unit of Work implícita do projeto, sem tratamento
especial.

## Antecipação de parcelas

Não exige nenhum mecanismo novo. Parcela de conta: `PATCH /transacoes/{id}` já cobre
(nunca travada). Parcela de cartão: como a geração é eager, a parcela futura e sua fatura
futura já existem — antecipar é só pagar aquela fatura mais cedo via
`POST /faturas/{id}/pagamentos` (endpoint já existente). Quitação total antecipada é pagar
cada fatura futura restante, uma por vez, pelo mesmo endpoint (cada parcela cai numa fatura
diferente, por construção). Sem desconto por antecipação — não existe amortização aqui.

## Cancelamento

Achado que muda a modelagem: hard delete de `Parcelamento` com parcelas geradas violaria o
`CheckConstraint` de `numero_parcela` de `Transacao` (o `ondelete="SET NULL"` zeraria
`parcelamento_id` mas deixaria `numero_parcela` preenchido). Como a geração é sempre eager,
não existe "Parcelamento vazio" depois de criado — não há janela segura para exclusão
física. **Decisão: sem endpoint de exclusão física.** Cancelamento é uma ação própria
(`POST /parcelamentos/{id}/cancelar`, mesmo estilo de `Fatura`): marca `ativo=False` no
cabeçalho e remove, via `TransacaoService.excluir()` reaproveitado, só as parcelas ainda não
travadas (conta: sempre; cartão: só se a fatura correspondente ainda está `ABERTA`).
Parcelas com fatura já fechada ficam intocadas — cancelamento nunca reescreve histórico.
Diferente do "tudo ou nada" de `Fatura.excluir()` porque Parcelamento naturalmente acumula
histórico ao longo de vários ciclos; "cancelar o que falta" é a única semântica sensata.

## Prevenção de inconsistências

1. Novo `CheckConstraint` em `Parcelamento`: XOR `cartao_id`/`conta_id`.
2. Nova `UniqueConstraint(parcelamento_id, numero_parcela)` em `Transacao` — impede duas
   linhas reivindicando a mesma parcela do mesmo Parcelamento (`NULL` não colide consigo
   mesmo, então não afeta transações sem parcelamento).
3. `num_parcelas >= 2` no Schema.
4. Consistência soma-das-parcelas-== `valor_total` garantida por construção na geração, não
   por checagem contínua — editar uma parcela isolada depois pode divergir do total, aceito
   como limitação conhecida e documentada (mesmo raciocínio de não travar edição que
   ninguém pediu para travar).
5. `TransacaoRepository.listar_do_usuario` ganha filtro `parcelamento_id`.

## Evitar duplicação de regras entre Parcelamento e Transação

`ParcelamentoService` orquestra `TransacaoService`, nunca contorna. A única regra que
genuinamente pertence a `ParcelamentoService` é o que `TransacaoService` estruturalmente não
pode saber (opera numa transação por vez): dividir `valor_total` em N parcelas datadas, e
decidir quais cancelar. `ParcelamentoUpdate` não deveria existir como `PATCH` genérico
tocando campos estruturais (`valor_total`, `num_parcelas`, `cartao_id`, `conta_id`,
`data_inicio` são imutáveis após a criação — mudar qualquer um exigiria regenerar parcelas).

## Mudanças de modelagem necessárias antes da implementação

1. Novo `CheckConstraint` em `Parcelamento`: `cartao_id` XOR `conta_id`.
2. Nova `UniqueConstraint(parcelamento_id, numero_parcela)` em `Transacao`.
3. `TransacaoRepository.listar_do_usuario` ganha filtro opcional `parcelamento_id`.
4. `ParcelamentoRepository` novo; `TransacaoService` passa a validar posse (mesmo usuário) e
   faixa (`numero_parcela` entre 1 e `num_parcelas`) ao vincular manualmente um
   `parcelamento_id` — fecha a lacuna YAGNI deixada em aberto em
   `docs/analise-arquitetural-transacao.md` especificamente para este campo.
   `financiamento_id`/`emprestimo_id`/`meta_id`/`origem_recorrente_id` continuam sem essa
   validação até seus próprios CRUDs existirem.
5. Extrair `_proximo_mes`/`_dia_valido` de `FaturaService` para um utilitário compartilhado
   (`ParcelamentoService` precisa do mesmo cálculo para datar as parcelas).
6. Nenhuma mudança necessária em `Cartão`, `Fatura`, `Categoria`, `Conta`.
7. Sem endpoint de exclusão física de `Parcelamento` — só `criar`, `obter`, `listar`, e a
   ação `cancelar` (parcial, preserva histórico).

## Conclusão

Arquitetura validada. A implementação não introduz nenhuma abstração nova além de um
utilitário de datas compartilhado (extração, não invenção) — todo o resto é composição dos
Services já existentes. Pronta para servir de base à implementação do CRUD de
`Parcelamento`.
