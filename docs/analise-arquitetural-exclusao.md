# Análise Arquitetural — Exclusão definitiva (hard delete)

Documento de arquitetura puro — **nenhum código é escrito nesta etapa**. Responde a um
adendo do usuário: hoje toda entidade com CRUD no frontend (Conta, Categoria, Tag, Cartão) só
tem criar, editar e **desativar** (soft delete, `ativo = false`) — falta a opção de
**excluir de verdade**, com confirmação, para "evitar grandes problemas".

Cross-cutting como `docs/analise-arquitetural-rich-pickers.md` (não pertence a uma entidade
só) — mesma convenção: aprovado antes de qualquer código, sequenciado junto com a Etapa F10
por pedido do usuário.

## 0. Por que isso não é "adicionar um botão" — o risco real

Toda entidade que já tem soft delete escolheu esse caminho por um motivo específico, já
documentado no código de cada `Service.desativar()`: **excluir de verdade pode apagar
histórico financeiro por tabela em cascata**, não só a linha da própria entidade. Verificado
diretamente nas FKs do banco (`app/models/*.py`), não hipótese:

| Entidade | Quem aponta para ela | `ondelete` | Efeito de um `DELETE` físico hoje |
|---|---|---|---|
| `Conta` | `Transacao.conta_id` | **CASCADE** | Apagaria **todas as transações** da conta — perda de histórico financeiro real |
| `Categoria` | `Transacao.categoria_id` | `SET NULL` | Transações ficam "sem categoria" (não são apagadas) |
| `Categoria` | `Categoria.categoria_pai_id` (auto-FK) | **CASCADE** | Apagaria **toda a subárvore de subcategorias**, mesmo as inativas |
| `Cartão` | `Fatura.cartao_id` | **CASCADE** | Apagaria **todas as faturas** do cartão — documento financeiro histórico (`valor_total` congelado) some por tabela |
| `Tag` | `transacao_tag` (tabela de associação) | **CASCADE** | Remove só a linha de vínculo — a transação em si **não é afetada** |

Conclusão direta da tabela: **não existe uma regra única "bloqueia se estiver em uso" que
sirva para as quatro entidades igual**. Cada uma precisa da sua própria checagem, do mesmo
jeito que `Fatura.excluir()` já faz (`existe_transacao_vinculada` — precedente já existente no
projeto, ver `app/services/fatura_service.py`) e do jeito que `Categoria.desativar()` já
bloqueia com subcategoria ativa. Este documento estende esse mesmo padrão para as quatro
entidades, nunca inventa um mecanismo novo.

## 1. Decisão central: "Excluir" é uma TERCEIRA ação, nunca substitui "Desativar"

- `Desativar`/`Reativar` (soft delete, `ativo`) continuam existindo exatamente como estão —
  nenhuma mudança de contrato, nenhuma regressão.
- `Excluir` (hard delete) é uma ação nova, **irreversível**, disponível só quando a entidade
  não tem nenhum vínculo real que uma exclusão apagaria silenciosamente.
- **Endpoint novo, não uma reinterpretação do `DELETE` existente**: hoje
  `DELETE /contas/{id}`, `DELETE /categorias/{id}`, `DELETE /tags/{id}`, `DELETE /cartoes/{id}`
  **já significam "desativar"** (confirmado lendo os quatro routers — ex.
  `def desativar_conta(...)` está literalmente pendurado em `@router.delete("/{conta_id}")`).
  Reaproveitar o mesmo verbo+caminho para um significado diferente quebraria o contrato que o
  frontend já depende (todo botão "Desativar" das quatro páginas chama esse endpoint hoje).
  Convenção nova, mesmo espírito das ações de negócio de Fatura (`/faturas/{id}/fechar`,
  `/faturas/{id}/pagamentos` — sub-rotas de ação em vez de sobrecarregar um verbo genérico):
  **`DELETE /{entidade}/{id}/permanente`** para as quatro entidades desta etapa.

## 2. Regra de exclusão por entidade (backend)

Mesmo formato de exceção já usado em todo o projeto (`BusinessRuleError` → 422, mensagem
específica — nunca um 500 genérico nem um `IntegrityError` de banco vazando pro cliente):

### 2.1 Conta

Bloqueia se: existir **qualquer** transação vinculada (`Transacao.conta_id`), **qualquer**
transferência (origem ou destino), ou **qualquer** cartão com `conta_pagamento_id` apontando
para ela — **mesmo inativos/desativados**. Só permite excluir uma conta genuinamente vazia
(criada por engano, nunca usada). Novo método `ContaRepository.existe_vinculo(conta_id)`
(compõe as três checagens acima) + `ContaService.excluir()`.

### 2.2 Categoria

Bloqueia se: existir **qualquer** transação vinculada (`Transacao.categoria_id` — resolve
formalmente o `# TODO(categoria-em-uso)` já presente em `CategoriaService.desativar()`, escrito
exatamente para este momento) **ou** existir **qualquer** subcategoria, ativa ou inativa (a
checagem atual de `_impedir_desativacao_com_subcategoria_ativa` só olha subcategoria *ativa*
porque soft delete não é destrutivo; hard delete tem cascade real no auto-FK, então precisa
ser mais rígido: zero subcategorias em qualquer estado). Categoria de sistema
(`usuario_id is None`) já é somente-leitura (`AcessoNegadoError`) — a mesma checagem de
`_buscar_editavel` já bloqueia exclusão dela, nenhuma regra nova aqui. Novo método
`CategoriaRepository.existe_transacao_vinculada`/`existe_subcategoria` (qualquer status) +
`CategoriaService.excluir()`.

### 2.3 Tag

**Não bloqueia por uso** — diferente das outras três, o vínculo com `Transacao` é N-N via
`transacao_tag` com `ondelete=CASCADE` só na tabela de associação: excluir uma tag remove o
rótulo das transações que a usavam, mas **não apaga nenhuma transação**. Risco real é
inexistente (nenhum dado financeiro é destruído), então a regra de negócio no backend é
simplesmente "sempre permitido" — mas o **frontend avisa quantas transações usam a tag antes
de confirmar** (seção 3), para a exclusão nunca ser uma surpresa silenciosa mesmo sem risco de
perda de histórico. `TagService.excluir()` sem nenhuma checagem de bloqueio.

### 2.4 Cartão

Bloqueia se: existir **qualquer** fatura vinculada (`Fatura.cartao_id`), em qualquer status
(ABERTA, FECHADA, PAGA, etc.) — mesma decisão que `Fatura.excluir()` já aplica a si mesma
("fatura é documento financeiro histórico, nunca desaparece via cascade de outra coisa").
Resolve também o item já listado em `README.md` ("Avaliar bloqueio de desativação de Cartão
com fatura em aberto... ainda não implementado") — a checagem nasce aqui, para hard delete;
decisão explícita de escopo: **não** estender a mesma checagem para `desativar()` nesta etapa
(pedido do usuário é sobre a exclusão nova, não sobre revisar a regra de desativação
existente — abrir esse segundo escopo aqui seria além do pedido). Novo método
`CartaoRepository.existe_fatura_vinculada` + `CartaoService.excluir()`.

## 3. Frontend — nova ação "Excluir" nas quatro páginas

- **Nova `RowAction`** (`Trash2` do `lucide-react`, `tone: "danger"`) ao lado de
  `Desativar`/`Reativar` em `ContasPage`/`CategoriasPage`/`TagsPage`/`CartoesPage` — sempre
  visível (o frontend nunca pré-calcula se a exclusão vai ser aceita; a mesma filosofia já
  usada em todo o projeto: o backend é a única fonte de verdade da regra de negócio, o
  frontend só reage à resposta). Evita uma query extra por linha só para decidir se o botão
  aparece — mesmo raciocínio de "não otimizar antes de confirmar necessidade" já registrado em
  `docs/analise-arquitetural-dashboard.md`, seção 15.
- **Confirmação reaproveitando `ConfirmAction`** (mesmo componente já usado por
  `Desativar` nas quatro páginas), texto explicitamente mais forte e específico por entidade —
  nunca o mesmo texto de "Desativar":
  - Conta/Categoria/Cartão: *"Esta ação é permanente e não pode ser desfeita. `<Nome>` será
    excluído(a) para sempre."*
  - Tag: *"Esta ação é permanente. `<Nome>` será removida de todas as transações que a usam."*
    (sem alarmismo de "perder dados financeiros" — não é o caso aqui, seção 2.3).
- **Erro 422 (bloqueado)** vira toast via `getErrorMessage` — mecânica idêntica a qualquer
  outro erro de regra de negócio do projeto (ex. o 409 de nome duplicado já tratado em
  Tag/Cartão), nenhum componente novo de erro.
- **Nomenclatura de hooks**: `useExcluirConta`/`useExcluirCategoria`/`useExcluirTag`/
  `useExcluirCartao` (mutação nova, ao lado de `useDesativarX` já existente) chamando
  `DELETE /{entidade}/{id}/permanente` — invalidam a mesma `queryKey` que `useDesativarX` já
  invalida hoje.
- **`CartaoFormDialog`/demais `FormDialog`**: sem mudança — exclusão é ação de linha da
  tabela, não uma ação dentro do modal de edição (mesmo padrão de `Desativar` hoje).

## 4. Fora de escopo (explicitamente)

- Estender a checagem de fatura vinculada para o `desativar()` de Cartão (seção 2.4) — mesma
  decisão de não reabrir uma regra que não foi pedida agora.
- Exclusão em lote (`BulkActions` já existe no `DataTable` para outras ações, mas excluir em
  massa é um risco proporcionalmente maior — não pedido, não implementado).
- Qualquer entidade além de Conta/Categoria/Tag/Cartão — as únicas quatro com CRUD de frontend
  hoje. Fatura já tem exclusão real (sem soft delete, seção 0). Quando Transação e as demais
  entidades ganharem frontend, herdam o mesmo padrão desta análise, sem novo documento.

## 5. Ordem de implementação sugerida

1. Backend: `existe_vinculo`/`existe_transacao_vinculada`/`existe_fatura_vinculada` por
   repository + `excluir()` por service + rota `DELETE /{entidade}/{id}/permanente` — as
   quatro entidades, testes unitários e de integração cobrindo bloqueado vs. permitido.
2. Frontend: hooks `useExcluirX` + `RowAction` "Excluir" + `ConfirmAction` com texto por
   entidade, nas quatro páginas.
3. `tsc -b`/`vite build` + smoke test real (criar entidade vazia → excluir com sucesso; criar
   entidade com vínculo → excluir bloqueado com mensagem correta) para as quatro entidades.

## 6. Critérios de pronto

- As quatro entidades ganham "Excluir" como ação de linha, com confirmação específica.
- Backend bloqueia exclusão com 422 e mensagem clara quando há vínculo real (tabela da seção 0
  nunca é violada por um hard delete permitido incorretamente).
- Nenhuma regressão em `Desativar`/`Reativar` existentes.
- Tag pode ser excluída mesmo em uso (por design, seção 2.3), com aviso claro na confirmação.

## 7. Próximos passos

Aguardando aprovação — junto com `docs/analise-arquitetural-rich-pickers.md` e
`docs/analise-arquitetural-fatura-frontend.md` (ainda a redigir), forma o pacote completo da
preparação da Etapa F10. Ordem combinada sugerida: Rich Pickers → Exclusão → CRUD de Fatura
propriamente dito (Exclusão antes de Fatura porque toca as quatro entidades já existentes,
sem depender de nada novo que Fatura introduza).
