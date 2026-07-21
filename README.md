# 💰 Finanças Pessoais

Sistema financeiro pessoal, multi-usuário. Desenvolvimento por etapas.

## 📊 Status

✅ **Etapa 1 concluída:** estrutura inicial do projeto (scaffolding) + Alembic configurado.
✅ **Etapa 2 concluída:** modelo de domínio completo (models SQLAlchemy) + migration inicial.
✅ **Etapa 3 concluída:** arquitetura de camadas (Repository/Service/Schema), injeção de
dependência, tratamento de erros de domínio e estrutura de testes.
✅ **Etapa 4 concluída:** camada completa de autenticação (registro, login, JWT access
token, refresh token com rotation, logout escopado e global, autorização por papel).
🚧 **Etapa 5 em andamento:** CRUD dos módulos de domínio, entidade por entidade, protegido
por autenticação e isolado por usuário. `Conta`, `Categoria`, `Tag`, `Cartão`, `Fatura`,
`Transação`, `Parcelamento`, `Transferência`, `Conta Recorrente`, `Financiamento`,
`Empréstimo`, `Meta` e `Anexo` já implementadas; a única restante (Alerta) segue o mesmo
padrão.
✅ **Etapa 6 concluída:** Central Financeira — camada de orquestração/agregação somente-
leitura sobre os Services de domínio já existentes, a última camada funcional do backend
antes do frontend. 11 endpoints agregadores (`/central-financeira/*`), zero regra de
negócio nova, zero acesso a Repository, zero SQL direto — ver seção dedicada abaixo e
`docs/analise-arquitetural-central-financeira.md`.
🚧 **Etapa 7 em andamento:** frontend (React + TypeScript + Vite + Tailwind), consumindo o
backend exatamente como ele existe hoje. Backend considerado encerrado (exceto correções
pontuais). F1 (fundação: autenticação, roteamento, guarda de rota) concluída; F2 (Design
System — tokens, `motion`, `lucide-react`, fonte Geist self-hosted, componentes base,
Sidebar/Header) concluída, seguindo `docs/design-system.md` e `docs/motion-principles.md`
(documentos congelados). F3 (Dashboard real consumindo os 11 endpoints da Central
Financeira, reordenada para vir antes de Formulários/Tabelas por decisão explícita do
usuário) concluída — ver `docs/analise-arquitetural-dashboard.md`. F4 (infraestrutura
genérica de tabelas — `DataTable` e as 18 peças que a compõem, nenhuma entidade real
ainda) concluída — ver `docs/analise-arquitetural-frontend.md`, seção 13, e
`docs/revisao-tecnica-tabelas.md`. F5 (infraestrutura genérica de formulários — React
Hook Form + Zod, `Form`/`FormDialog` e 27 campos/peças reutilizáveis, nenhuma entidade
real ainda) concluída — ver `docs/analise-arquitetural-frontend.md`, seção 12, e
`docs/revisao-tecnica-formularios.md`. F6 (CRUD de Conta — primeira entidade real,
compondo integralmente os sistemas de Tabela e Formulário das etapas anteriores)
concluída — ver `docs/revisao-tecnica-conta-frontend.md`. Refinamento Visual (branding de
instituições financeiras, tema claro/escuro com toggle no menu do usuário, microinterações
de hover em Button/Card/Table/Sidebar/StatCard) concluído — ver
`docs/revisao-tecnica-branding-e-microinteracoes.md`. F7 (CRUD de Categoria — hierarquia
pai/filho, categorias de sistema somente leitura, dois campos novos do Form System —
`IconField`/`ColorField`) concluída — ver `docs/revisao-tecnica-categoria-frontend.md`.
Refinamento de UI (revisão crítica de UX/UI/Performance/Responsividade sobre tudo que já
existia, sem funcionalidade nova) concluído — ver
`docs/revisao-tecnica-refinamento-ui.md`. F8 (CRUD de Tag — terceira entidade real, sem
hierarquia e sem segunda camada de permissão, primeira etapa 100% composição de
infraestrutura já existente, nenhum componente novo de Form System) concluída — ver
`docs/revisao-tecnica-tag-frontend.md`. Organização da Sidebar (melhoria de UX global —
reordenação por drag-and-drop dos itens de navegação, Dashboard sempre fixo em primeiro,
preferência 100% local via `localStorage`, sem backend) concluída — ver
`docs/revisao-tecnica-organizacao-sidebar.md`. F9+ (CRUD das demais entidades) ainda não
implementadas — ver seção dedicada abaixo.

O projeto é de uso pessoal (um usuário, sem necessidade de escala) — infraestrutura como
CI/CD e observabilidade avançada foi deliberadamente adiada para priorizar entrega de
funcionalidade. Arquitetura limpa, isolamento entre camadas e testes continuam sendo
mantidos em todas as etapas.

## 🏗️ Arquitetura

```
1Financas-app/
├── backend/                        # API — FastAPI + SQLAlchemy + SQLite + Alembic
│   ├── alembic/
│   │   ├── env.py                  # conecta o Alembic ao Base.metadata e à URL do banco
│   │   └── versions/                # migrations, uma por mudança de schema
│   ├── app/
│   │   ├── main.py                 # monta o app, CORS e os exception handlers globais
│   │   ├── core/
│   │   │   ├── config.py           # configurações via variáveis de ambiente (inclui JWT/expiração)
│   │   │   ├── exceptions.py       # exceções de domínio (inclui NaoAutenticadoError/AcessoNegadoError)
│   │   │   ├── security.py         # ÚNICO módulo que toca bcrypt/JWT diretamente
│   │   │   ├── datas.py            # proximo_mes/dia_valido — compartilhado por Fatura, Parcelamento, Conta Recorrente, Financiamento e Emprestimo
│   │   │   ├── amortizacao.py      # gerar_cronograma() PRICE/SAC — compartilhado por Financiamento e Emprestimo
│   │   │   └── logging_config.py   # configuração central de logging
│   │   ├── db/
│   │   │   ├── base.py             # Base declarativa do SQLAlchemy
│   │   │   └── session.py          # engine + sessão por request (unidade de trabalho)
│   │   ├── models/                 # ENTIDADES DO DOMÍNIO — ver README anterior / seção abaixo
│   │   ├── repositories/
│   │   │   ├── base.py             # IRepository (Protocol) + SQLAlchemyRepository genérico
│   │   │   ├── usuario_repository.py
│   │   │   ├── sessao_usuario_repository.py
│   │   │   ├── conta_repository.py     # + agregações de saldo (soma Transacao/Transferencia)
│   │   │   ├── categoria_repository.py # + visibilidade (sistema/próprias) e checagem de subcategoria
│   │   │   ├── tag_repository.py       # + busca por nome (unicidade por usuário)
│   │   │   ├── cartao_repository.py    # + busca por nome e soma de gastos nao pagos (limite_disponivel)
│   │   │   ├── fatura_repository.py    # + soma de compras/pagamentos do ciclo (valor_total/valor_pago)
│   │   │   ├── transacao_repository.py # CRUD + listagem filtrada (conta/cartao/categoria/parcelamento/tipo/data)
│   │   │   ├── parcelamento_repository.py # CRUD + listar_do_usuario (apenas_ativos)
│   │   │   ├── transferencia_repository.py # CRUD + listar_do_usuario (apenas_ativas)
│   │   │   ├── conta_recorrente_repository.py # CRUD + listar_do_usuario (apenas_ativas)
│   │   │   ├── financiamento_repository.py # CRUD + listar_do_usuario (apenas_ativos = status != QUITADO)
│   │   │   ├── emprestimo_repository.py # CRUD + listar_do_usuario (apenas_ativos = status != QUITADO)
│   │   │   ├── meta_repository.py  # CRUD + listar_do_usuario + buscar_por_descricao + somar_transacoes_pagas
│   │   │   └── anexo_repository.py # CRUD + listar_por_transacao
│   │   ├── services/
│   │   │   ├── __init__.py         # convenção dos Services (sem base genérica, ver abaixo)
│   │   │   ├── auth_service.py       # registro, login, refresh (com rotation), logout
│   │   │   ├── conta_service.py      # CRUD + calculo de saldo_atual + isolamento por usuario
│   │   │   ├── categoria_service.py  # CRUD + hierarquia (pai/filho, sem ciclo) + visibilidade sistema/proprio
│   │   │   ├── tag_service.py        # CRUD + reativação por nome (soft delete x unicidade)
│   │   │   ├── cartao_service.py     # CRUD + calculo de limite_disponivel + validacao cruzada com Conta
│   │   │   ├── fatura_service.py     # CRUD + status/valor_total derivados + fechar/pagamento + resolver_fatura_aberta
│   │   │   ├── transacao_service.py  # CRUD + validacao estrutural + resolucao de fatura + imutabilidade
│   │   │   ├── parcelamento_service.py # CRUD + geracao eager de parcelas + divisao de valor + cancelamento parcial
│   │   │   ├── transferencia_service.py # CRUD + validacao cruzada de contas + cancelamento (soft delete)
│   │   │   ├── conta_recorrente_service.py # CRUD + geracao lazy de ocorrencias (MENSAL) + sincronizacao + desativacao
│   │   │   ├── financiamento_service.py # CRUD + cronograma de amortizacao PRICE/SAC + pagamento de parcela + saldo_devedor
│   │   │   ├── emprestimo_service.py # CRUD + desembolso (RECEITA avulsa) + cronograma compartilhado + pagamento de parcela + saldo_devedor
│   │   │   ├── meta_service.py     # CRUD + cofrinho automatico (Conta oculta) + valor_acumulado = legado (meta_id) + Transferencia
│   │   │   ├── anexo_service.py    # CRUD, posse SEMPRE transitiva via TransacaoService.obter()
│   │   │   └── central_financeira_service.py # SEM Repository proprio — so orquestra os 8 Services de dominio acima
│   │   ├── schemas/
│   │   │   ├── base.py             # OrmBaseModel — base dos schemas Pydantic
│   │   │   ├── auth.py             # UsuarioCreate, LoginRequest, TokenResponse...
│   │   │   ├── conta.py            # ContaCreate, ContaUpdate, ContaRead
│   │   │   ├── categoria.py        # CategoriaCreate, CategoriaUpdate, CategoriaRead
│   │   │   ├── tag.py              # TagCreate, TagUpdate, TagRead
│   │   │   ├── cartao.py           # CartaoCreate, CartaoUpdate, CartaoRead
│   │   │   ├── fatura.py           # FaturaCreate, FaturaPagamentoCreate, FaturaRead
│   │   │   ├── transacao.py        # TransacaoCreate, TransacaoUpdate, TransacaoRead
│   │   │   ├── parcelamento.py     # ParcelamentoCreate, ParcelamentoRead (sem Update)
│   │   │   ├── transferencia.py    # TransferenciaCreate, TransferenciaRead (sem Update)
│   │   │   ├── conta_recorrente.py # ContaRecorrenteCreate, ContaRecorrenteUpdate, ContaRecorrenteRead
│   │   │   ├── financiamento.py    # FinanciamentoCreate, FinanciamentoRead (sem Update)
│   │   │   ├── emprestimo.py       # EmprestimoCreate, EmprestimoRead (sem Update)
│   │   │   ├── meta.py             # MetaCreate, MetaUpdate, MetaRead (com valor_acumulado/percentual)
│   │   │   ├── anexo.py            # AnexoCreate, AnexoRead (sem AnexoUpdate - sem PATCH)
│   │   │   └── central_financeira.py # so *Read (11 Outputs) — camada 100% somente-leitura
│   │   └── api/
│   │       ├── deps.py             # DI + get_current_user() + exigir_papel()
│   │       └── routes/
│   │           ├── health.py
│   │           ├── auth.py         # /auth/registrar, /login, /refresh, /logout, /logout-todas, /me
│   │           ├── conta.py        # /contas (CRUD completo, protegido, isolado por usuario)
│   │           ├── categoria.py    # /categorias (CRUD, sistema x proprias, hierarquia)
│   │           ├── tag.py          # /tags (CRUD completo, protegido, isolado por usuario)
│   │           ├── cartao.py       # /cartoes (CRUD completo, validacao cruzada com Conta)
│   │           ├── fatura.py       # /faturas (criar/obter/listar/fechar/pagamentos/excluir)
│   │           ├── transacao.py    # /transacoes (CRUD completo, conta_id/cartao_id imutaveis)
│   │           ├── parcelamento.py # /parcelamentos (criar/obter/listar/cancelar, sem PATCH/DELETE)
│   │           ├── transferencia.py # /transferencias (criar/obter/listar/cancelar, sem PATCH/DELETE)
│   │           ├── conta_recorrente.py # /contas-recorrentes (CRUD + gerar-ocorrencias-pendentes + DELETE soft)
│   │           ├── financiamento.py # /financiamentos (criar/obter/listar + parcelas/{numero}/pagar, sem PATCH/DELETE)
│   │           ├── emprestimo.py   # /emprestimos (criar/obter/listar + parcelas/{numero}/pagar, sem PATCH/DELETE)
│   │           ├── meta.py         # /metas (CRUD completo, com PATCH e DELETE)
│   │           ├── anexo.py        # /anexos (criar/obter/listar/excluir, sem PATCH)
│   │           └── central_financeira.py # /central-financeira/* (11 GETs agregadores, sem POST/PATCH/DELETE)
│   └── tests/
│       ├── unit/                   # Services/Repository testados isolados (com mocks/fakes)
│       └── integration/            # API + banco real (SQLite em memória) ponta a ponta
│
├── frontend/                       # React + Vite + Tailwind
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       └── index.css
│
└── dashboard/                      # painel interno de acompanhamento do projeto (não faz parte do app)
    ├── index.html / style.css / app.js  # HTML/CSS/JS puro, sem build, lê o JSON abaixo
    ├── project-status.json         # ÚNICA fonte de dados do painel — editar aqui para atualizar
    ├── start-dashboard.bat         # duplo clique para abrir (Windows)
    └── README.md                   # como abrir e como atualizar os dados
```

## 🧩 Camadas do backend e responsabilidade de cada uma

O fluxo de uma requisição sempre segue a mesma direção:
**Router → Service → Repository → banco**, e a resposta volta pelo caminho inverso. Cada
seta só conhece a camada imediatamente abaixo dela — um Router nunca fala com um
Repository diretamente, por exemplo.

**Router** (`app/api/routes/`) — só sabe de HTTP. Recebe a requisição, valida o corpo
contra um Schema (Pydantic), chama exatamente um método do Service correspondente e
devolve o resultado. Nunca contém `if` de regra de negócio, nunca monta uma query, nunca
tem `try/except` (as exceções de domínio são traduzidas em respostas HTTP por handlers
globais registrados em `main.py` — ver `app/core/exceptions.py`).

**Schema** (`app/schemas/`) — define o formato de entrada e saída de cada endpoint
(`ContaCreate`, `ContaRead`, etc.), usando Pydantic. Não é o mesmo que um Model do
SQLAlchemy: o Schema descreve um payload HTTP, o Model descreve uma tabela. Um schema de
leitura herda de `OrmBaseModel` para poder ser construído direto a partir de um objeto
retornado pelo Repository.

**Service** (`app/services/`) — toda regra de negócio mora aqui: validações que dependem
de estado, cálculos, orquestração de mais de um Repository numa única operação, e decisão
de quando levantar uma exceção de domínio. Um Service recebe seus Repositories por
injeção no construtor e nunca importa nada de FastAPI — ele não sabe (nem precisa saber)
que está sendo servido via REST. Diferente do Repository, não existe uma classe base
genérica para Service: regra de negócio não se repete de forma padronizada entre
entidades do jeito que get/list/create/delete se repetem, então cada Service declara
explicitamente do que precisa (motivo detalhado no docstring de `app/services/__init__.py`).

**Repository** (`app/repositories/`) — a única camada que conhece SQLAlchemy/SQL.
Traduz "buscar", "listar", "salvar", "remover" em queries. `SQLAlchemyRepository` (em
`base.py`) já implementa essas operações genericamente; cada entidade ganha seu próprio
Repository herdando dela e adicionando buscas específicas quando precisar. Repository
nunca decide *quando* confirmar uma transação (`commit`) — só dá `flush` (envia o SQL,
sem fechar a transação). Quem commita é a sessão do request inteiro.

**Unit of Work implícita** (`app/db/session.py`) — a função `get_db()` abre uma sessão no
início do request, e essa MESMA sessão é compartilhada por todos os Repositories usados
por um Service durante aquele request. `get_db()` só dá `commit()` se o request inteiro
terminar sem exceção; qualquer erro (de domínio ou não) causa `rollback()` de tudo. Isso
garante atomicidade em operações que mexem em mais de uma tabela (ex: `Transferencia`
debitando uma conta e creditando outra) sem precisar de uma classe `UnitOfWork` separada
— o escopo do request já cumpre esse papel neste projeto.

**Exceções de domínio** (`app/core/exceptions.py`) — `NotFoundError`, `BusinessRuleError`
e `ConflictError` são levantadas pelos Services. `app/main.py` registra um handler para
cada uma, traduzindo para HTTP 404, 422 e 409 respectivamente. Isso é o que permite os
Routers nunca precisarem de `try/except`.

### Por que Repository tem uma base genérica e Service não

`SQLAlchemyRepository[ModelType]` cobre `get/list/create/update/delete` porque essas
operações são *mecanicamente* idênticas para qualquer entidade — só muda o `model`.
Regra de negócio não tem essa propriedade: o que o `TransferenciaService` precisa
verificar (contas diferentes, saldo suficiente) não tem nada a ver com o que o
`MetaService` precisa (data alvo no futuro, valor positivo). Forçar os dois a herdar de
uma base comum obrigaria essa base a saber sobre casos que não são dela — violaria o
Interface Segregation Principle. Em vez disso, cada Service declara seus próprios
Repositories no construtor (injeção explícita de dependência).

## 🗂️ Modelo de domínio

Sistema multi-usuário: toda entidade abaixo (exceto `Categoria` global) pertence a um
`Usuario` via `usuario_id` — direto na maioria dos casos, transitivo em `Fatura` (via
`Fatura.cartao.usuario_id`, primeira entidade sem coluna `usuario_id` própria). Isolamento
entre usuários é garantido filtrando por esse campo na camada de Service (implementado para
`Conta`, `Categoria`, `Tag`, `Cartão`, `Fatura` e `Transação`; as demais entidades seguem o
mesmo padrão à medida que ganham CRUD — ver seções de CRUD abaixo). `Categoria` é a única
exceção parcial: além das próprias, todo usuário também enxerga as categorias globais do
sistema (`usuario_id` nulo), somente leitura.

**Transacao** é o centro do sistema — toda entrada ou saída real de dinheiro (o campo
`tipo` distingue RECEITA de DESPESA, em vez de duas tabelas separadas). As demais
entidades não duplicam dado financeiro: elas geram, agrupam ou dão contexto a transações.

| Entidade | Responsabilidade |
|---|---|
| `Usuario` | Dono de todos os dados. |
| `Conta` | Onde o dinheiro fica (corrente, poupança, carteira, investimento). Saldo é sempre calculado, nunca armazenado. |
| `Cartao` | Cartão de crédito: tem limite, não tem saldo. Aponta para a `Conta` que paga a fatura. |
| `Fatura` | Um ciclo de fechamento do cartão (mês de referência, status ABERTA→FECHADA→PAGA/ATRASADA). Permite alertas de vencimento e reconciliação de pagamento. |
| `Categoria` | Classificação hierárquica (subcategorias via auto-relacionamento). `usuario_id` nulo = categoria padrão do sistema. |
| `Tag` | Classificação livre e complementar à Categoria, N-N com `Transacao` via `transacao_tag`. |
| `Transacao` | Todo lançamento real de caixa. Pertence a uma `Conta` OU a um `Cartao` (nunca os dois — `CHECK` constraint no banco). Pertence a no máximo um `Parcelamento`/`Financiamento`/`Emprestimo`, e `numero_parcela` só existe quando um desses três está preenchido (dois outros `CHECK`s). Sem soft delete — lançamento incorreto é removido de verdade, não desativado. |
| `Parcelamento` | Compra dividida em parcelas (cartão ou lojista), sem ser um contrato de crédito formal. Cada parcela concreta é uma `Transacao`. |
| `Financiamento` | Contrato de crédito atrelado a um bem (imóvel, veículo), com instituição financeira, CET, sistema de amortização (PRICE/SAC) e saldo devedor. O valor financiado normalmente não passa pela conta do usuário — só a entrada (se houver) e as parcelas mensais geram `Transacao`. |
| `Emprestimo` | Contrato de crédito de propósito geral (pessoal, consignado). Mesma estrutura de `Financiamento` (via `ContratoCreditoMixin`), mas `valor_liberado` é obrigatório e SEMPRE gera uma `Transacao` de RECEITA (desembolso) na conta do usuário — diferente da entrada opcional de `Financiamento`. |
| `ContaRecorrente` | Template de lançamento periódico (aluguel, salário, assinatura). Gera `Transacao` a cada ocorrência, sob demanda (lazy, nunca por scheduler). Nesta etapa, só `MENSAL` é suportada. |
| `Transferencia` | Movimentação entre duas `Conta` do mesmo usuário. Fica fora de `Transacao` DE PROPÓSITO (decisão reafirmada explicitamente no CRUD desta entidade, ver `docs/revisao-tecnica-transferencia.md`) — não é receita nem despesa. É, ela mesma, a fonte de verdade do próprio efeito em saldo; `ativo` permite cancelar preservando histórico. |
| `Meta` | Objetivo de economia (valor alvo, prazo opcional). `conta_id` é obrigatório e SEMPRE automático — um "cofrinho" (`Conta` oculta) criado por `MetaService.criar()`, nunca escolhido pelo usuário. `valor_acumulado`/`percentual` nunca são armazenados — somam o histórico legado (`Transacao.meta_id`, congelado, só leitura) com o saldo do cofrinho (`Transferencia` real, aporte/resgate). Aportes/resgates novos são sempre `Transferencia` para o cofrinho, nunca `Transacao` (ver `docs/analise-arquitetural-metas-transferencias.md`). Nome único por usuário (mesmo padrão de `Tag`/`Cartao`), soft delete via `ativo`. |
| `Alerta` | Regra de notificação. Referencia qualquer entidade via `entidade_tipo` + `entidade_id` (polimórfico, sem FK real). |
| `Anexo` | Arquivo anexado a uma `Transacao` (comprovante, nota fiscal). Pertence SEMPRE a uma `Transacao`, nunca diretamente ao usuário — posse transitiva, validada reaproveitando `TransacaoService`. Redesenhado nesta etapa a partir do desenho especulativo original (polimórfico, via `entidade_tipo`/`entidade_id`, mesma estratégia de `Alerta`) — decisão registrada em `docs/analise-arquitetural-anexo.md`. Só guarda metadados (nome, caminho, mime type, tamanho, data de upload); o arquivo em si fica fora do banco. `ondelete=CASCADE`: some junto quando a `Transacao` é excluída (hard delete). Soft delete via `ativo`, sem `PATCH`. |

Detalhe técnico relevante: `Fatura` e `Transacao` se referenciam duas vezes, mas sempre na
MESMA direção (`Transacao → Fatura`), sem dependência cíclica entre as tabelas.
`Transacao.fatura_id` marca uma transação como COMPRA de um ciclo; `Transacao.fatura_paga_id`
marca uma transação como PAGAMENTO (total ou parcial) de um ciclo — um `CHECK constraint`
garante que nunca são preenchidos ao mesmo tempo na mesma linha. (Um desenho anterior usava
`Fatura.transacao_pagamento_id`, FK singular apontando de volta para `Transacao`, o que
exigia `use_alter=True` por causa do ciclo resultante — substituído durante a implementação
do CRUD de Fatura, ver `docs/analise-arquitetural-fatura.md`.)

`Financiamento` e `Emprestimo` têm a mesma "forma" de contrato (instituição financeira,
número de contrato, taxa de juros, sistema de amortização, CET, saldo devedor, permite
quitação antecipada) mas são tabelas separadas, não uma só com um campo `tipo`: elas têm
relação diferente com `Transacao` (empréstimo gera uma transação de entrada no
desembolso, financiamento normalmente não) e tendem a ganhar regras próprias no futuro
(ex: margem consignável só existe em empréstimo consignado). Os campos comuns vêm de
`ContratoCreditoMixin` (`app/models/mixins.py`), evitando duplicar a definição de coluna
sem forçar as duas entidades a compartilhar Service. `saldo_devedor` é a única exceção ao
padrão "nunca guardar valor calculado" (usado em `Conta`/`Meta`): com PRICE/SAC ele não é
uma soma simples, então fica armazenado e é atualizado pelo Service a cada parcela paga.

## 🔐 Autenticação

Camada completa de autenticação, obrigatória antes de qualquer CRUD de domínio. Segue
`Router → Service → Repository` como o resto do projeto — nenhuma regra de autenticação
mora fora de `AuthService`/`app/core/security.py`.

**Fluxo de tokens.** Login devolve dois tokens com naturezas diferentes de propósito:

- **Access token**: JWT (HS256) auto-contido, vida curta (`ACCESS_TOKEN_EXPIRE_MINUTES =
  15`). Vai no header `Authorization: Bearer <token>` de toda requisição protegida.
  Nenhuma consulta ao banco é necessária para validá-lo — só decodificar e checar
  assinatura/expiração.
- **Refresh token**: segredo opaco (não é um JWT), vida longa
  (`REFRESH_TOKEN_EXPIRE_DAYS = 30`). É armazenado com hash SHA-256 (nunca em texto
  puro) na tabela `sessoes_usuario`, uma linha por sessão/dispositivo logado — é o que
  permite múltiplas sessões simultâneas (notebook + celular) e revogação real: como o
  access token JWT não pode ser "invalidado" antes de expirar, todo controle de
  logout/revogação acontece no refresh token, que depende inteiramente do banco para ser
  válido.

**Rotation.** Cada uso de `/auth/refresh` revoga a sessão usada e cria uma nova — um
refresh token só pode ser usado uma vez. Isso limita a janela de exploração caso um
token seja roubado.

**Logout escopado vs. global.** `POST /auth/logout` encerra só a sessão do refresh token
informado (outros dispositivos continuam logados). `POST /auth/logout-todas` chama
`SessaoUsuarioRepository.revogar_todas_do_usuario` e encerra todas as sessões do usuário
autenticado de uma vez (ex: "saí de todos os dispositivos").

**Senhas.** Hash com bcrypt (fator de custo 12), nunca `passlib` (histórico de problemas
de manutenção/compatibilidade com bcrypt novo). Bcrypt trunca silenciosamente entradas
acima de 72 bytes — por isso `UsuarioCreate.senha` já limita `max_length=72` no Schema, e
`security.py` valida de novo antes do hash (`SenhaMuitoLongaError`), para nunca depender
só da validação de borda do Pydantic.

**Prevenção de enumeração de usuário.** Login com email inexistente e login com senha
errada devolvem exatamente a mesma mensagem e status (`401`) — um atacante não consegue
descobrir quais emails têm conta testando o endpoint.

**`get_current_user()` é o único ponto de decodificação de JWT** fora de
`security.py`/`AuthService`. Nenhum outro Service ou Router chama `decodificar_access_token`
diretamente — protegida com `Depends(get_current_user)`/`CurrentUser`
(`app/api/deps.py`), essa é a única forma de obter o usuário autenticado em qualquer
endpoint futuro.

**Autorização por papel.** `Usuario.papel` (enum `TipoPapel`, hoje só `USER`) e a
dependency `exigir_papel(*papeis)` já existem prontos para quando houver um segundo
papel (ex: `ADMIN`) — nenhuma mudança estrutural será necessária, só popular o enum e
anotar as rotas.

**Preparado, mas não implementado nesta etapa** (arquitetura pronta para evoluir sem
retrabalho):
- *Rotação de chave JWT*: `JWT_KEY_ID` (claim `kid`) e a resolução de chave centralizada
  em uma única função (`_chave_assinatura()`, em `security.py`) já isolam o ponto exato
  onde uma segunda chave entraria em uso.
- *Rate limiting*: comentários `# TODO(rate-limit)` marcam os pontos exatos de injeção de
  dependência em `/auth/login` e `/auth/refresh` (os endpoints mais sensíveis a
  força bruta/credential stuffing).

**Logging.** Eventos de autenticação são logados via `logging` (nunca senha, token
completo ou outro dado sensível — só identificadores seguros como `usuario_id`,
`sessao_id`, `email`, `ip`, `jti`): login bem-sucedido, login inválido, refresh
realizado, logout, logout global, tentativa de acesso não autenticado.

**Configuração obrigatória.** `SECRET_KEY` não tem valor padrão — a aplicação falha ao
subir (erro de validação do Pydantic Settings) se a variável de ambiente não estiver
definida. Gere uma com `python -c "import secrets; print(secrets.token_urlsafe(32))"` e
coloque no seu `.env` (nunca reaproveite o valor de exemplo do `.env.example`).

## 🏦 CRUD de Conta (primeira entidade de domínio)

Primeiro CRUD implementado sobre o padrão `Router → Service → Repository`, servindo de
modelo para as próximas entidades. Todas as rotas exigem autenticação
(`Depends(get_current_user)`) e só enxergam dados do usuário autenticado.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/contas` | Cria uma conta para o usuário autenticado. |
| 🔵 GET | `/contas` | Lista as contas do usuário (`apenas_ativas` por padrão `true`, `skip`/`limit`). |
| 🔵 GET | `/contas/{id}` | Obtém uma conta (com `saldo_atual` calculado). |
| 🟡 PATCH | `/contas/{id}` | Atualiza campos parcialmente (só o que for enviado no corpo). |
| 🔴 DELETE | `/contas/{id}` | Desativa a conta (soft delete — ver abaixo). |

**Saldo nunca é armazenado, sempre calculado** (ver `Conta.saldo_inicial` no model):
`saldo_atual = saldo_inicial + Σ(Transacao PAGA da conta) + Σ(Transferencia líquida da
conta)`. Transação com status `PENDENTE` não entra na soma — ainda não é dinheiro que
efetivamente mudou de mãos. `ContaService._com_saldo()` monta esse valor e o anexa como
atributo transiente ao objeto `Conta` antes de devolvê-lo ao Router (nunca é persistido).
`ContaRepository` expõe as agregações (`somar_transacoes_pagas`, `somar_transferencias`)
como consultas puras; a fórmula em si é regra de negócio e mora no Service. Decisão sobre
performance dessa agregação em volume (por que `SUM` real-time é definitivo, não
provisório, e qual o gatilho real para revisitar) documentada em
`docs/decisao-performance-saldo.md`.

**Isolamento multi-tenant como 404, nunca 403.** Se uma conta não existe OU pertence a
outro usuário, a resposta é idêntica: `NotFoundError` → HTTP 404. Distinguir os dois
casos (ex: 403 para "existe mas não é sua") permitiria a um usuário autenticado descobrir,
testando IDs sequenciais, quantas contas outros usuários têm — Broken Object Level
Authorization, OWASP API Security Top 10. Mesmo raciocínio já aplicado em
`AuthService.autenticar` (mensagem idêntica para e-mail inexistente e senha errada).

**Exclusão é soft delete.** `DELETE /contas/{id}` marca `ativo=false` em vez de apagar a
linha — `Transacao.conta_id` tem `ondelete="CASCADE"`, e um DELETE físico apagaria junto
todo o histórico financeiro ligado àquela conta, o que não é o comportamento esperado de
um sistema financeiro. A listagem padrão (`GET /contas`) só mostra contas ativas;
`?apenas_ativas=false` inclui as desativadas.

## 🏷️ CRUD de Categoria

Segunda entidade de domínio, sobre o mesmo padrão `Router → Service → Repository`. Mais
complexa que `Conta` por ter três níveis de visibilidade e uma hierarquia auto-referente.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/categorias` | Cria uma categoria para o usuário autenticado. |
| 🔵 GET | `/categorias` | Lista categorias visíveis (sistema + próprias; `apenas_ativas`, `skip`/`limit`). |
| 🔵 GET | `/categorias/{id}` | Obtém uma categoria (sistema ou própria). |
| 🟡 PATCH | `/categorias/{id}` | Atualiza campos parcialmente (nunca em categoria do sistema). |
| 🔴 DELETE | `/categorias/{id}` | Desativa a categoria (soft delete, bloqueado se houver subcategoria ativa). |

**Visibilidade em três níveis, não dois.** Categoria do sistema (`usuario_id` nulo) é
pública — todo usuário autenticado a lê e lista, mas ninguém edita. Categoria de outro
usuário é privada — tratada como inexistente (404), mesmo raciocínio anti-BOLA do
`Conta`. Categoria própria — leitura e escrita liberadas. Isso significa: não encontrada
→ 404, do sistema → 403 explícito ("categorias do sistema são somente leitura"), de
outro usuário → 404. `CategoriaService._buscar_editavel()` constrói sobre
`_buscar_visivel()` para não duplicar a checagem de existência.

**Hierarquia sem ciclos.** `categoria_pai_id` é validado em duas frentes: (1) a
categoria pai proposta precisa ser do sistema ou do mesmo usuário — reusa a mesma
checagem de visibilidade, então apontar para uma categoria privada de outro usuário
recebe a mesma resposta (404) de qualquer outro acesso indevido; (2) o novo vínculo não
pode criar um ciclo — `_cria_ciclo()` sobe a cadeia de ancestrais a partir do pai
proposto e recusa (`BusinessRuleError` → 422) se a própria categoria aparecer nessa
cadeia. Auto-referência (pai = si mesma) é o caso trivial desse mesmo mecanismo, com
mensagem própria por clareza.

**A regra "não excluir com subcategoria ativa" vale nos dois caminhos que produzem o
mesmo efeito.** `DELETE /categorias/{id}` e `PATCH /categorias/{id} {"ativo": false}`
resultam no mesmo estado final — por isso os dois passam pela mesma checagem
(`_impedir_desativacao_com_subcategoria_ativa`), evitando que a regra seja contornada só
trocando de verbo HTTP (achado da revisão técnica, ver `docs/revisao-tecnica-categoria.md`).

**Preparado, mas não implementado nesta etapa:** bloqueio de exclusão de categoria em uso
por `Transacao` — marcado com `# TODO(categoria-em-uso)` no ponto exato em
`CategoriaService.desativar()`, para quando esse CRUD existir.

## 🔖 CRUD de Tag

Terceira entidade de domínio, sobre o mesmo padrão `Router → Service → Repository`. A
mais simples das três em modelagem (sem hierarquia, sem valor calculado), mas com uma
sutileza própria: nome único por usuário precisa conviver com soft delete.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/tags` | Cria uma tag para o usuário autenticado (ou reativa uma inativa com o mesmo nome). |
| 🔵 GET | `/tags` | Lista as tags do usuário (`apenas_ativas` por padrão `true`, `skip`/`limit`). |
| 🔵 GET | `/tags/{id}` | Obtém uma tag própria. |
| 🟡 PATCH | `/tags/{id}` | Atualiza campos parcialmente (renomear, recolorir, reativar/desativar). |
| 🔴 DELETE | `/tags/{id}` | Desativa a tag (soft delete). |

**Reativar em vez de bloquear no nome.** A `UniqueConstraint(usuario_id, nome)` não
distingue tag ativa de desativada — sem tratamento especial, apagar uma tag "queimaria"
seu nome permanentemente. Por isso `TagService.criar()` verifica se já existe uma tag
inativa com o nome pedido e, se existir, reativa essa linha em vez de inserir uma nova
(o payload é aplicado por completo, então a cor antiga é substituída se não for reenviada
— semântica de criação, não de "restaurar como estava"). Renomear uma tag (`PATCH`) para
o nome de uma tag inativa **não** aciona essa fusão — é tratado como conflito comum
(`409`), porque mesclar identidades implicitamente ao renomear seria uma decisão grande
demais para ser automática. `PATCH {"ativo": true}` reativa uma tag diretamente por id,
como caminho alternativo à reativação por nome. Detalhamento completo em
`docs/revisao-tecnica-tag.md`.

**Isolamento binário, mesmo padrão de Conta.** Tag não tem conceito de recurso do
sistema — não encontrada e de outro usuário levam à mesma resposta (404).

A tabela de associação N:N com `Transacao` (`transacao_tag`) está em uso desde o CRUD de
Transação — ver seção própria abaixo.

## 💳 CRUD de Cartão

Quarta entidade de domínio, sobre o mesmo padrão `Router → Service → Repository`. Primeira
a introduzir uma validação cruzada entre Services: `conta_pagamento_id` precisa apontar
para uma `Conta` do mesmo usuário.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/cartoes` | Cria um cartão para o usuário autenticado (ou reativa um inativo com o mesmo nome). |
| 🔵 GET | `/cartoes` | Lista os cartões do usuário (`apenas_ativos` por padrão `true`, `skip`/`limit`). |
| 🔵 GET | `/cartoes/{id}` | Obtém um cartão (com `limite_disponivel` calculado). |
| 🟡 PATCH | `/cartoes/{id}` | Atualiza campos parcialmente (inclusive trocar a conta de pagamento). |
| 🔴 DELETE | `/cartoes/{id}` | Desativa o cartão (soft delete). |

**Validação cruzada: `conta_pagamento_id` precisa ser do mesmo usuário.** Primeira vez no
projeto em que um Service valida posse de uma entidade diferente da que ele gerencia —
`CartaoService` recebe `ContaRepository` por injeção (além do seu próprio
`CartaoRepository`) só para essa checagem. Mesma resposta 404 uniforme para "conta não
existe" e "conta é de outro usuário" (anti-enumeração, mesmo padrão de sempre).

**Nome único + soft delete: mesmo mecanismo de `Tag`, reaplicado sem modificações.**
Criar um cartão com o nome de um cartão desativado reativa a linha existente; renomear
(PATCH) para esse mesmo nome bloqueia com 409 em vez de mesclar. Raciocínio completo já
documentado em `docs/revisao-tecnica-tag.md` — não precisou ser redescoberto para Cartão.

**`limite_disponivel` calculado, nunca armazenado** — mesmo princípio de `Conta.saldo_atual`:
`limite - Σ(despesas do cartão cuja fatura ainda não foi paga)`. Como `Transacao` ainda não
tem CRUD próprio nem geração automática de fatura, a query já é real (roda sobre `Fatura`
de verdade, criada manualmente via `/faturas`), mas só reflete transações inseridas por fora
do CRUD — decisão definitiva (real-time SQL), não provisória, mesmo raciocínio de
`docs/decisao-performance-saldo.md`. Pode ficar negativo (cartão estourado): não é limitado
em zero, de propósito.

Detalhamento completo (incluindo os itens deferidos, como a checagem de "cartão em uso"
antes de desativar) em `docs/revisao-tecnica-cartao.md`.

**Fora de escopo nesta etapa, por pedido explícito:** geração automática de fatura (agora
implementada manualmente — ver seção seguinte).

## 🧾 CRUD de Fatura

Quinta entidade de domínio. Análise arquitetural completa validada antes da implementação
em `docs/analise-arquitetural-fatura.md`; detalhamento técnico da implementação em
`docs/revisao-tecnica-fatura.md`. Primeira entidade sem `PATCH` genérico e sem
`usuario_id` próprio (posse sempre transitiva via `Cartão`).

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/faturas` | Cria um ciclo (`cartao_id` + `mes_referencia`) — datas derivadas do Cartão. |
| 🔵 GET | `/faturas?cartao_id=X` | Lista as faturas de um cartão (mais recente primeiro). |
| 🔵 GET | `/faturas/{id}` | Obtém uma fatura, com `valor_total`/`status`/`valor_pago` calculados. |
| 🟢 POST | `/faturas/{id}/fechar` | Fecha o ciclo (`ABERTA → FECHADA`), congelando `valor_total`. |
| 🟢 POST | `/faturas/{id}/pagamentos` | Registra um pagamento (total ou parcial) de uma fatura fechada. |
| 🔴 DELETE | `/faturas/{id}` | Exclui (hard delete) uma fatura ainda `ABERTA` e sem transações vinculadas. |

**`status`/`valor_total` derivados, sem tocar a coluna real.** Só `ABERTA`/`FECHADA` são
gravados de verdade; `PARCIALMENTE_PAGA`/`PAGA`/`ATRASADA` são calculados a cada leitura a
partir de `valor_pago`/`valor_total`/`data_vencimento` — nunca persistidos. Para evitar o
risco de sobrescrever a coluna real do SQLAlchemy (e commitar um valor que nunca deveria ir
ao banco), os valores derivados são anexados sob nomes diferentes (`status_calculado`,
`valor_total_calculado`) e expostos na API via `Field(validation_alias=...)` no Schema.

**Pagamento parcial via FK invertida.** `Fatura.transacao_pagamento_id` (FK singular) foi
substituído por `Transacao.fatura_paga_id` — várias transações de pagamento podem apontar
para a mesma fatura, e de quebra elimina a dependência cíclica que antes exigia
`use_alter=True` entre `Fatura` e `Transacao`.

**Sem `PATCH` genérico, de propósito.** Datas e `cartao_id` são imutáveis (derivados na
criação); as transições de estado válidas são ações de negócio explícitas
(`POST .../fechar`, `POST .../pagamentos`), não edição de campo livre.

**Sem soft delete.** Fatura é um registro histórico de ciclo, não um cadastro que se
desativa. Exclusão (hard delete) só é permitida para desfazer uma criação por engano —
`ABERTA` e sem nenhuma transação vinculada.

**Fora de escopo nesta etapa, por pedido explícito:** geração/resolução automática do
próximo ciclo por data (implementada agora, ver seção seguinte), e qualquer integração
automática com `Parcelamento`/`Financiamento` (ainda fora de escopo).

## 🔁 CRUD de Transação

Sexta entidade de domínio, e a de maior fan-out do sistema — praticamente todo cálculo
financeiro (`saldo_atual`, `limite_disponivel`, `valor_total`/`valor_pago` de Fatura) já
dependia dela mesmo sem ela ter CRUD próprio. Análise arquitetural completa validada antes
da implementação em `docs/analise-arquitetural-transacao.md` (relação com as 11 entidades
do domínio); detalhamento técnico da implementação em `docs/revisao-tecnica-transacao.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/transacoes` | Cria uma transação de conta OU de cartão (nunca as duas). |
| 🔵 GET | `/transacoes` | Lista as transações do usuário (filtros opcionais: `conta_id`, `cartao_id`, `categoria_id`, `parcelamento_id`, `tipo`, `data_inicio`, `data_fim`). |
| 🔵 GET | `/transacoes/{id}` | Obtém uma transação. |
| 🟡 PATCH | `/transacoes/{id}` | Atualiza campos parcialmente (`conta_id`/`cartao_id` são imutáveis). |
| 🔴 DELETE | `/transacoes/{id}` | Exclui a transação (hard delete — sem soft delete, ver abaixo). |

**Resolução automática de fatura, finalmente implementada.** Toda transação de cartão
resolve `fatura_id` internamente via `FaturaService.resolver_fatura_aberta()` (novo método,
find-or-create do ciclo aberto que cobre a data da transação) — nunca aceito do payload do
cliente. Duas compras na mesma janela do ciclo reaproveitam a mesma fatura; uma compra após
o fechamento cai automaticamente no ciclo seguinte, criado sob demanda. `fatura_id` nunca é
gerado em lote/scheduler — cada resolução acontece pontualmente, no momento em que uma
transação de cartão é criada.

**`StatusTransacao` tem dois significados, nunca confundidos.** Para transação de CONTA,
`status` é autoritativo (`PENDENTE`/`PAGO`, editável livremente). Para transação de
CARTÃO, `status` **não é** autoridade sobre pagamento da dívida — essa autoridade é sempre
a `Fatura` — por isso `TransacaoService` força `status = PAGO` na criação e ignora
qualquer valor de `status` enviado num `PATCH` de transação de cartão. Documentado
explicitamente no docstring de `StatusTransacao` (`app/models/enums.py`) para não ser
reintroduzido por engano no futuro.

**Imutabilidade de fatura fechada, cumprida.** Prometida em
`docs/analise-arquitetural-fatura.md` antes deste CRUD existir: `valor`, `data` e
`parcelamento_id` de uma transação de compra (`fatura_id` preenchido) não podem mais ser
alterados, nem a transação excluída, uma vez que a fatura correspondente não está mais
`ABERTA`. Campos descritivos (`categoria_id`, `descricao`, `tags`) continuam livres. Uma
transação de pagamento (`fatura_paga_id`) nunca é travada por essa regra.

**Sem soft delete, de propósito.** Diferente de Conta/Categoria/Tag/Cartão, `Transacao` é
lançamento de livro-razão — um lançamento incorreto é removido de verdade. Única restrição
de exclusão: a imutabilidade de fatura fechada acima.

**Validação de tipo entre Categoria e Transação, resolvida.** `docs/revisao-tecnica-categoria.md`
deixou essa checagem em aberto até haver um caso de uso real; resolvida aqui —
`categoria.tipo` incompatível com o `tipo` da transação (ex: categoria só-DESPESA numa
transação RECEITA) é rejeitado.

**Validação estrutural centralizada só no Service, nunca no Schema.** Conta XOR cartão, no
máximo um contrato (`parcelamento_id`/`financiamento_id`/`emprestimo_id`), e
`numero_parcela` condizente com o contrato — mesma família dos `CheckConstraint`s do banco,
mas validados em `TransacaoService`, não em `TransacaoCreate`/`TransacaoUpdate`: a mesma
regra precisa valer tanto na criação (payload completo) quanto no `PATCH` (payload
parcial), e só o Service enxerga o estado final mesclado nos dois casos.

**Vínculos manuais sem validação de posse, por decisão explícita (YAGNI), no momento em que
este parágrafo foi escrito.** `financiamento_id`, `emprestimo_id`, `meta_id` e
`origem_recorrente_id` eram aceitos e persistidos sem checagem de propriedade cruzada,
porque nenhuma dessas entidades tinha Repository/CRUD próprio ainda. Cada uma ganhou essa
validação quando o próprio CRUD nasceu: `parcelamento_id` SAIU dessa lista desde o CRUD de
Parcelamento (seção seguinte) — valida posse, faixa de `numero_parcela` (1..`num_parcelas`)
e duplicidade, os três achados de `docs/revisao-tecnica-parcelamento.md`;
`origem_recorrente_id` desde o CRUD de Conta Recorrente; `financiamento_id` desde o CRUD de
Financiamento; `emprestimo_id` desde o CRUD de Empréstimo (mesmo padrão de posse + faixa +
duplicidade nos quatro casos). Hoje só `meta_id` permanece na lista, já que `Meta` ainda não
tem CRUD próprio.

## 🧩 CRUD de Parcelamento

Sétima entidade de domínio. Análise arquitetural completa validada antes da implementação
em `docs/analise-arquitetural-parcelamento.md` (relação com Transação/Cartão/Fatura,
geração de parcelas, antecipação, cancelamento); detalhamento técnico da implementação —
incluindo um problema real encontrado e corrigido na revisão — em
`docs/revisao-tecnica-parcelamento.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/parcelamentos` | Cria o cabeçalho e gera, na hora, todas as N parcelas (uma `Transacao` por parcela). |
| 🔵 GET | `/parcelamentos` | Lista os parcelamentos do usuário (filtro opcional `apenas_ativos`, `true` por padrão). |
| 🔵 GET | `/parcelamentos/{id}` | Obtém um parcelamento. |
| 🟢 POST | `/parcelamentos/{id}/cancelar` | Cancelamento parcial: marca `ativo=false` e remove só as parcelas ainda não travadas. |

Sem `PATCH` (campos como `valor_total`, `num_parcelas`, `data_inicio`, `cartao_id`/`conta_id`
são estruturais e imutáveis após a criação) e sem `DELETE` físico (hard delete de um
Parcelamento com parcelas geradas quebraria a `UniqueConstraint` de `numero_parcela` em
`Transacao` — achado da análise arquitetural).

**Geração eager, não lazy.** Diferente da resolução lazy de `Fatura`, todas as N parcelas
(e as Faturas futuras correspondentes, se for um parcelamento de cartão) são criadas de
uma vez, na criação do Parcelamento — uma compra parcelada é um compromisso determinístico
com N lançamentos futuros já conhecidos, diferente de um ciclo mensal que ninguém se
comprometeu a preencher. `ParcelamentoService` nunca constrói uma `Transacao` nem fala com
`TransacaoRepository` para escrever — cada parcela nasce e morre via `TransacaoService`,
mesmo padrão de composição Service→Service já usado por `TransacaoService`→`FaturaService`.

**Divisão de valor sem perda de centavo.** `valor_parcela = round(valor_total / num_parcelas,
2)` para as N-1 primeiras parcelas; a última absorve o resto (positivo ou negativo), para a
soma bater exatamente com `valor_total`.

**Cancelamento é sempre parcial, nunca reescreve histórico.** Reaproveita
`TransacaoService.excluir()` para cada parcela — ignora o `BusinessRuleError` das parcelas
com fatura já fechada (ficam intocadas) e remove as demais. Diferente do "tudo ou nada" de
`FaturaService.excluir()`: um Parcelamento naturalmente acumula histórico ao longo de vários
ciclos, então "cancelar o que falta" é a única semântica sensata.

**Novos invariantes de banco.** `CheckConstraint` XOR em `Parcelamento.cartao_id`/`conta_id`
(`ck_parcelamento_cartao_xor_conta`) e `UniqueConstraint(parcelamento_id, numero_parcela)`
em `Transacao` (`uq_transacao_parcelamento_numero_parcela`) — impede duas linhas
reivindicando a mesma parcela do mesmo parcelamento.

**Achado da revisão técnica: duplicidade de `numero_parcela` derrubava um 500 cru.** Antes
da correção, só o `UniqueConstraint` do banco barrava a duplicata — e como `main.py` não
tem handler genérico para `IntegrityError`, um `POST /transacoes` manual reivindicando uma
parcela já usada derrubava um erro cru, sem tradução para uma resposta HTTP de domínio.
Corrigido em `TransacaoService._validar_parcelamento()`, que agora levanta `ConflictError`
(409) — mesmo raciocínio já usado em `FaturaService.criar()` para o par cartão+mês. Ver
`docs/revisao-tecnica-parcelamento.md` para o relato completo, incluindo o gap de
roteamento também corrigido (`GET /transacoes` não expunha `parcelamento_id` como filtro).

## 💸 CRUD de Transferência

Oitava entidade de domínio. Diferente das anteriores, esta implementação começou com um
conflito arquitetural real: o pedido original especificava gerar duas `Transacao`
vinculadas (saída/entrada) a cada transferência, mas isso contradiz uma decisão já tomada
antes desta etapa (`Transferencia` fica fora de `Transacao` de propósito, para não inflar
relatórios de receita/despesa com dinheiro que só trocou de conta) e quebraria em silêncio
o cálculo de `saldo_atual` (que já soma `Transacao` e `Transferencia` como duas fontes
independentes — gerar `Transacao` a partir de `Transferencia` contaria o mesmo movimento
duas vezes). Apresentado o conflito, o usuário decidiu manter a modelagem original.
Detalhamento completo em `docs/revisao-tecnica-transferencia.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/transferencias` | Cria uma transferência entre duas contas do usuário autenticado. |
| 🔵 GET | `/transferencias` | Lista as transferências do usuário (filtro opcional `apenas_ativas`, `true` por padrão). |
| 🔵 GET | `/transferencias/{id}` | Obtém uma transferência. |
| 🟢 POST | `/transferencias/{id}/cancelar` | Cancela (soft delete): desfaz o efeito no saldo, preserva o histórico. |

Sem `PATCH` (`conta_origem_id`, `conta_destino_id`, `valor` e `data` são estruturais e
imutáveis após a criação) e sem `DELETE` físico (uma transferência incorreta é preservada
como histórico, nunca apagada).

**Nenhuma Transacao é gerada — Transferencia continua sendo, ela mesma, a fonte de verdade
do próprio efeito financeiro.** `TransferenciaService` nunca fala com
`TransacaoRepository`/`TransacaoService`. `ContaRepository.somar_transferencias` (já
existente desde o primeiro CRUD de Conta) continua sendo a única origem do efeito de uma
transferência em `saldo_atual`, agora filtrando `ativo=True` — a única mudança necessária
fora do módulo novo, confirmando que nenhum outro Service do projeto assumia que "toda
movimentação financeira passa por Transação".

**Atomicidade resolvida pela própria modelagem, não por código novo.** Como não há duas
Transacoes para criar, não existe o risco de "só um lado foi criado" — um único `INSERT`
já é atômico pela Unit of Work do request (`app/db/session.py`): commit só no fim, rollback
em qualquer exceção. Testado explicitamente: uma criação rejeitada (ex: conta de outro
usuário) não deixa nenhuma linha na tabela nem altera saldo de nenhuma conta.

**Cancelamento reaproveita a regra já adotada no projeto, não inventa uma nova.** Soft
delete (`ativo`, mesmo padrão de Conta/Categoria/Tag/Cartão) preserva a linha; "saldo nunca
é armazenado, sempre calculado" (mesmo princípio desde o CRUD de Conta) faz o efeito
financeiro desaparecer automaticamente na leitura seguinte, sem nenhum ajuste manual de
valor. A transferência cancelada continua visível via `GET /transferencias/{id}`
(`ativo: false`) — cancelamento nunca é um "apagar".

**Validação cruzada de posse, duas vezes.** `conta_origem_id` e `conta_destino_id`
precisam pertencer ao usuário autenticado e estar ativas — mesma checagem
(`_validar_conta_do_usuario_ativa`) aplicada aos dois campos, mesmo padrão já usado em
`CartaoService`+`ContaRepository`. Origem igual a destino é rejeitada no Service antes de
chegar no `CheckConstraint` do banco (mesma família de validação estrutural já usada em
Transação/Parcelamento).

**Fora de escopo, por decisão explícita (mesma lacuna já aceita em Cartão):**
`ContaService.desativar()` não bloqueia a desativação de uma conta envolvida numa
transferência ativa — desativar impede *novas* transferências (via checagem de `ativo`),
mas não reverte o histórico já lançado, mesmo comportamento de Conta/Cartão em qualquer
outro fluxo.

## 📅 CRUD de Conta Recorrente

Nona entidade de domínio. Análise arquitetural completa apresentada e aprovada antes da
implementação em `docs/analise-arquitetural-conta-recorrente.md` (interação com Transação,
geração lazy, escopo de frequência); detalhamento técnico da implementação — incluindo um
problema real encontrado e corrigido na revisão — em
`docs/revisao-tecnica-conta-recorrente.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/contas-recorrentes` | Cria o template e já gera as ocorrências vencidas até hoje. |
| 🔵 GET | `/contas-recorrentes` | Lista as recorrências do usuário (filtro opcional `apenas_ativas`, `true` por padrão). |
| 🔵 GET | `/contas-recorrentes/{id}` | Obtém uma recorrência. |
| 🟡 PATCH | `/contas-recorrentes/{id}` | Atualiza campos do template (nunca retroage sobre ocorrências já geradas). |
| 🟢 POST | `/contas-recorrentes/{id}/gerar-ocorrencias-pendentes` | Sincronização explícita — gera o que estiver vencido e ainda não existir; idempotente. |
| 🔴 DELETE | `/contas-recorrentes/{id}` | Desativa a recorrência (soft delete, sem efeito colateral nas ocorrências já geradas). |

**Geração é sempre sob demanda (lazy), nunca por scheduler/cron/job/fila.** Uma ocorrência só
nasce quando o Service é chamado explicitamente — na criação do template (ocorrências já
vencidas) ou via `POST .../gerar-ocorrencias-pendentes` (sincronização manual, idempotente).
Nenhuma ocorrência futura é gerada com antecedência — diferente de `Parcelamento` (compromisso
finito, gerado eager de uma vez), `ContaRecorrente` pode não ter fim (`data_fim` opcional), e
gerar uma ocorrência futura criaria uma `Transacao` para algo que ainda não aconteceu.

**Apenas `MENSAL` é suportada nesta etapa, por decisão explícita do usuário (YAGNI).**
`FrequenciaRecorrencia` mantém `SEMANAL`/`ANUAL` no enum (evita refatorar o model), mas
`ContaRecorrenteService` rejeita as duas com `BusinessRuleError` (422) — `dia_vencimento`
(dia do mês) e o utilitário compartilhado `app/core/datas.py` só têm semântica bem definida
para recorrência mensal. Extensão futura, se necessária, será evolução do domínio, não código
antecipado sem uso real.

**`ContaRecorrente` é só o template — a fonte da verdade continua sendo `Transacao`.** Nenhuma
mudança foi necessária em `ContaRepository`/`CartaoRepository`: cada ocorrência é uma
`Transacao` real (marcando `origem_recorrente_id`), então saldo e relatórios já a enxergam
automaticamente. Diferente do caso de `Transferencia`, aqui não havia nenhum conflito com
decisão arquitetural prévia — o próprio model já previa essa geração desde antes deste CRUD.

**Reaproveita `TransacaoService` por composição, nunca duplica validação.** Mesmo padrão de
`ParcelamentoService`: cada ocorrência nasce via `transacao_service.criar()`, herdando de
graça posse/ativo de conta ou cartão, resolução de fatura (recorrência cobrada no cartão),
compatibilidade de categoria e, agora, duplicidade de data. `ContaRecorrenteService` nunca
fala com `TransacaoRepository` para escrever, e nunca chama métodos privados de
`TransacaoService` — só os públicos.

**`PATCH` existe aqui — diferente de Fatura/Parcelamento/Transferência.** Editar o template
(`valor`, `descricao`, `categoria_id`, `dia_vencimento`, `frequencia`, `conta_id`/`cartao_id`,
`data_inicio`/`data_fim`) é seguro porque cada ocorrência já gerada é uma `Transacao`
independente que nunca volta a ler o template — só afeta gerações futuras. Testado
explicitamente: mudar o `valor` do template não altera o valor das ocorrências já geradas.

**Novos invariantes de banco.** `CheckConstraint` XOR em `ContaRecorrente.conta_id`/`cartao_id`
(`ck_conta_recorrente_cartao_xor_conta` — mesma lacuna que existia em `Parcelamento` antes de
sua própria análise corrigir) e `UniqueConstraint(origem_recorrente_id, data)` em `Transacao`
(`uq_transacao_origem_recorrente_data`) — impede duas ocorrências na mesma data da mesma
recorrência, mesma família de `uq_transacao_parcelamento_numero_parcela`.

**Achado da revisão técnica: `data_fim` anterior a `data_inicio` criava um template "morto".**
Sem checagem, a recorrência era aceita normalmente e nunca gerava nenhuma ocorrência — o
limite de geração (`min(hoje, data_fim)`) ficava sempre no passado da primeira data possível,
silenciosamente. Corrigido com uma validação explícita (`BusinessRuleError`, 422) em `criar()`
e `atualizar()`. Ver `docs/revisao-tecnica-conta-recorrente.md` para o relato completo.

## 🏦 CRUD de Financiamento

Décima entidade de domínio. Análise arquitetural completa apresentada em chat, com dois
conflitos arquiteturais reais identificados e resolvidos explicitamente pelo usuário antes
de qualquer código, formalizada em `docs/analise-arquitetural-financiamento.md`;
detalhamento técnico da implementação em `docs/revisao-tecnica-financiamento.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/financiamentos` | Cria o contrato e gera, na hora, o cronograma de amortização inteiro (uma `Transacao` por parcela, mais uma avulsa para a entrada, se houver). |
| 🔵 GET | `/financiamentos` | Lista os financiamentos do usuário (filtro opcional `apenas_ativos`, `true` por padrão — oculta os `QUITADO`). |
| 🔵 GET | `/financiamentos/{id}` | Obtém um financiamento (com `saldo_devedor` armazenado). |
| 🟢 POST | `/financiamentos/{id}/parcelas/{numero_parcela}/pagar` | Única forma de pagar uma parcela — marca a `Transacao` como `PAGO`, decrementa `saldo_devedor`, quita o contrato na última parcela. |

Sem `PATCH` (todo campo é estrutural e determina o cronograma inteiro) e sem `DELETE`
físico (nenhuma ação de cancelamento foi pedida nem implementada nesta etapa — ver
"Conflitos resolvidos" abaixo).

**Reaproveita `ContratoCreditoMixin` sem alteração.** `instituicao_financeira`,
`taxa_juros`, `sistema_amortizacao`, `num_parcelas`, `saldo_devedor`, `status`, `conta_id`,
`categoria_id` já vinham prontos do model. `cet` e `permite_quitacao_antecipada` continuam
persistidos, mas sem nenhuma regra construída em cima nesta etapa — mesmo princípio já
aplicado a `TipoRecorrencia` em `ContaRecorrente`.

**Cronograma de amortização PRICE/SAC: a única lógica genuinamente nova do domínio.**
`FinanciamentoService._gerar_cronograma()` é uma função pura sobre os campos imutáveis do
contrato (`valor_financiado`, `valor_entrada`, `taxa_juros`, `num_parcelas`,
`sistema_amortizacao`) — nenhuma coluna nova de juros/amortização por parcela foi
adicionada; o cronograma inteiro é recalculado sempre que necessário, tanto na geração
inicial quanto no pagamento de uma parcela específica. PRICE gera parcela fixa
(`PMT = principal × i / (1 − (1+i)⁻ⁿ)`); SAC gera amortização constante e parcela
decrescente. Em ambos, a última parcela absorve o saldo residual de arredondamento —
mesma técnica de `ParcelamentoService._dividir_valor` — garantindo que `saldo_devedor`
sempre feche em exatamente zero.

**`valor_entrada` gera uma `Transacao` avulsa, nunca uma "parcela zero".** Se vinculada a
`financiamento_id`, corromperia a contagem "parcelas restantes = `num_parcelas` − pagas"
que a Central Financeira já espera (`docs/central-financeira-especificacao.md`). A entrada
usa a mesma `conta_id`/`categoria_id` do contrato, mas sem `financiamento_id`/`numero_parcela`.

**Conflito arquitetural 1 (resolvido): pagamento de parcela é ação dedicada, nunca `PATCH`
genérico.** `TransacaoService.atualizar()` agora bloqueia edição de `status` sempre que
`financiamento_id`/`emprestimo_id` está preenchido (`BusinessRuleError`, 422) — sem essa
trava, um `PATCH /transacoes/{id}` poderia marcar uma parcela como paga sem passar por
`FinanciamentoService.pagar_parcela()`, e `saldo_devedor` (armazenado, não recalculado)
ficaria desincronizado silenciosamente. `TransacaoService.criar()` também força toda
transação de contrato de crédito a nascer `PENDENTE`, ignorando qualquer `status` enviado
no payload — checagem posicionada deliberadamente depois do ramo conta/cartão, para vencer
mesmo num payload não-intencional combinando `financiamento_id` com `cartao_id`. O único
caminho para `PAGO` é o novo método público `TransacaoService.marcar_parcela_de_contrato_paga()`,
chamado exclusivamente por `FinanciamentoService.pagar_parcela()` — idempotente (levanta
erro se a parcela já estava paga, protegendo contra decremento duplo de `saldo_devedor`).

**Conflito arquitetural 2 (resolvido): `conta_id` obrigatório validado só no Service, não
no banco.** `ContratoCreditoMixin.conta_id` é `nullable=True` (compartilhado com
`Emprestimo`), mas sem `conta_id` é estruturalmente impossível gerar qualquer parcela
(`Transacao` exige `conta_id XOR cartao_id`, e nenhum dos dois contratos usa cartão). Em vez
de alterar a coluna no banco, `FinanciamentoService.criar()` valida `conta_id is not None`
explicitamente (`BusinessRuleError`, 422). **Decisão consolidada com o CRUD de
`Emprestimo`:** a nullability da coluna no banco permanece inalterada — `conta_id`
obrigatório continua sendo uma regra de negócio, validada redundantemente em
`EmprestimoService.criar()` da mesma forma, não uma restrição estrutural do schema (ver
`docs/analise-arquitetural-emprestimo.md`).

**Encerramento do contrato: só `ATIVO → QUITADO`, automático.** Transição disparada dentro
de `pagar_parcela()` quando a última parcela é quitada ou `saldo_devedor` chega a zero.
`INADIMPLENTE` fica sem lógica de transição nesta etapa (exigiria comparar vencimento com
"hoje", o tipo de scheduler que o projeto já decidiu evitar) e nenhuma ação de cancelamento
foi implementada (não foi pedida, e cairia em amortização extraordinária/renegociação,
ambos explicitamente fora de escopo) — mesmo princípio YAGNI já aplicado a
`FrequenciaRecorrencia.SEMANAL`/`ANUAL`. Como nenhuma `Transacao` de financiamento é
apagada e o cabeçalho nunca é hard-deleted, o histórico se preserva sozinho.

**Novo invariante de banco.** `UniqueConstraint(financiamento_id, numero_parcela)` em
`Transacao` (`uq_transacao_financiamento_numero_parcela`) — mesma família de
`uq_transacao_parcelamento_numero_parcela`/`uq_transacao_origem_recorrente_data`, aplicada
proativamente (sem esperar descobrir o mesmo bug de novo).

**Fora de escopo nesta etapa, por pedido explícito:** renegociação, refinanciamento,
amortização extraordinária, carência, juros variáveis, indexadores (IPCA/CDI), seguros,
multas e qualquer funcionalidade bancária avançada. `permite_quitacao_antecipada` e `cet`
continuam no model, sem regra construída em cima.

## 🏦 CRUD de Empréstimo

Décima primeira entidade de domínio. Regras definidas explicitamente pelo usuário antes de
qualquer código (domínio praticamente idêntico ao de `Financiamento`), formalizadas em
`docs/analise-arquitetural-emprestimo.md`; detalhamento técnico da implementação em
`docs/revisao-tecnica-emprestimo.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/emprestimos` | Cria o contrato, gera a `Transacao` de desembolso (RECEITA, sempre) e o cronograma de amortização inteiro (uma `Transacao` PENDENTE por parcela). |
| 🔵 GET | `/emprestimos` | Lista os empréstimos do usuário (filtro opcional `apenas_ativos`, `true` por padrão — oculta os `QUITADO`). |
| 🔵 GET | `/emprestimos/{id}` | Obtém um empréstimo (com `saldo_devedor` armazenado). |
| 🟢 POST | `/emprestimos/{id}/parcelas/{numero_parcela}/pagar` | Única forma de pagar uma parcela — marca a `Transacao` como `PAGO`, decrementa `saldo_devedor`, quita o contrato na última parcela. |

Sem `PATCH` e sem `DELETE` físico — mesmo raciocínio de `Financiamento`.

**Reaproveita `ContratoCreditoMixin` e `Financiamento` quase integralmente.** Repository,
Schemas, Service e Router são estruturalmente idênticos aos de `Financiamento` (mesma
validação de posse, mesmo bloqueio de parcela paga, mesmo mecanismo de atualização de
`saldo_devedor`). A única diferença de domínio real: `valor_liberado` é obrigatório (sem
equivalente opcional a `valor_entrada`) e gera SEMPRE uma `Transacao` de RECEITA avulsa (o
desembolso), nunca condicional — ao contrário da entrada de `Financiamento`, que só existe
se informada e é DESPESA.

**Cronograma PRICE/SAC extraído para módulo compartilhado.** A matemática de amortização
(antes duplicada em `FinanciamentoService._gerar_cronograma_price/_sac`) foi movida para
`app/core/amortizacao.py` (`gerar_cronograma()`), a mesma função pura usada agora por
`FinanciamentoService` e `EmprestimoService` — mesmo padrão de extração já aplicado a
`app/core/datas.py` (rollover de dia_valido). `FinanciamentoService._gerar_cronograma()`
permanece como `staticmethod` que apenas delega, preservando a assinatura usada pelos testes
já existentes; os 37 testes unitários de `Financiamento` continuam passando sem alteração.

**Pagamento de parcela: zero mudanças no mecanismo já construído.**
`TransacaoService.marcar_parcela_de_contrato_paga()` e o bloqueio de `status` em
`TransacaoService.atualizar()`/`criar()` já cobriam `emprestimo_id` desde a implementação de
`Financiamento` (a guarda checava `financiamento_id is not None OR emprestimo_id is not
None` de forma genérica) — nenhuma alteração de lógica foi necessária nesses métodos, só a
adição da validação de posse (`_validar_emprestimo`, espelhando `_validar_financiamento`) e
do parâmetro de constructor `emprestimo_repo`. Isso confirma que a arquitetura desenhada
durante o CRUD de `Financiamento` já antecipava corretamente este caso.

**Encerramento do contrato: só `ATIVO → QUITADO`, automático** — mesmo princípio de
`Financiamento`.

**Novo invariante de banco.** `UniqueConstraint(emprestimo_id, numero_parcela)` em
`Transacao` (`uq_transacao_emprestimo_numero_parcela`) — mesma família aplicada
proativamente pela quarta vez (`Parcelamento` → `ContaRecorrente` → `Financiamento` →
`Emprestimo`).

**Bug real encontrado e corrigido durante esta etapa (não relacionado a `Emprestimo` em
si): forward ref `Mapped["Meta | None"]` não resolvia em `Transacao.meta`.** Bloqueava
`configure_mappers()` — e portanto toda a suíte de testes e o Alembic — de forma 100%
reprodutível, mesmo com o model de `Emprestimo` estruturalmente correto. Corrigido com um
import direto (`from app.models.meta import Meta`) em `app/models/transacao.py`. Relato
completo, incluindo a investigação e a hipótese sobre a causa raiz, em
`docs/revisao-tecnica-emprestimo.md`.

**Fora de escopo nesta etapa, por pedido explícito:** renegociação, refinanciamento,
amortização extraordinária, juros variáveis, seguros, multas, inadimplência e cancelamento
complexo — mesma lista de exclusões de `Financiamento`.

## 🎯 CRUD de Meta

Décima segunda entidade de domínio. Regras definidas explicitamente pelo usuário antes de
qualquer código, formalizadas em `docs/analise-arquitetural-meta.md`; detalhamento técnico
da implementação em `docs/revisao-tecnica-meta.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/metas` | Cria a meta (nome único por usuário, reativa uma meta inativa de mesmo nome em vez de duplicar). |
| 🔵 GET | `/metas` | Lista as metas do usuário, com `valor_acumulado`/`percentual` calculados (filtro opcional `apenas_ativas`, `true` por padrão). |
| 🔵 GET | `/metas/{id}` | Obtém uma meta, com progresso calculado. |
| 🟡 PATCH | `/metas/{id}` | Atualização parcial — inclusive `ativo`, para reativar diretamente. |
| 🔴 DELETE | `/metas/{id}` | Soft delete (`ativo=False`). |

Ao contrário de `Financiamento`/`Empréstimo`, `Meta` tem `PATCH` e `DELETE` — é uma entidade
de acompanhamento simples, sem cronograma nem contrato, mesma família de `Tag`/`Cartão`.

**Único conflito de modelagem real: qual é a fonte do cálculo de `valor_acumulado`?** O
pedido do usuário admitia duas leituras — (a) somar pelo saldo da `Conta` vinculada, ou (b)
somar sempre pelas `Transacao` com `meta_id` apontando para a meta, independente de
`conta_id`. Registrado em `docs/analise-arquitetural-meta.md` e resolvido ANTES de qualquer
código, via pergunta direta ao usuário: a regra escolhida foi (b) — `valor_acumulado` é
SEMPRE `SUM(Transacao.valor)` onde `meta_id` aponta para a meta e `status=PAGO` (RECEITA
soma positivo, DESPESA subtrai), e `conta_id` é puramente uma referência organizacional que
NUNCA participa do cálculo, mesmo quando preenchido. Coberto por teste de regressão explícito
tanto em unit (`test_valor_acumulado_independe_de_conta_vinculada`) quanto em integração
(aporte lançado numa `Conta` diferente da vinculada à `Meta` e ainda assim contabilizado).

**`valor_acumulado`/`percentual` calculados, nunca armazenados** — mesmo princípio de
`Conta.saldo_atual` e `Cartao.limite_disponivel`. `MetaService._com_progresso()` chama
`MetaRepository.somar_transacoes_pagas()` (agregação SQL com `CASE`, mesma família de
`ContaRepository.somar_transacoes_pagas`) e calcula o percentual em Python
(`ROUND_HALF_UP`, duas casas). Sem teto artificial em 100% — mesma filosofia de não clampar
`limite_disponivel` negativo: mostra a realidade, inclusive metas superadas.

**Fecha a última lacuna YAGNI de vínculo manual em `TransacaoService`.** `meta_id` ganha
validação de posse (`_validar_meta_ativa`) e bloqueio de meta inativa — mesmo padrão de
`_validar_conta_ativa`/`_validar_cartao_ativo`, mas SEM faixa nem duplicidade de parcela
(`Meta` não tem conceito de parcela; múltiplos aportes à mesma meta são normais, não erros,
ao contrário de `financiamento_id`/`emprestimo_id`/`parcelamento_id`). `meta_id` é ortogonal
à estrutura "no máximo um contrato" — uma transação pode ter `meta_id` E `financiamento_id`
simultaneamente. Com isso, `parcelamento_id`, `origem_recorrente_id`, `financiamento_id`,
`emprestimo_id` e `meta_id` têm todos validação de posse — não resta mais nenhum vínculo
manual aceito sem checagem em `Transacao`.

**Sem Repository/Service novo em `TransacaoService`.** Diferente de `Parcelamento`/
`ContaRecorrente`/`Financiamento`/`Empréstimo`, `MetaService` não escreve nenhuma `Transacao`
— é composição puramente de leitura via `MetaRepository`. A única mudança em
`TransacaoService`/`TransacaoRepository` foi a validação de posse e o filtro `meta_id` em
`listar()`.

**Novo invariante de banco.** `UniqueConstraint(usuario_id, descricao)` em `Meta`
(`uq_meta_usuario_descricao`) — mesmo padrão de `Tag`/`Cartão`.

**Fora de escopo nesta etapa, por pedido explícito:** notificações, automações, integração
com `Alerta`, scheduler, IA e histórico de progresso.

## 📎 CRUD de Anexo

Décima terceira entidade de domínio. Regras definidas explicitamente pelo usuário antes de
qualquer código, formalizadas em `docs/analise-arquitetural-anexo.md`; detalhamento técnico
da implementação em `docs/revisao-tecnica-anexo.md`.

| Método | Rota | Descrição |
|---|---|---|
| 🟢 POST | `/anexos` | Cria o anexo, vinculado a uma `Transacao` que precisa existir e pertencer ao usuário. |
| 🔵 GET | `/anexos` | Lista os anexos de uma transação (`transacao_id` obrigatório na query; filtro opcional `apenas_ativos`, `true` por padrão). |
| 🔵 GET | `/anexos/{id}` | Obtém um anexo. |
| 🔴 DELETE | `/anexos/{id}` | Soft delete (`ativo=False`). |

Sem `PATCH` — decisão confirmada explicitamente com o usuário antes da implementação: Anexo é
create+read+soft-delete apenas, mesmo raciocínio de `Financiamento`/`Empréstimo` (registro que
não faz sentido editar livremente após criado).

**Redesenho do model a partir do desenho especulativo original — o único conflito real desta
etapa.** `Anexo` já existia desde o "modelo inicial do domínio financeiro", mas nunca teve
Router/Service/Repository: o desenho original era polimórfico (`entidade_tipo` +
`entidade_id`, mesma estratégia de `Alerta`), com `usuario_id` como FK direta e sem soft
delete. As regras de domínio desta etapa são explícitas e sem ambiguidade — "Anexo pertence
sempre a uma Transação" e "nunca pertence diretamente ao usuário" — e contradizem esse
desenho. Diferente do conflito de `Meta` (duas leituras honestas do mesmo pedido), aqui não
havia ambiguidade de leitura: o model foi redesenhado, substituindo `entidade_tipo`/
`entidade_id`/`usuario_id` por uma FK obrigatória `transacao_id`, e adicionando `ativo`.
`TipoEntidadeReferenciavel` (o enum do desenho polimórfico) permanece intacto — é
infraestrutura reservada para `Alerta`, que ainda não teve suas regras de domínio definidas e
pode legitimamente precisar de referência polimórfica de verdade. `Usuario.anexos` (a
relationship direta) foi removida; `Transacao.anexos` foi adicionada.

**Posse SEMPRE transitiva via `TransacaoService` — nunca duplicada.** Pedido explícito do
usuário: "Toda validação de autorização deve reutilizar TransacaoService/Repository quando
apropriado, nunca duplicar regras." `AnexoService` injeta `TransacaoService` (não
`TransacaoRepository` diretamente) e chama `.obter(transacao_id, usuario_id)` em todo ponto
que precisa confirmar posse — o mesmo 404 uniforme que essa chamada já levanta tanto para
"transação não existe" quanto para "é de outro usuário" (anti-BOLA), nunca reimplementado
localmente. Isso cobre também a regra "não permitir anexar arquivos em transações de outro
usuário".

**Terceiro padrão de composição com `TransacaoService` neste projeto.** Distinto dos dois já
existentes: `Parcelamento`/`ContaRecorrente`/`Financiamento`/`Empréstimo` chamam
`TransacaoService` para ESCREVER (gerar parcelas/ocorrências); `MetaService` nunca fala com
`TransacaoService` — só lê `Transacao` via `MetaRepository` (agregação SQL própria).
`AnexoService` não escreve nem agrega `Transacao` — chama `TransacaoService.obter()` apenas
para validação de posse (leitura pontual, delegada, nunca duplicada).

**`ondelete="CASCADE"` — consequência direta de `Transacao` não ter soft delete.** `Transacao`
é removida de verdade (hard delete); um `Anexo` órfão (apontando para uma transação que não
existe mais) não faz sentido, então `transacao_id` usa `ForeignKey(ondelete="CASCADE")` e
`Transacao.anexos` usa `cascade="all, delete-orphan"` — mesmo padrão já usado em `Usuario`
para relacionamentos que ele possui exclusivamente.

**Migration recria a tabela `anexos` via `batch_alter_table`** (remove `entidade_tipo`,
`entidade_id`, `usuario_id`, `nome_arquivo`, `criado_em`, `tipo_mime`; adiciona `transacao_id`,
`nome_original`, `mime_type`, `data_upload`, `ativo`) — mesma estratégia manual de sempre
(autogenerate não usa batch mode por padrão para SQLite).

**Fora de escopo nesta etapa, por pedido explícito:** upload para cloud, OCR, thumbnails,
compressão, antivírus, versionamento, compartilhamento, criptografia de arquivo, download
autenticado especial. `AnexoService`/`AnexoRepository` nunca tocam o conteúdo do arquivo em
si — `caminho_arquivo` é só uma referência de string.

## 🏛️ Central Financeira

Última camada funcional do backend antes do frontend: uma camada de **orquestração e
agregação somente-leitura** sobre os Services de domínio já existentes, sem nenhuma regra
de negócio nova. `CentralFinanceiraService` (`app/services/central_financeira_service.py`)
não tem Repository próprio, nunca executa SQL diretamente e nunca duplica um cálculo que já
existe em outro Service — ele só injeta e reutiliza `ContaService`, `CartaoService`,
`FaturaService`, `TransacaoService`, `FinanciamentoService`, `EmprestimoService`,
`ParcelamentoService` e `MetaService` pelo construtor, compondo o resultado de métodos
públicos já existentes (ex: `ContaService.saldo_atual`, `CartaoService.limite_disponivel`,
o cálculo de progresso do `MetaService`).

11 endpoints agregadores, todos `GET`, todos protegidos por autenticação, sob
`/central-financeira/*`: `/resumo` (resumo financeiro geral do mês), `/saldo-consolidado`,
`/contas`, `/cartoes`, `/faturas`, `/financiamentos`, `/emprestimos`, `/metas` (progresso),
`/agenda` (próximos vencimentos), `/visao-mensal` e `/indicadores` (contagens gerais).
Nenhum `POST`/`PATCH`/`DELETE` — é uma camada puramente de leitura.

Duas pequenas extensões mecânicas foram necessárias em `TransacaoService`/
`TransacaoRepository` para evitar duplicar lógica na Central: um filtro `status` em
`listar()` (paralelo ao filtro `tipo` já existente) e `somar_por_periodo()` (agregação SQL
`SUM`, seguindo a diretriz de nunca somar em Python — ver `docs/decisao-performance-saldo.md`).
Nenhuma outra mudança em Service/Repository/Model existente foi necessária; `alembic check`
confirma zero migration nova.

`mes`/`ano` (`/resumo`, `/visao-mensal`) e `dias` (`/agenda`) são validados no
Router (`Query(ge=..., le=...)`) — devolvem 422 fora de faixa em vez de deixar
`calendar.monthrange`/`date()` levantar um `ValueError` não tratado (500);
achado da revisão técnica desta etapa, ver `docs/revisao-tecnica-central-
financeira.md`.

Escopo desta etapa, com justificativa completa em
`docs/analise-arquitetural-central-financeira.md`: `Alerta`/insights ficam de fora (fora da
lista de 11 endpoints pedida, e exigiriam regra de negócio nova — vedado nesta camada); a
Agenda Financeira (`/agenda`) lista só ocorrências já materializadas (`Transacao`s reais,
parcelas de contrato, faturas em aberto) — não projeta ocorrências futuras ainda não
geradas de `ContaRecorrente` (lazy por design, ver seção de `ContaRecorrente` acima).

## 🖥️ Ambiente de Desenvolvimento

Como rodar o projeto inteiro localmente e acompanhar o desenvolvimento visual em tempo
real — backend e frontend juntos, com um único comando no dia a dia. Pré-requisitos:
Python 3.10+ e Node 18+ instalados.

### Configuração inicial (uma vez só)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # Linux/Mac: cp .env.example .env
# edite backend/.env e defina um SECRET_KEY proprio - sugestao para gerar um:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
alembic upgrade head
cd ..

# Frontend
cd frontend
npm install
copy .env.example .env        # Linux/Mac: cp .env.example .env
cd ..

# Orquestração (raiz do projeto)
npm install
```

`frontend/.env` já vem com `VITE_API_URL=http://localhost:8000` (aponta pro backend
local) — normalmente não precisa editar nada nele.

### Uso diário — um único comando

Da raiz do projeto:

```bash
npm run dev:full
```

Isso sobe **backend** (`uvicorn --reload`, porta 8000) e **frontend** (`vite`, porta
5173) juntos, com saída colorida e prefixada (`[BACKEND]`/`[FRONTEND]`) no mesmo
terminal. `Ctrl+C` encerra os dois de uma vez.

**Abra `http://localhost:5173` no navegador** — é essa URL que mostra a aplicação.
`http://localhost:8000` é só a API (sem tela; `http://localhost:8000/docs` mostra a
documentação interativa do Swagger, útil pra testar endpoints direto).

Se preferir rodar cada lado separado (dois terminais): `npm run dev:backend` e
`npm run dev:frontend`, também a partir da raiz.

### O que já está validado

- **Hot reload dos dois lados.** Vite (frontend) recarrega o navegador instantaneamente
  ao salvar um arquivo em `frontend/src/` (HMR — sem perder o estado do React quando
  possível); Uvicorn (`--reload`) reinicia o processo do backend ao salvar um arquivo em
  `backend/app/`.
- **CORS em vez de proxy** — decisão já validada, não um item pendente. O frontend
  chama o backend diretamente (`fetch` cross-origin) usando `VITE_API_URL`;
  `CORS_ORIGINS` no backend já libera `http://localhost:5173` por padrão
  (`app/core/config.py`). Mais simples que configurar um proxy do Vite, e funciona
  igual em dev e em produção (só troca a URL).
- **Favicon, título e loading inicial** — aba do navegador mostra "Finanças Pessoais"
  com o ícone da marca (`frontend/public/favicon.svg`); `index.html` tem fundo escuro
  aplicado antes de qualquer CSS carregar (evita flash branco) e um spinner estático
  enquanto o bundle React ainda está carregando — substituído pelo spinner "de verdade"
  (`ProtectedRoute`) assim que a aplicação monta e checa a sessão salva.
- **Todo o fluxo validado de ponta a ponta**: `npm install` do zero (pasta limpa, sem
  `node_modules`), `npm run dev` subindo o Vite, backend respondendo em `/health`,
  registro + login reais via HTTP entre as duas portas com CORS correto.

### Variáveis de ambiente

| Arquivo | Variável | Obrigatória? | Descrição |
|---|---|---|---|
| `backend/.env` | `DATABASE_URL` | não (tem default) | Caminho do SQLite. Default: `sqlite:///./financas.db` |
| `backend/.env` | `CORS_ORIGINS` | não (tem default) | Origens autorizadas a chamar a API. Default: `["http://localhost:5173"]` |
| `backend/.env` | `SECRET_KEY` | **sim** | Assina os JWT. A aplicação não sobe sem isso. |
| `backend/.env` | `JWT_ALGORITHM`, `JWT_KEY_ID`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `LOG_LEVEL` | não (têm default) | Ver `backend/.env.example` para os valores e o porquê de cada um. |
| `frontend/.env` | `VITE_API_URL` | **sim** | URL base da API. Default sugerido: `http://localhost:8000`. |

Os `.env` reais nunca vão pro Git (`.gitignore`) — só os `.env.example`, que documentam
todas as variáveis com comentário explicando cada uma.

### Nota sobre SQLite em pastas sincronizadas na nuvem

Se a pasta do projeto estiver dentro de uma pasta sincronizada (OneDrive, Dropbox etc.)
e o backend acusar erro de I/O no banco ao rodar `alembic upgrade head` ou ao usar a
API, é o sincronizador segurando o arquivo `financas.db` momentaneamente — não é bug do
projeto. Pausar a sincronização durante o desenvolvimento (ou mover a pasta pra fora de
uma pasta sincronizada) resolve.

## 🚀 Como rodar

### 🐍 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # depois edite e defina um SECRET_KEY próprio (ver seção Autenticação)
alembic upgrade head        # cria o banco financas.db com todas as tabelas
uvicorn app.main:app --reload
```

API sobe em `http://localhost:8000`. Verifique com `GET /health`. Endpoints de
autenticação em `/auth/*` (ver seção Autenticação acima).

### 🧬 Migrations (Alembic)

A URL do banco usada pelas migrations vem de `app.core.config.settings` (a mesma
fonte usada pela aplicação) — não precisa duplicar em `alembic.ini`. Todo model novo
deve ser importado em `app/models/__init__.py` para que o Alembic o enxergue.

```bash
cd backend
alembic revision --autogenerate -m "descricao da mudanca"   # gera uma migration a partir dos models
alembic upgrade head                                         # aplica migrations pendentes
alembic downgrade -1                                          # desfaz a ultima migration
alembic current                                               # mostra a revisao atual do banco
```

### ✅ Testes

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

- `tests/unit/` — testa uma camada isolada, com dependências (ex: a sessão do banco)
  substituídas por Mock/fake. Não precisa de banco de dados, roda em milissegundos. Cobre
  o `SQLAlchemyRepository` genérico, `app/core/security.py` (hash, JWT, tampering),
  `AuthService`, `ContaService`, `CategoriaService`, `TagService`, `CartaoService`,
  `FaturaService` (incluindo `resolver_fatura_aberta`), `TransacaoService` (incluindo posse,
  faixa e duplicidade de `parcelamento_id`, de `financiamento_id` e de `emprestimo_id`, posse
  e duplicidade de data de `origem_recorrente_id`, bloqueio de edição de `status` para
  parcela de contrato de crédito, e o `marcar_parcela_de_contrato_paga`), `ParcelamentoService`,
  `ContaRecorrenteService`, `FinanciamentoService` e `EmprestimoService` (todos com
  repositories falsos em memória — a correção da *query* SQL em si, quando existe agregação,
  fica a cargo dos testes de integração; aqui só a fórmula e as regras de negócio, incluindo a
  validação cruzada de posse entre `CartaoService`/`ContaRepository`,
  `FaturaService`/`CartaoRepository`, `TransacaoService`/{`ContaRepository`,
  `CartaoRepository`, `CategoriaRepository`, `TagRepository`, `ParcelamentoRepository`,
  `FinanciamentoRepository`, `EmprestimoRepository`, `ContaRecorrenteRepository`,
  `FaturaRepository`, `FaturaService`} — o Service com mais dependências injetadas do
  projeto — `ParcelamentoService`/{`ParcelamentoRepository`, `TransacaoRepository`,
  `TransacaoService`}, `ContaRecorrenteService`/{`ContaRecorrenteRepository`,
  `TransacaoRepository`, `TransacaoService`}, `FinanciamentoService`/{`FinanciamentoRepository`,
  `TransacaoRepository`, `TransacaoService`} e `EmprestimoService`/{`EmprestimoRepository`,
  `TransacaoRepository`, `TransacaoService`} — os quatro últimos testados com um
  `TransacaoService` falso para não reexercitar validações já cobertas em
  `test_transacao_service.py` (incluindo geração lazy mensal com clamping/rollover de data,
  idempotência da sincronização, rejeição de `SEMANAL`/`ANUAL`, e — para `Financiamento` e
  `Emprestimo` — as invariantes matemáticas do cronograma PRICE/SAC, agora centralizadas em
  `app/core/amortizacao.py`: soma das amortizações fechando exatamente o principal, parcela
  fixa vs. decrescente, e juros da primeira parcela batendo com `principal × taxa`), e
  `TransferenciaService`/{`TransferenciaRepository`, `ContaRepository`} — validação cruzada
  de posse/ativo das duas contas envolvidas, origem distinta de destino, e cancelamento
  (soft delete)), e `CentralFinanceiraService`/{fakes dos 8 Services de domínio injetados}
  — saldo consolidado, resumos de contas/cartões/faturas/financiamentos/empréstimos/metas,
  fluxo de caixa e patrimônio líquido do resumo financeiro geral, agenda financeira
  (inclusão/exclusão de eventos pela janela de dias e por status pago/pendente) e
  indicadores gerais, sempre reexercitando só a composição/agregação — nunca a fórmula em
  si, já coberta no teste do Service de origem.
- `tests/integration/` — testa a aplicação de verdade contra um SQLite em memória (fixture
  `db_session`) e, para os endpoints, contra um `TestClient` do FastAPI com o banco real
  substituído pelo de teste (fixture `client`). Cada teste roda em um banco novo e vazio.
  Cobre o fluxo HTTP completo de autenticação (registro, login, acesso protegido, refresh
  com rotation, logout escopado, logout global), o CRUD de Conta (cálculo de saldo com
  Transacao/Transferencia reais no banco, isolamento multi-tenant, soft delete, PATCH
  parcial), o CRUD de Categoria (visibilidade sistema/própria/de outro usuário, hierarquia
  sem ciclos, bloqueio de subcategoria ativa nos dois caminhos - DELETE e PATCH), o CRUD
  de Tag (nome único por usuário, reativação por nome vs. bloqueio ao renomear, soft
  delete), o CRUD de Cartão (validação cruzada com Conta de outro usuário, nome único,
  cálculo de `limite_disponivel` com Transacao/Fatura reais inseridas diretamente via
  `db_session`), o CRUD de Fatura (posse transitiva via Cartão, derivação de datas do
  ciclo, unicidade cartão+mês, fechamento com snapshot, pagamento parcial/total com
  `Transacao` reais no banco, exclusão restrita), o CRUD de Transação (resolução
  automática de fatura via HTTP real, reaproveitamento do mesmo ciclo, transição para o
  ciclo seguinte após o fechamento, status forçado para cartão, imutabilidade de fatura
  fechada, categoria/tag de outro usuário, duplicidade de `numero_parcela` retornando 409)
  o CRUD de Parcelamento (geração eager de parcelas por cartão e por conta com Fatura/
  Transacao reais no banco, distribuição entre ciclos diferentes, cancelamento parcial
  preservando parcelas com fatura já fechada, ausência de `PATCH`/`DELETE`) e o CRUD de
  Transferência (efeito real em `saldo_atual` das duas contas via `GET /contas/{id}`,
  ausência de qualquer `Transacao` gerada, cancelamento desfazendo o saldo mas preservando
  o histórico, atomicidade de uma criação rejeitada não deixando resíduo no banco, ausência
  de `PATCH`/`DELETE`) e o CRUD de Conta Recorrente (geração lazy de ocorrências reais via
  HTTP tanto por conta quanto por cartão — vinculadas a Fatura real —, rejeição de
  `SEMANAL`/`ANUAL`, rejeição de `data_fim` anterior a `data_inicio`, efeito em `saldo_atual`,
  sincronização idempotente, duplicidade de data retornando 409 num `POST /transacoes`
  manual, `PATCH` do template sem afetar ocorrências já geradas, soft delete via `DELETE`) e
  o CRUD de Financiamento (geração eager do cronograma PRICE/SAC real via HTTP — parcela
  fixa vs. decrescente conferida sobre `Transacao`s reais no banco, rollover/clamping de
  data, transação de entrada separada das parcelas, pagamento de parcela via a ação
  dedicada com efeito real em `saldo_devedor` e transição para `QUITADO` na última parcela,
  bloqueio de `PATCH /transacoes/{id}` para `status` de parcela de financiamento com
  `saldo_devedor` confirmadamente inalterado, posse cruzada num `POST /transacoes` manual
  com `financiamento_id` de outro usuário, duplicidade de `numero_parcela` retornando 409) e
  o CRUD de Empréstimo (mesma cobertura de `Financiamento`, mais a diferença de domínio:
  desembolso via `Transacao` de RECEITA sempre gerada — nunca condicional —, ausência do
  conceito de entrada, `valor_liberado` obrigatório retornando 422 quando ausente) e o CRUD
  de Meta (`valor_acumulado`/`percentual` calculados via HTTP a partir de `Transacao`s reais
  com `meta_id`, RECEITA soma e DESPESA subtrai, `PENDENTE` ignorada, percentual passando de
  100%, independência do cálculo em relação a `conta_id`, posse cruzada e meta inativa num
  `POST /transacoes` manual, filtro `GET /transacoes?meta_id=`) e o CRUD de Anexo (posse
  transitiva via `Transacao` real, criação/obtenção/listagem/soft delete via HTTP, rejeição em
  transação de outro usuário e em transação inexistente, múltiplos anexos na mesma transação,
  ausência de `PATCH` retornando 405, cascade físico dos anexos ao excluir a `Transacao` dona)
  e a Central Financeira (os 11 endpoints de `/central-financeira/*` contra um `TestClient`
  real, com `Conta`/`Cartão`/`Fatura`/`Transacao`/`Financiamento`/`Meta` reais no banco:
  soma de saldo entre múltiplas contas, reflexo de pagamento de parcela de `Financiamento`
  no resumo, exclusão de transação `PENDENTE` do fluxo de caixa mensal, janela de dias da
  agenda financeira, isolamento multi-tenant entre dois usuários, e exigência de
  autenticação em todos os 11 GETs, e rejeição com 422 de `mes`/`ano`/`dias`
  fora de faixa nas 3 rotas que os aceitam) e os casos de erro
  (401/403/404/409/422).

Suíte atual: 788 testes (471 unit + 317 integration, todos passando).

### 🎨 Frontend

```bash
cd frontend
cp .env.example .env   # ajuste VITE_API_URL se o backend não estiver em localhost:8000
npm install
npm run dev
```

Frontend sobe em `http://localhost:5173` (mesma origem já liberada por
`CORS_ORIGINS` no backend, sem proxy necessário). `npm run build` roda
`tsc -b && vite build`.

### 🔌 Deixar sempre no ar (sem terminal aberto)

Para uso local do dia a dia sem precisar deixar dois terminais abertos, três scripts na
raiz do projeto sobem backend + frontend em segundo plano, sem nenhuma janela visível:

```powershell
# 1. Gerar o build de produção do frontend (repita sempre que o código do frontend mudar)
cd frontend
npm run build
cd ..

# 2. Iniciar os dois processos em segundo plano
.\iniciar.ps1          # ou dê duplo-clique em iniciar-silencioso.vbs (zero janela)

# 3. Parar quando quiser
.\parar.ps1            # ou dê duplo-clique em parar-silencioso.vbs (zero janela)
```

Abre em `http://localhost:5173` (frontend, servindo o build via `vite preview`) e
`http://localhost:8000` (backend, `uvicorn` sem `--reload`). Para o app iniciar sozinho a
cada login do Windows, coloque um atalho de `iniciar-silencioso.vbs` na pasta de
inicialização (`Win+R` → `shell:startup`).

**Duplo-clique em `.ps1` direto não funciona** (bug reportado em 2026-07-20): o Windows não
executa arquivos `.ps1` com duplo-clique por padrão — abre num editor de texto ou não faz
nada, dependendo da associação de arquivo do sistema. Use sempre `iniciar-silencioso.vbs`/
`parar-silencioso.vbs` (zero janela) — já existiam para iniciar, `parar-silencioso.vbs` foi
criado agora para fechar essa mesma lacuna do lado de parar. Alternativa com janela visível
(mostra a mensagem de confirmação antes de fechar): `iniciar.bat`/`parar.bat`, também na raiz.

**Importante:** este modo serve um build ESTÁTICO — mudanças no código do frontend só
aparecem depois de rodar `npm run build` de novo e reiniciar (`parar.ps1` + `iniciar.ps1`).
Backend e frontend continuam em processos/portas separados de propósito: as rotas do
frontend (`/cartoes`, `/contas`, `/transacoes`...) têm o MESMO nome dos prefixos da API —
servir os dois da mesma origem faria a API sempre vencer o roteamento e quebrar o
carregamento direto de qualquer página do app. Nenhum código de negócio/API foi alterado
para viabilizar isso; é puramente uma forma alternativa de execução local.

**Combinado com o usuário (2026-07-18):** já que o app roda sempre em segundo plano a
partir de um build, toda etapa de frontend a partir de agora termina com `npm run build` +
`parar.ps1`/`iniciar.ps1` (ou equivalente) já executados por quem estiver desenvolvendo —
nunca deixar o build antigo no ar depois de uma mudança sem avisar.

Recomendado apenas para uso local — este projeto ainda não tem rate limiting em
`/auth/login`/`/auth/refresh` nem uma estratégia de backup do SQLite (ver seção
"Próximas etapas"), então expor essas portas fora do próprio computador (internet ou até a
rede local) não é indicado ainda.

**Stack:** React 18 + TypeScript 5 + Vite 5 + Tailwind 3 + React Router +
TanStack React Query + React Hook Form + Zod + `motion` (Framer Motion) +
`lucide-react` + fonte Geist (`@fontsource-variable`, self-hosted). `fetch`
nativo como transporte HTTP (sem axios). Ver `docs/analise-arquitetural-
frontend.md` para a arquitetura de camadas e `docs/design-system.md` +
`docs/motion-principles.md` (documentos congelados) para a identidade
visual e as regras de motion — o frontend consome a API do backend
exatamente como ela existe hoje, sem alterar nenhum endpoint/contrato/regra
de negócio.

**Duas camadas** (diferente do backend, que tem três — o frontend não tem
regra de negócio, então não precisa de uma camada de Service própria):
acesso a dado (`api/`, `services/`, `types/`, `schemas/`) e apresentação
(`hooks/`, `components/`, `pages/`, `layouts/`). React Query é a
infraestrutura de comunicação com a API (cache, loading, refetch,
invalidação, deduplicação) — nenhuma página gerencia esse estado à mão.
`components/` já nasce na estrutura definitiva (`ui/`, `layout/`,
`domain/`), populada de forma incremental por etapa.

**Etapa F1 concluída** (fundação, sem nenhuma tela de negócio ainda):
autenticação completa (registro, login, refresh silencioso com rotation no
boot da aplicação, logout, guarda de rota), cliente HTTP com renovação
automática de sessão em 401 (com mutex contra corridas), tratamento
uniforme de erro (inclusive a dualidade de `detail` do FastAPI — string dos
handlers de domínio do projeto vs. lista do validador padrão, mesmo status
422). Validado de ponta a ponta contra o backend real (não só
compilação): `POST /auth/registrar`, `/login`, `/refresh` com reuso de
token antigo rejeitado (rotation), `/me` com e sem token, `/logout`, CORS e
os dois formatos de 422, todos batendo exatamente com os tipos TypeScript
declarados em `src/types/auth.ts`.

**Etapa F2 concluída** (Design System implementado em código, seguindo
`docs/design-system.md` e `docs/motion-principles.md` exatamente): tokens
de cor/tipografia/espaçamento/radius/sombra/blur/motion como variáveis CSS
(`src/index.css`) lidas pelo `tailwind.config.js`; fonte Geist self-hosted;
`MotionConfig reducedMotion="user"` no root (`App.tsx`) e constantes de
motion reutilizáveis (`src/lib/motion.ts`); componentes base restilizados
(`Button` — variantes/tamanhos/estado `loading`, `Input`, `Spinner`,
`ErrorMessage`) e novos (`Badge`, `Checkbox`, `Switch`, `Select`,
`Textarea`, `Tooltip`, `Kbd`, `Divider`, `Avatar`, `ProgressBar`);
`Sidebar`/`Header` em `components/layout/` compondo `AppLayout`; `tsc -b` e
`vite build` validados. Barra de progresso de navegação de rota e os
componentes compostos de formulário (`FormField`, `MoneyInput`,
`FormDialog`, `CategorySelect` etc.) ficam para uma etapa futura de
Formulários, que é quando passam a ter uso real.

**Etapa F3 concluída** (Dashboard real consumindo os 11 endpoints de
`/central-financeira/*` — a primeira tela com dado financeiro real,
reordenada para vir logo após o Design System por decisão explícita do
usuário, antes de Formulários/Tabelas; ver
`docs/analise-arquitetural-dashboard.md`): camada de dados dedicada
(`types/centralFinanceira.ts`, `services/centralFinanceiraService.ts`,
seção `dashboard` de `queryKeys.ts`, onze hooks em
`hooks/useCentralFinanceiraQueries.ts`, um por endpoint); dez componentes
genéricos novos em `components/ui/` (`Card`, `Skeleton`, `EmptyState`,
`LoadingCard`, `SectionTitle`, `MetricCard`, `FinancialBadge`,
`TrendIndicator`, `AnimatedNumber`, `StatCard`); treze componentes de
`components/domain/dashboard/`, cada um independente e dono da própria
busca via seu hook (diretriz explícita: `DashboardPage.tsx` só orquestra o
layout — Bento Grid, gate de onboarding para usuário sem nenhuma conta
ainda — nunca busca dado nem guarda estado de seção); rota `/dev`
(`pages/dev/DevPage.tsx`), laboratório visual permanente e protegido, fora
do `Sidebar`, cobrindo os dez componentes novos com dado fixo. Validado
com `tsc -b` + `vite build` limpos e com uma sessão real contra os 11
endpoints (registro, login, criação de conta, todas as respostas
conferidas byte a byte contra os tipos TypeScript declarados). Sem
Alertas/Insights/Parcelamentos no Dashboard — nenhum dos três tem endpoint
na Central Financeira hoje (confirmado por leitura direta do router, não
assumido da especificação de produto original) — nem gráfico de
biblioteca (decisão de qual lib usar segue adiada; "Visão Mensal" usa uma
comparação simples sem dependência nova).

**Etapa F4 concluída** (infraestrutura reutilizável de tabelas — nenhuma entidade real,
nenhum CRUD ainda; ver `docs/analise-arquitetural-frontend.md`, seção 13, e
`docs/revisao-tecnica-tabelas.md`): `hooks/useDataTable.ts` centraliza busca (via
`useDeferredValue`), filtro, ordenação, paginação e seleção client-side sobre
`ColumnDef`/`FilterDef`/`RowAction`/`BulkAction` genéricos (`types/table.ts`); dezenove
componentes novos em `components/ui/` (`Table`, `TableHeader`, `TableBody`, `TableRow`,
`TableCell`, `SortHeader`, `SelectionCheckbox`, `TableSkeleton`, `LoadingTable`,
`EmptyTable`, `Pagination`, `SearchBar`, `FilterBar`, `ColumnVisibility`, `Toolbar`,
`RowActions`, `ConfirmAction`, `BulkActions` e o orquestrador `DataTable`, que compõe
todos os outros); responsivo (`<table>` real em `md+`, cards abaixo disso, nunca scroll
horizontal — design-system.md, seção 24); motion conforme motion-principles.md (um único
fade de conjunto no corpo da tabela a cada mudança de página/busca/filtro/ordenação, sem
stagger por linha); rota `/dev/tables` (`pages/dev/DevTablesPage.tsx`), laboratório
visual permanente com 4.000 registros sintéticos gerados por PRNG determinístico
(`pages/dev/fixtures/tableFixtures.ts`), cobrindo vazio/carregando/erro/sucesso, busca,
filtros, ordenação, paginação, seleção, ações por linha e em lote (com confirmação).
Validado com `tsc -b` + `vite build` limpos.

**Etapa F5 concluída** (infraestrutura reutilizável de formulários — nenhuma entidade
real, nenhum CRUD ainda; ver `docs/analise-arquitetural-frontend.md`, seção 12, e
`docs/revisao-tecnica-formularios.md`): base em React Hook Form + Zod (`zodResolver`,
`mode: "onBlur"`) — o schema Zod valida só formato/obrigatoriedade, nunca regra de
negócio, que continua 100% no backend. Dez peças estruturais em `components/ui/`
(`Form`, `FormDialog`, `FormSection`, `FormField`, `FormLabel`, `FormDescription`,
`FormError`, `FormActions`, `SubmitButton`, `CancelButton`); dezessete campos
genéricos (`TextField`, `EmailField`, `PasswordField`, `TextAreaField`, `NumberField`,
`CurrencyField`, `PercentageField`, `DateField`, `DateTimeField`, `SelectField`,
`MultiSelectField`, `SearchSelect`, `TagsInput`, `CheckboxField`, `SwitchField`,
`RadioGroupField`, `FileUpload` — este último só infraestrutura local, sem integração
com `Anexo`); `utils/mask.ts` com máscara de moeda/percentual/número/data por
manipulação de dígito puro (sem biblioteca pesada); `Form` foca e rola automaticamente
até o primeiro campo com erro num submit inválido; `FormDialog` reaproveita
`modalBackdrop`/`modalPanel` de `lib/motion.ts` (mesmo par já usado pelo
`ConfirmAction` da F4) e, ao tentar fechar com alteração não salva, troca o conteúdo do
modal por uma confirmação em vez de empilhar um segundo modal (design-system.md, seção
22); ícone de sucesso do `Toast` (F1) passou a desenhar o check via `pathLength`
(motion-principles.md, seção 5.7) em vez do ícone estático anterior. Rota `/dev/forms`
(`pages/dev/DevFormsPage.tsx`), laboratório visual permanente com um formulário
completo cobrindo quase todo tipo de campo, um `FormDialog` de exemplo, erro 422
simulado vindo "do servidor" (`form.setError`) e campos desabilitados. Validado com
`tsc -b` + `vite build` limpos.

**Etapa F6 concluída** (CRUD de Conta — primeira entidade real, compondo integralmente
os sistemas de Tabela (F4) e Formulário (F5); ver `docs/revisao-tecnica-conta-frontend.md`):
não existiam `docs/analise-arquitetural-conta.md` nem `docs/revisao-tecnica-conta.md`
(Conta foi a primeira entidade implementada no backend, antes da convenção de
doc-por-entidade) — o contrato real (`ContaCreate`/`ContaUpdate`/`ContaRead`,
`TipoConta`, `saldo_atual` sempre calculado pelo `ContaService`, `DELETE` como soft
delete, reativação via `PATCH {ativo: true}`) foi lido direto de `app/models/conta.py`,
`app/schemas/conta.py`, `app/api/routes/conta.py` e `app/services/conta_service.py`.
Camada de dados nova: `types/conta.ts` (com `ContaRead` re-exportado a partir de
`types/centralFinanceira.ts`, eliminando a duplicação sinalizada na revisão técnica da
F3), `schemas/conta.ts` (Zod só de formato; `instituicao` fica `string` no formulário —
nunca `string | null`, que quebraria o valor nativo do `<input>` — e vira `null` só no
mapeamento para o payload da API, em `contaFormValuesParaPayload`), `services/contaService.ts`
e `hooks/useContaQueries.ts` (`useContas`/`useConta`/`useCriarConta`/`useAtualizarConta`/
`useDesativarConta`, invalidando só `contas.*` mais as três chaves do Dashboard que
realmente dependem de Conta: `dashboard.contas`, `dashboard.saldoConsolidado`,
`dashboard.indicadores`). `components/domain/conta/` com `contaTableColumns.tsx`
(colunas para o `DataTable` da F4) e `ContaFormDialog.tsx` — um único `FormDialog` (F5)
serve criação, edição e visualização: em modo leitura os campos ficam desabilitados
(todo `*Field` da F5 já aceita `disabled`) e o rodapé troca "Salvar" por "Editar", em vez
de um componente de detalhe separado. Página `/contas` (`pages/contas/ContasPage.tsx`)
compõe só peças já existentes (`DataTable`, `ContaFormDialog`, `ConfirmAction` da F4 para
a confirmação de desativação) — nenhum componente de layout novo. Rota adicionada ao
`Sidebar` (primeira entidade fora de `/dev/*`). Validado com `tsc -b` + `vite build`
limpos e um smoke test real contra o backend (registro, login, criar conta com e sem
instituição, listar, editar, validação 422, desativar, reativar, conferindo que
`/central-financeira/contas` reflete cada mudança) rodado num backend descartável isolado
(SQLite temporário, nunca o `financas.db` real do usuário).

**Etapa de Refinamento Visual concluída** (branding de instituições financeiras + tema
claro/escuro + microinterações — nenhuma regra de negócio, nenhum contrato de API,
nenhum backend alterado; ver `docs/revisao-tecnica-branding-e-microinteracoes.md`):
`lib/institutions.ts` é o registry único que resolve nome/cor de marca/monograma/fallback
para qualquer `instituicao` livre (Conta hoje, Cartão/Fatura/qualquer entidade futura
reaproveitam sem alteração) — sem SVG de logo real embutido nesta etapa (direitos de
marca + falta de uma fonte confiável para as ~17 instituições pedidas dentro do tempo da
etapa), arquitetado para receber um logo de verdade depois sem tocar em nenhum
consumidor. `components/ui/InstitutionBadge.tsx` é a única peça visual que usa esse
registry, já aplicada em `contaTableColumns.tsx`, `ContaFormDialog.tsx` (preview ao vivo
enquanto digita) e nos cards `ContasCard`/`CartoesCard` do Dashboard. Tema claro/escuro:
`design-system.md` (seção 0) já tinha deixado essa porta aberta ("tokens como variável
CSS para não fechar a porta a um tema claro no futuro") mas decidira, naquela etapa,
dark-only sem toggle — um toggle de verdade foi pedido explicitamente pelo usuário nesta
etapa, então `[data-theme="light"]` foi adicionado a `src/index.css` (mesmos tokens de
tipografia/espaçamento/radius/motion, cores recalibradas para contraste AA sobre fundo
claro — semânticas financeiras e cores de gráfico usam tons "600" em vez de "400"),
`contexts/ThemeContext.tsx` persiste em `localStorage`, e um script síncrono em
`index.html` aplica o tema salvo antes do React montar (sem flash). Menu do usuário
novo (`components/layout/UserMenu.tsx`, abre ao clicar no nome no `Header` — pedido
explícito) contém o `ThemeToggle` e o botão "Sair" (que antes vivia solto no `Header`);
o menu é a âncora documentada para onde futuras opções de personalização devem crescer.
Microinterações: elevação de hover em `Button`/`Card` via `whileHover` do Framer Motion
(nunca `translate` via classe Tailwind no mesmo elemento que já usa `motion` para
`whileTap` — os dois sistemas de `transform` brigariam pela mesma propriedade), glow
discreto de acento (`--shadow-glow-accent`, token novo) no botão primário e no item ativo
da `Sidebar`, barra de acento via `box-shadow: inset` no hover/seleção de `TableRow`
(preferido a `border-left` por não ser afetado por `border-collapse` da `Table`),
entrada com fade+slide-up em `StatCard` (opt-in via `Card.animateEntrance`, nunca
padrão — evita reanimar em remontagens frequentes como itens de lista filtrada) e ícone
reagindo com escala+rotação no próprio hover. `AnimatedNumber` não foi alterado (pedido
explícito do usuário: "números mantendo o padrão já existente"). Ripple foi
deliberadamente descartado (inconsistente com a estética "confiança silenciosa" já
estabelecida, mesmo raciocínio que rejeitou "shake" em erro de validação na F5). `/dev`
ganhou seções novas para a galeria de `InstitutionBadge`, o `ThemeToggle` e os estados de
hover de `Button` — o resto das microinterações já é visível em qualquer componente
existente na própria página (é passar o mouse). Validado com `tsc -b` + `vite build`
limpos.

**Etapa F7 concluída** (CRUD de Categoria — segunda entidade real; análise arquitetural
prévia em `docs/analise-arquitetural-categoria-frontend.md`, revisão técnica em
`docs/revisao-tecnica-categoria-frontend.md`): contrato lido direto de
`app/models/categoria.py`, `app/schemas/categoria.py`, `app/services/categoria_service.py`,
`app/repositories/categoria_repository.py` e `app/api/routes/categoria.py`. Duas
complexidades sem precedente em Conta — hierarquia autorreferenciada
(`categoria_pai_id`) e duas camadas de permissão distintas (visibilidade via 404
anti-enumeração, igual Conta; editabilidade de categoria de sistema via 403,
`AcessoNegadoError`, nova) — resolvidas sem nenhum componente de árvore visual: a tabela
ganha uma coluna "Categoria pai" resolvida por lookup em memória contra a lista já
carregada, e `CategorySelect` (primeiro select "inteligente" de domínio do projeto,
previsto desde a F1) rotula cada opção com a cadeia de ancestrais (`"Moradia > Aluguel"`)
e exclui a própria categoria e seus descendentes das opções de pai no modo edição —
filtro de UX; o anti-ciclo de verdade continua 100% no backend. Achado que exigiu parar e
perguntar antes de implementar (registrado em `docs/analise-arquitetural-categoria-frontend.md`,
seção 0): os campos `cor`/`icone` não tinham nenhum campo equivalente no Form System, e o
backend não impõe convenção nenhuma para `icone` (string livre, sem seed) — o usuário
escolheu `IconField` (registry curado de ~30 ícones `lucide-react` em `lib/icons.ts`,
mesmo princípio de registry único de `lib/institutions.ts`, sem switch/case) e `ColorField`
(swatch + hex + paleta de sugestão), os dois novos em `components/ui/`, reutilizáveis pela
Tag no futuro. `corDeContraste` foi extraída de `lib/institutions.ts` para `lib/color.ts`
(compartilhada agora por `InstitutionBadge` e o novo `CategoryBadge`, sem duplicação).
Categoria de sistema: `CategoriaFormDialog` força modo leitura mesmo se aberto para
edição, e as ações "Editar"/"Desativar" ficam escondidas na tabela — UX proativa, o
backend segue sendo a fonte de verdade (403 se contornado). Validado com `tsc -b` +
`vite build` limpos e um smoke test real contra um backend descartável isolado (SQLite
temporário, nunca o `financas.db` real): registro, login, categoria de sistema inserida
manualmente e confirmada como somente leitura (403 ao tentar `PATCH`), criação de
categoria própria com hierarquia pai/filho, bloqueio de desativação com subcategoria
ativa (422), bloqueio de autorreferência (422), desativação e reativação (`PATCH
{ativo:true}`) e filtro `apenas_ativas` — todas as regras de negócio documentadas na
análise arquitetural se comportaram exatamente como esperado.

**Refinamento de UI concluído** (revisão crítica de UX/UI/Performance/Responsividade sobre
`/contas`, `/categorias`, `Dashboard`, `Sidebar`/`Header` e o sistema de tabelas —
nenhuma funcionalidade nova, ver `docs/revisao-tecnica-refinamento-ui.md`): dois bugs reais
encontrados e corrigidos, não só polimento visual. Primeiro, `Sidebar` é `hidden` abaixo de
`md` e não existia nenhum substituto — o app ficava sem navegação nenhuma no celular;
corrigido com `MobileNav` (painel deslizante, `NAV_ITEMS` extraído para
`components/layout/navItems.ts` e compartilhado entre os dois) e um botão de menu novo em
`Header`. Segundo, `ColumnDef.hideOnMobile` existia no tipo e era usado por
`categoriaTableColumns`/`contaTableColumns`, mas `DataTable` nunca aplicava esse filtro no
card mobile — corrigido (`mobileColumns` derivado de `visibleColumns`). Performance
percebida: o `<motion.tbody>` de `DataTable` usava a busca crua (`table.query`, não
`deferredQuery`) como parte da `key` de remontagem — cada tecla digitada remontava a
tabela inteira com fade, mesmo com `useDeferredValue` no hook; a `key` não inclui mais a
busca. `useCategorias`/`useContas` ganharam `placeholderData: keepPreviousData` — alternar
"mostrar inativas" não pisca mais um skeleton cheio. Hierarquia de Categoria: a listagem
agora ordena pai-then-filhos por padrão (`ordenarCategoriasPorHierarquia`) e a coluna
"Nome" indenta subcategorias com um conector (`CornerDownRight`) e a contagem de
subcategorias diretas, sem badge escrito "Pai". Áreas de toque: `RowActions` ganhou um
`size` opcional, usado como `md` (36px) no card mobile em vez do `sm` (28px) fixo de antes.
`TableCell` foi de `px-3 py-2.5` para `px-4 py-3` (menos apertado). Validado com `tsc -b` +
`vite build` limpos.

**Etapa F8 concluída** (CRUD de Tag — terceira entidade real; análise arquitetural prévia
em `docs/analise-arquitetural-tag-frontend.md`, revisão técnica em
`docs/revisao-tecnica-tag-frontend.md`): contrato lido direto de `app/models/tag.py`,
`app/schemas/tag.py`, `app/services/tag_service.py`, `app/repositories/tag_repository.py`
e `app/api/routes/tag.py`. A entidade mais simples do CRUD até agora — sem hierarquia, sem
"tag do sistema", sem `tipo`, sem `icone` — resultou na primeira etapa 100% composição:
nenhum componente novo do Form System (`ColorField`, criado na F7 já prevendo este
reaproveitamento, cobre `cor` sem nenhuma adaptação) e nenhuma extensão de `DataTable`,
`FormDialog` ou qualquer outra infraestrutura compartilhada. Único componente de domínio
novo: `TagBadge` (pill colorido, `rounded-full`, análogo a `CategoryBadge` mas sem ícone).
Achado de implementação registrado na análise: o backend usa `ConflictError` → 409 para
nome duplicado (primeiro uso desse status num CRUD de entidade — Conta e Categoria não têm
restrição de unicidade de nome), mas o tratamento já existia desde a F1 (mesmo caminho do
e-mail duplicado em `RegistrarPage.tsx`) — nenhum código novo de erro necessário. Nuance de
negócio documentada e validada: se o nome colidir com uma tag **desativada** do mesmo
usuário, o backend reativa a existente e sobrescreve `cor` em vez de rejeitar; se colidir
com uma tag **ativa**, é 409 puro — confirmado via smoke test real (`POST` duplicado ativo
→ 409; desativar → `GET ?apenas_ativas` reflete corretamente; `POST` com nome de tag
desativada → reativa com a cor nova; `PATCH {ativo:true}` também reativa, preservando a
cor). `useTagQueries.ts` já nasceu com `placeholderData: keepPreviousData` desde o primeiro
commit (Categoria/Conta só ganharam isso numa etapa de correção posterior). Item de
navegação usa o ícone `Tags` (plural) em vez de `Tag` (singular) para não colidir
visualmente com o ícone já usado por "Categorias" no mesmo menu. Validado com `tsc -b` +
`vite build` limpos e smoke test real contra um backend descartável isolado (SQLite
temporário, nunca o `financas.db` real).

**Organização da Sidebar concluída** (melhoria de UX global, não é uma etapa de CRUD de
entidade; análise arquitetural prévia em
`docs/analise-arquitetural-organizacao-sidebar.md`, revisão técnica em
`docs/revisao-tecnica-organizacao-sidebar.md`): permite reordenar por drag-and-drop os itens
de navegação (Contas, Categorias, Tags, e qualquer entidade futura), com "Dashboard" sempre
fixo em primeiro. Acesso via `UserMenu` → "Organizar navegação" (abaixo do toggle de tema),
abrindo um modal que reaproveita `FormDialog` inteiro como casca (foco preso, fluxo de
"descartar alterações?" via `isDirty` — decoupled de RHF por design, primeira vez que esse
desacoplamento foi exercido na prática). Reordenação usa `Reorder.Group`/`Reorder.Item` do
`motion` (já instalado, nenhuma dependência nova), com alternativa completa por teclado
(botões "mover para cima"/"para baixo" em cada item, já que `Reorder` não tem suporte nativo
a gestos de teclado). Novo `NavOrderContext`/`NavOrderProvider` (mesmo formato de
`ThemeContext`) resolve a sincronização entre `Sidebar`/`MobileNav` (consumidores) e o modal
(gatilho da mudança) — ramos irmãos da árvore, sem relação pai-filho. Persistência é só um
array de rotas em `localStorage` (chave `financas:ordem-navegacao`), nunca a lista de itens
inteira — a reconciliação com `navItems.ts` acontece a cada leitura, então uma página nova
adicionada no futuro aparece automaticamente ao final da navegação de todo usuário que já
personalizou a ordem, sem nenhuma mudança de código além da própria linha nova em
`navItems.ts` (já era assim antes desta etapa). Validado com `tsc -b` + `vite build` limpos.

**Expansão de ícones e cores concluída** (pedido do usuário, sem etapa formal própria):
`lib/icons.ts` (registry de `IconField`/`CategoryBadge`, F7) cresceu de ~32 para ~80 ícones
`lucide-react` curados, organizados em grupos comentados (Moradia, Transporte, Alimentação,
Compras, Saúde, Educação, Lazer e cultura, Família e relacionamentos, Tecnologia, Trabalho e
finanças). `lib/color.ts` (`PALETA_SUGESTAO` de `ColorField`, também F7) cresceu de 10 para
43 tons, reorganizados em ordem de arco-íris linear de verdade (ROYGBIV — vermelho → laranja
→ amarelo → verde → azul → índigo/violeta → magenta/rosa, 2-5 tons por faixa de matiz antes
de passar para a próxima cor), com neutros (branco, três cinzas, preto) e o accent da marca
fora do espectro, ao final. `ColorField` ganhou `max-h-56 overflow-y-auto` no popover de
swatches para acomodar a paleta maior. Validado com `tsc -b` + `vite build` limpos.

**Ajustes de UX/UI + Etapa F9 (CRUD de Cartão) concluídos** — pedido pelo usuário como um
único bloco de trabalho, antes de qualquer código de Cartão ser escrito ("análise
arquitetural rápida" prévia confirmou que nenhum item exigia alterar a arquitetura já
aprovada; ver `docs/analise-arquitetural-cartao-frontend.md` para a análise da entidade e
`docs/revisao-tecnica-cartao-frontend.md` para o detalhamento completo desta etapa):

- **Escala global da interface** (~20% maior): `--ui-scale: 1.2` em `index.css` escala
  tipografia (seção 7 do design-system) e radius (seção 9) via valor já embutido no px de
  cada token; espaçamento/altura/largura (`p-*`/`gap-*`/`h-*`/`w-*`) escala com o MESMO
  multiplicador em `tailwind.config.js` (`theme.spacing` sobrescrito a partir de
  `tailwindcss/defaultTheme` × `UI_SCALE`, fora do `extend` de propósito) — nenhum componente
  precisou de alteração individual, a escala inteira do Design System cresceu no token.
- **`CartaoVisual`** (`components/domain/cartao/`) — cartão de crédito com visual de
  "carteira digital premium": proporção real (`aspect-[1.586/1]`), gradiente de marca da
  instituição (`lib/cardThemes.ts`, novo registry com variantes por instituição — ex. "Nubank
  Ultra", "Inter Black" — preferência por cartão persistida em `localStorage`, nunca
  enviada ao backend), tilt 3D + glow seguindo o mouse via `useMotionValue`/`useSpring`/
  `useMotionTemplate` do Framer Motion (nunca `useState` a cada `mousemove`), desligado sob
  `prefers-reduced-motion`. Dois `layout`s no mesmo componente: `"full"` (preview do
  formulário, card mobile automático do `DataTable`) e `"compact"` (linha da tabela em
  desktop, sem tilt — motion rico por linha prejudicaria performance/escaneabilidade).
- **`lib/bandeiras.ts` + `BandeiraBadge`** — mesmo espírito de `lib/institutions.ts`, mas
  para o enum fechado `Bandeira` (monograma sobre cor de marca real, sem SVG de logo
  embutido, mesma decisão de direitos de marca já tomada para instituições).
- **`AccountSelect`** (`components/domain/conta/`) — segundo select "inteligente" de domínio
  do projeto (`CategorySelect` foi o primeiro, F7), infraestrutura já prevista desde a F1 e
  só ativada agora que Cartão (`conta_pagamento_id`) precisou dela de verdade.
- **`ProgressBar`** ganhou uma prop `tone` (`accent`/`warning`/`negative`) — evolução do
  componente existente (não um paralelo) para o "progresso do limite" reagir à proximidade
  do limite (≥80%/≥100%).
- **CRUD de Cartão**: contrato lido direto de `app/models/cartao.py`, `schemas/cartao.py`,
  `services/cartao_service.py`, `repositories/cartao_repository.py`,
  `api/routes/cartao.py`. `limite_disponivel` é sempre calculado (nunca uma coluna, pode
  ficar negativo de propósito — cartão "estourado", nunca clampado em zero); reativação
  implícita ao recriar com nome de cartão desativado (mesmo padrão de Tag/Categoria);
  renomear nunca reativa, é 409 puro; `conta_pagamento_id` de outro usuário é 404
  (anti-enumeração). Camada de dados nova (`types/cartao.ts`, `schemas/cartao.ts`,
  `services/cartaoService.ts`, `queryKeys.cartoes`, `hooks/useCartaoQueries.ts` — mutations
  invalidam `dashboard.cartoes`/`dashboard.indicadores`, mesmo padrão de Conta). Página
  `/cartoes` (`pages/cartoes/CartoesPage.tsx`) é a primeira página de entidade com uma faixa
  de `MetricCard` de indicadores agregados no topo (limite total/utilizado/disponível,
  cartões ativos — calculados no cliente via `reduce` sobre a própria listagem já
  carregada, sem requisição nova), justificada pela natureza agregável do limite (Conta não
  tem equivalente natural). Busca inclui últimos 4 dígitos; filtro por bandeira.
- **Performance**: `lib/cardThemes.ts` ganhou um cache em memória da preferência de tema
  (evita `JSON.parse` de `localStorage` a cada linha da tabela a cada tecla digitada na
  busca); `useCartoes` já nasceu com `placeholderData: keepPreviousData`.

Validado com `tsc -b` + `vite build` limpos e um smoke test real contra um backend
descartável isolado (SQLite temporário, nunca o `financas.db` real): criação de conta e
cartão, `limite_disponivel` calculado corretamente, 409 de nome duplicado (criação e
renomeação — sem reativar no segundo caso), 404 anti-enumeração de `conta_pagamento_id` de
outro usuário, desativação, listagem `apenas_ativos=true/false`, reativação implícita
(recriar com mesmo nome, campos sobrescritos) e reativação explícita (`PATCH
{ativo:true}`) — todas as regras de negócio documentadas na análise arquitetural se
comportaram exatamente como esperado.

Próximas etapas (CRUD das demais entidades — Transação, Parcelamento, Transferência,
Conta Recorrente, Financiamento, Empréstimo, Meta, Anexo — mesmo padrão de F6/F7/F8/F9,
Fatura já concluída na F10 abaixo) documentadas em `docs/analise-arquitetural-frontend.md`,
seção 16 (números desatualizados ali — a ordem real já diverge, ver seção 0 de
`docs/analise-arquitetural-dashboard.md`) — nenhuma delas implementada ainda.

## 📈 Painel do projeto

`dashboard/` é uma página interna, separada do app, para acompanhar o progresso real do
desenvolvimento (áreas, roadmap, funcionalidades, kanban, changelog, arquitetura,
indicadores de qualidade). HTML/CSS/JS puro, sem build, dirigido inteiramente por
`dashboard/project-status.json` — atualizar o progresso é editar esse JSON, nunca o HTML.
Abrir com `dashboard/start-dashboard.bat` (Windows) ou `python -m http.server` na pasta;
ver `dashboard/README.md` para detalhes.

## 🎴 Etapa F9 (Cartão, frontend) + Revisão de UX/UI

Quarta entidade real do frontend (`Conta` → `Categoria` → `Tag` → `Cartão`), acompanhada de
ajustes de UX/UI que a antecederam (`CartaoVisual` — cartão físico com tilt 3D e glow no
hover, branding por instituição com múltiplas variantes de tema, `BandeiraBadge`,
`ProgressBar.tone`, escala global de tipografia/radius) — detalhes em
`docs/revisao-tecnica-cartao-frontend.md`.

Na sequência, antes de iniciar o próximo CRUD (Fatura), foi feita uma revisão de UX/UI de
toda a aplicação (Dashboard + Cartões), seguindo o mesmo padrão de "avaliar antes de
implementar" (não duplicar o que já está previsto para etapas futuras):

- **Overflow de valores no `StatCard`** (Saldo Total/Patrimônio Líquido) corrigido com
  tipografia adaptativa por comprimento do valor-alvo (`tamanhoValorHero`, `utils/format.ts`
  — nunca recalculada por frame do count-up) + grid ponderado de 12 colunas no
  `ResumoFinanceiroSection` (cards "hero" com mais largura). Deliberadamente **não** é
  redução uniforme de fonte.
- **Cartões evoluído** de "apenas um cadastro": barra de utilização por cartão (já existia
  via `CartaoVisual` na tabela, mantida), "faltam N dias" para fechamento/vencimento
  (substituindo o dia-do-mês cru), e um mini-histórico de faturas recentes na visualização de
  um cartão — reaproveitando `/central-financeira/faturas` (já existente), sem endpoint novo
  e sem duplicar a futura Etapa F10 (CRUD de Fatura).
- **Cartões no Dashboard**: `FaturasCard` agora identifica de qual cartão é cada fatura
  (cruzando com `/central-financeira/cartoes`); `CartoesCard` ganhou a mesma barra de
  utilização do `CartaoVisual`.
- **Bug real encontrado e corrigido**: o CTA "Criar conta" da tela de onboarding do Dashboard
  estava desabilitado com tooltip "Disponível em breve" desde antes da Etapa F6 — a página
  `/contas` já existe há várias etapas, então o botão mandava o usuário recém-cadastrado para
  lugar nenhum. Agora navega de verdade.
- **Contas → nova transação**: avaliado e confirmado que pertence naturalmente à Etapa F11
  (Transação) — não implementado agora para não duplicar trabalho.

`tsc -b` e `vite build` validados limpos após todas as mudanças.

## 🧾 Etapa F10 (Fatura, frontend) + Overlays/Pickers/Exclusão

Quinta entidade real do frontend (`Conta` → `Categoria` → `Tag` → `Cartão` → `Fatura`),
precedida por um pacote de 4 documentos arquiteturais aprovados com um ajuste do usuário:
Fatura não ficaria presa a um único Drawer de lista — o Cartão ganhou uma página de
detalhes própria (`docs/analise-arquitetural-fatura-frontend.md`,
`docs/analise-arquitetural-rich-pickers.md`, `docs/analise-arquitetural-exclusao.md`,
`docs/analise-arquitetural-overlays.md`, este último formalizado a pedido do usuário como
padrão único de overlays do projeto).

- **`docs/analise-arquitetural-overlays.md`** — documento canônico novo: dois tiers de
  overlay (Tier 1 — Tooltip/Popover/RichPicker/Context Menu, leves, não-bloqueantes, podem
  empilhar; Tier 2 — Dialog/Drawer/Command Palette, bloqueantes, mutuamente exclusivos) e a
  heurística "2 cliques ou mais/precisa de busca" promovida a regra canônica de qual overlay
  usar em cada entrada. `useDismissableOverlay`/`useIsMobileViewport`
  (`hooks/useDismissableOverlay.ts`) extraídos como hooks compartilhados, substituindo lógica
  de clique-fora/Esc duplicada em `IconField`/`ColorField`/`SearchSelect`.
- **`Drawer`** (`components/ui/Drawer.tsx`) — overlay ancorado à direita, reaproveita o
  padrão de focus-trap (`FOCUSABLE_SELECTOR`) do `FormDialog`; novo par de variantes de
  motion (`drawerBackdrop`/`drawerPanel`) em `lib/motion.ts`.
- **`RichPicker<T>`** (`components/ui/RichPicker.tsx`) — componente genérico novo (grid ou
  lista, agrupamento, busca acima de um `searchThreshold`, navegação por teclado, fallback
  para modal centralizado em mobile via `useIsMobileViewport`). Substitui a implementação
  ad-hoc que `IconField`/`ColorField` tinham cada uma a sua.
- **`IconPicker` + `ColorPicker`** — substituem `IconField`/`ColorField` (F7), agora
  compostos sobre `RichPicker`. `lib/icons.ts` e `lib/color.ts` ganharam um campo `grupo` em
  cada entrada para permitir filtro/agrupamento visual no picker. `ColorPicker` preserva o
  campo de texto livre (hex) ao lado do picker — nunca vira lista fechada.
- **`BankPicker` + `CardBrandPicker`** — novos pickers de domínio para `instituicao`
  (`Conta`/`Cartão`) e `bandeira` (`Cartão`). `BankPicker` preserva a mesma liberdade de
  texto livre do campo original via uma entrada especial "Outra instituição" que revela um
  `<input>` de texto — a instituição nunca se torna um enum fechado no backend.
  `CardBrandPicker` usa `layout="list"` (enum fechado, 7 itens, sem busca).
- **`SearchSelect`/`Select`** ganharam um slot visual (`render`) nos itens/gatilho;
  `CategorySelect` (F7) passou a usar esse slot para mostrar ícone + cor de cada categoria,
  mesmo visual de `CategoryBadge`, em vez de texto puro.
- **Exclusão definitiva (hard delete)** — nova ação em `Conta`/`Categoria`/`Tag`/`Cartão`,
  distinta da desativação (soft delete) já existente, seguindo
  `docs/analise-arquitetural-exclusao.md`: rota nova `DELETE /{entidade}/{id}/permanente`
  (nunca reaproveita o `DELETE /{entidade}/{id}` existente, que já significa "desativar").
  Regras de bloqueio por entidade — `Conta`: qualquer transação, transferência ou cartão
  vinculado; `Categoria`: qualquer transação vinculada OU qualquer subcategoria (ativa ou
  inativa); `Cartão`: qualquer fatura vinculada (qualquer status); `Tag`: nunca bloqueia,
  é só informativo (`GET /tags/{id}/uso` retorna a contagem de transações antes de excluir).
  13 testes novos no backend (3-4 por entidade: exclusão bem-sucedida, exclusão bloqueada
  com 422, 404 anti-enumeração), 85 testes de integração passando ao todo entre as 4
  entidades. Frontend: nova ação "Excluir" (sempre visível) em cada página de listagem, com
  `ConfirmAction` de aviso mais forte que a desativação, texto específico por entidade.
- **`CartaoDetalhePage`** (`/cartoes/:id`) — primeira página de DETALHES do projeto; todas
  as entidades anteriores usam só `FormDialog` para visualizar/editar. Layout em duas
  colunas: `CartaoVisual` + ações (Editar/Desativar-Reativar/Excluir) + `MetricCard`s à
  esquerda, lista inline de Faturas (com mini-formulário "Nova fatura",
  `<input type="month">`) à direita — cada fatura clicada abre um `FaturaDrawer`. Ação "Ver
  detalhes" nova na tabela `/cartoes` (`ArrowUpRight`), ao lado de "Ver" (que continua
  abrindo o modal rápido). `CartaoFormDialog` perdeu o mini-histórico de faturas que tinha
  em modo de visualização (`FaturasDoCartao`) — a página de detalhes já mostra a lista
  completa, sem duplicar a mesma informação em dois lugares.
- **CRUD de Fatura** — sem `PATCH` (campos imutáveis por natureza), só endpoints de ação:
  `fechar` (congela `valor_total`), `registrarPagamento`, e exclusão definitiva (sempre hard
  delete, nunca existiu soft delete para Fatura). Camada de dados nova (`types/fatura.ts`,
  `schemas/fatura.ts`, `services/faturaService.ts`, `queryKeys.faturas`,
  `hooks/useFaturaQueries.ts` — mutations invalidam o prefixo `["faturas"]` inteiro mais
  `dashboard.faturas`/`dashboard.cartoes`/`cartoes.detail`). `FaturaDrawer` mostra detalhe
  (fechamento/vencimento/valor total/valor pago) e ações condicionais ao `status`
  (Fechar ciclo só quando `ABERTA`, Registrar pagamento quando não `ABERTA`, Excluir sempre).

Validado com `tsc -b` e `vite build` limpos (build de produção: 2512 módulos, ~720 KB no
bundle principal), suíte de testes de integração do backend (Conta, Categoria, Tag, Cartão)
rodando 100% verde após as mudanças de exclusão.

## 🪪 Revisão de UX — Módulo de Cartões (produto final)

Pedido explícito do usuário, depois da F10: elevar o módulo de Cartões de "parece um CRUD"
para "produto financeiro profissional" — análise completa em
`docs/analise-arquitetural-revisao-ux-cartoes.md`. Zero mudança de regra de negócio ou de
API; só apresentação. Zero impacto nas outras 13 entidades (Conta/Categoria/Tag continuam
`DataTable`, decisão deliberada, ver `design-system.md` seção 18).

- **`/cartoes` migrou de `DataTable` para um grid de `CartaoResumoCard`** — um cartão passou a
  ser tratado como um "mini dashboard" clicável em vez de uma linha de registro. O card
  inteiro navega para a página de detalhes ao clicar em qualquer área livre (`role="link"` +
  teclado, nunca um `<a>` envolvendo os botões da Action Bar — seria HTML inválido). Ordem de
  leitura dentro do card: identidade + utilização (`CartaoVisual`) → "Disponível" em destaque
  (`AnimatedNumber`) → próxima fatura resumida → chip de alerta (só quando exige ação) →
  `CartaoActionBar`. As ações "Ver" (modal) e "Ver detalhes" somem — o clique no card já é a
  navegação, e `CartaoFormDialog` perdeu o modo somente-leitura (serve só para criar/editar).
- **`CartaoActionBar`** (nova, compartilhada entre o card do grid e a página de detalhes) —
  Editar/Faturas/Desativar-Reativar/Excluir sempre com ícone + texto, nunca escondidas atrás
  de um menu. "Faturas" (só no card do grid) navega para `/cartoes/:id#faturas`, que rola até
  a seção — sem duplicar a lógica de fechar/pagar fatura em dois lugares.
- **Correção de auditoria**: a barra de utilização usava `--color-accent` (roxo da marca) para
  o estado "saudável" — violação de uma regra dura do Design System (`--color-accent` é
  reservado para interação, nunca para dado financeiro, seção 6.3). `ProgressBar` ganhou o
  tone `"positive"` (verde, mesmo token de saldo positivo/fatura paga), corrigido em
  `CartaoVisual` **e** no `CartoesCard` do Dashboard (mesma cor nas duas telas para o mesmo
  cartão).
- **`CartaoDetalhePage` reorganizada** na ordem "qual cartão → quanto posso gastar →
  utilização → próxima fatura → ações rápidas → faturas → informações do cartão → histórico":
  novo `ProximaFaturaCard` (fatura mais relevante em destaque, com atalho para abrir o
  `FaturaDrawer` já na ação certa), nova seção "Informações do cartão" (instituição, bandeira,
  dias de fechamento/vencimento, conta de pagamento — antes só existiam dentro do formulário
  de edição) e uma seção "Histórico" com placeholder documentado (depende do CRUD de
  Transação, nenhuma lógica provisória).
- **Correção de performance real** (lentidão reportada pelo usuário): o tilt 3D do
  `CartaoVisual` recalculava `getBoundingClientRect()` a cada pixel de movimento do mouse,
  forçando reflow de layout repetidamente — a causa da travadinha ao passar o mouse sobre o
  cartão no formulário e na página de detalhes. Corrigido: o rect agora é lido uma única vez
  por hover (`onMouseEnter`), nunca por `mousemove`.
- **`cartaoTableColumns.tsx` removido** (sem consumidor após a migração do grid);
  `CartaoVisual layout="compact"` removido junto (mesmo motivo).

Validado com `tsc -b` e `vite build` limpos (2515 módulos, ~726 KB no bundle principal).

## 🎨 Sistema semântico de status (refinamento reutilizável)

Pedido explícito do usuário: formalizar um padrão de cores/status para o projeto INTEIRO
(não só Cartões), antes de iniciar o CRUD de Transação. Zero mudança de regra de negócio ou
API. Toda a lógica nova vive em `utils/status.ts` e três componentes novos em `components/ui/`
— nenhum deles tem uma linha de código específica de Cartão, pensados para Transação,
Parcelamento, Conta Recorrente, Financiamento, Empréstimo e Meta reaproveitarem depois.

- **Novo tone `info` (azul, `--color-info` `#38BDF8`)** — quarta cor semântica (ao lado de
  positive/negative/warning), para o estado "em andamento, sem alerta" que antes caía em
  `neutral` por falta de opção (`ABERTA`/`ATIVO` em `FinancialBadge`). Mesmo azul já usado como
  `--color-chart-2`, promovido a semântico — nenhuma cor nova sem precedente no Design System.
- **`utils/status.ts`** — duas funções puras reutilizáveis: `tonePorUtilizacao(percentual)`
  (limite/orçamento: positive < 80% ≤ warning < 100% ≤ negative) e `tonePorPrazo(dias)`
  (urgência de prazo: negative ≤ 1 dia, warning ≤ 7 dias, info daí em diante). Substituem os
  ternários duplicados que `CartaoVisual`/`CartaoResumoCard`/`CartoesCard` (Dashboard) tinham
  cada um o seu.
- **`StatusChip`** (novo) — pill de fundo SÓLIDO com contraste garantido por token dedicado
  (`--color-text-on-positive/negative/warning/info`), para informação desenhada sobre um fundo
  que o componente não controla. Resolve o problema relatado: "Vence em X dias" dentro do
  `CartaoVisual` herdava a cor de texto do tema do cartão e podia perder destaque dependendo da
  cor escolhida — agora tem cor própria, sempre legível, em qualquer cartão.
- **`StatusDot`** (novo) — microindicador (ponto colorido de 6px), sempre ao lado de texto,
  nunca sozinho como única informação.
- **`AtivoBadge`** (novo) — unifica o `<Badge tone={x.ativo ? "positive" : "neutral"}>`
  duplicado em `Conta`/`Categoria`/`Tag`/`Cartão` num componente só, com rótulos parametrizáveis
  para concordância de gênero.
- **Achado de auditoria real: `corDeContraste` (`lib/color.ts`) tinha um bug de contraste** — a
  fórmula usava um limiar de luminância sem correção de gama (aproximação, não a fórmula real do
  WCAG). Teste completo contra as 43 cores de `PALETA_SUGESTAO` mostrou 11 casos em que a
  fórmula antiga recomendava o texto de PIOR contraste (ex. `#fb7185`: recomendava branco a
  2.69:1, que reprova AA, quando preto dá 7.31:1). Corrigido para calcular a razão de contraste
  WCAG real contra preto e branco e escolher a maior — mesma assinatura, benefício automático
  para `InstitutionBadge`/`BandeiraBadge`/`CategoryBadge`/preview do `ColorPicker`.
- **`FinancialBadge`**: `ABERTA`/`ATIVO` migraram de `neutral` para `info`.

Validado com `tsc -b` e `vite build` limpos (2519 módulos, ~727 KB no bundle principal) e a
suíte de testes de integração do backend (Conta, Cartão) 100% verde (nenhuma mudança de
backend nesta etapa).

## 🔁 Etapa F11 (Transação, frontend) — sexta entidade real do frontend

Sexta entidade de domínio do frontend (Conta, Categoria, Tag, Cartão, Fatura, agora
Transação — 6 de 14) e, segundo o pedido explícito, "um dos pontos altos do projeto": a
tela mais usada do aplicativo, não apenas uma tabela. Zero mudança de regra de negócio ou
API — arquitetura completa em `docs/analise-arquitetural-transacao-frontend.md`.

- **Filtragem híbrida (primeira do projeto)** — toda entidade anterior filtra/pagina/ordena
  100% no cliente (`useDataTable`), premissa que quebra em Transação: lançamentos acumulam
  de verdade. `/transacoes` sempre envia um período (`PeriodoSeletor`, reaproveitado do
  Dashboard) e, opcionalmente, tipo/status/categoria como parâmetros REAIS de
  `GET /transacoes` — o backend filtra de verdade, refetch a cada mudança. Só o resultado já
  filtrado (dezenas de linhas por mês, não centenas) entra no `DataTable`, que continua
  cuidando de busca textual/ordenação/paginação de exibição, sem nenhuma mudança em
  `useDataTable`/`DataTable` em si.
- **Origem Conta × Cartão** — seletor segmentado (dois botões) decide qual dos dois selects
  aparece (`AccountSelect` ou o novo `CardSelect`), resolvendo o XOR que o backend exige sem
  jamais mostrar os dois campos ao mesmo tempo. Imutável na edição (o backend não aceita
  `conta_id`/`cartao_id` em `TransacaoUpdate`) — os dois botões e o select ficam desabilitados
  fora da criação, com texto explicando por quê.
- **`CardSelect`** (novo, `components/domain/cartao/`) — espelha `AccountSelect` quase
  literalmente, com `InstitutionBadge`+`BandeiraBadge` como slot visual de cada opção.
- **`TagMultiSelect`** (novo, `components/domain/tag/`) — camada de domínio sobre o
  `MultiSelectField` genérico; cada chip selecionado é um `TagBadge` de verdade (cor real da
  tag). `MultiSelectField` ganhou uma prop `renderChip` para isso, sem duplicar a mecânica do
  popover.
- **`CategorySelect` ganhou filtro por tipo** — nova prop opcional `tipoTransacao` restringe
  as opções a categorias compatíveis (`RECEITA`/`DESPESA`/`AMBOS`), evitando o usuário
  escolher uma categoria de Despesa numa transação de Receita (filtro de UX; a validação real
  continua no backend). Trocar o tipo depois de já ter escolhido uma categoria incompatível
  limpa a seleção automaticamente.
- **`status` só aparece editável quando a origem é Conta** — em Cartão o backend sempre força
  `PAGO` (a Fatura é a autoridade real), então o formulário nem mostra o controle nesse caso.
- **`TransacaoResumoPeriodo`** (novo) — reaproveita `GET /central-financeira/visao-mensal`
  (já usado pelo Dashboard) para "Receitas/Despesas/Saldo do período", em vez de somar as
  transações já carregadas no cliente — mesma filosofia de `somar_por_periodo` no backend
  preferir `SUM` no banco a somar em Python.
- **Invalidação de cache mais ampla do projeto** — uma transação nova, editada ou excluída
  pode mudar saldo de Conta, limite de Cartão e/ou Fatura, então toda mutation invalida
  praticamente todo o Dashboard (`resumo`, `saldoConsolidado`, `contas`, `cartoes`,
  `faturas`, `visaoMensal`, `agenda`, `indicadores`), além de `contas.detail`/
  `cartoes.detail` da origem específica quando conhecida.
- **Campos de vínculo futuro documentados e propositalmente NÃO implementados** —
  `parcelamento_id`/`financiamento_id`/`emprestimo_id`/`numero_parcela`/
  `origem_recorrente_id`/`meta_id` existem em `types/transacao.ts` (espelhando o backend
  fielmente), mas nenhum formulário os envia: nenhuma dessas cinco entidades tem CRUD/tela
  própria ainda, e expor um campo de ID cru seria pior do que não expor nada. Extensão
  aditiva quando cada entidade ganhar seu CRUD.
- **Sem "desativar"** — `Transacao` é lançamento de livro-razão real, sem soft delete; a
  única ação de remoção é `DELETE /transacoes/{id}`, sempre definitiva.

Validado com `tsc -b` e `vite build` limpos, sem nenhuma mudança de backend nesta etapa.

## 🎛️ Refinamento de Pickers/Performance + Pagamento de Fatura (pós-F11)

Etapa exclusivamente de UX/performance/polimento, pedida antes do próximo CRUD. Duas frentes
paralelas, zero mudança de regra de negócio ou API em ambas — arquitetura completa em
`docs/analise-arquitetural-refinamento-pickers-performance.md` e
`docs/analise-arquitetural-refinamento-fatura-pagamento.md`.

**Pickers e performance geral:**

- **Causa raiz identificada antes de qualquer código** — os Pickers (`RichPicker`,
  `SearchSelect`, `MultiSelectField`, `Select`, `ColumnVisibility`) usavam `position: absolute`
  dentro do `overflow-y-auto` de um `FormDialog`, sendo cortados ("scroll dentro de scroll").
  Corrigido com um hook novo, `useFloatingPanel` (`hooks/useFloatingPanel.ts`): calcula a
  posição via `getBoundingClientRect()` do gatilho e renderiza o painel com `position: fixed`,
  portalado direto em `document.body`. Portal é necessário (não bastaria só trocar para
  `fixed` no lugar) porque o painel do `FormDialog` anima `scale` via Framer Motion, e um
  `transform` em qualquer ancestral cria um novo *containing block* que invalidaria as
  coordenadas do `getBoundingClientRect()`. `useDismissableOverlay` ganhou um parâmetro
  `extraRefs` para o clique dentro do próprio painel portalado não ser tratado como "fora".
- **Grade do `RichPicker`** — 6→10 colunas, células maiores (40px→44px), painel com largura
  fixa (560px grade / 400px lista, independente da largura do gatilho) e altura até
  `min(70vh, 480px)`. Dimensionado a partir da contagem real de registros do projeto (77
  ícones, 44 cores, ~20 instituições, 7 bandeiras).
- **Destaque de busca** (`utils/highlight.tsx`) — trecho que casa com a busca aparece em
  `<mark>` em `RichPicker` (lista) e `SearchSelect`.
- **Auditoria de performance real (antes de otimizar, não especulação)** — zero
  code-splitting existia no projeto inteiro; `vite build` já acusava um chunk único de 741KB.
  Corrigido com `React.lazy()` por rota em `routes/AppRoutes.tsx` (Sidebar/Header nunca
  desmontam, só o conteúdo da página) e import dinâmico do `ReactQueryDevtools` condicionado a
  `import.meta.env.DEV` (eliminado do bundle de produção). Depois da mudança, o maior chunk de
  página isolado fica na casa de 5-23KB; um chunk principal (~509KB) concentra as dependências
  compartilhadas (React, React Query, Framer Motion, React Hook Form, Zod) — candidato natural
  a uma futura divisão manual de vendor chunks, não feita agora por não haver evidência de que
  seja o gargalo real hoje. Nenhum `React.memo`/`useCallback` especulativo foi adicionado —
  nenhum ponto do projeto (fora de Context providers) apresentou evidência real de re-render
  custoso.

**Pagamento de Fatura:**

- **Bug real de invalidação corrigido** — `FaturaService.registrar_pagamento` sempre criou
  uma `Transacao` de despesa de verdade (vinculada via `fatura_paga_id`), mas nada invalidava
  `transacoes.*`/`contas.detail`/a maior parte do Dashboard depois de um pagamento — exigia F5
  manual para o saldo da conta e o extrato refletirem. `invalidarTransacoes`
  (`useTransacaoQueries.ts`) passou a ser exportada e reaproveitada por `useRegistrarPagamento`
  (`useFaturaQueries.ts`), sem duplicar a lista de invalidações.
- **Atalhos "Pagar total"/"Pagar restante"** (`FaturaDrawer`) — preenchem o campo de valor; o
  payload enviado é idêntico ao de qualquer valor digitado à mão (o backend aceita qualquer
  `valor > 0` na mesma rota, sem distinguir total/parcial/personalizado).
- **Preview client-side não-autoritativo** (`utils/fatura.ts`, `preverStatusPosPagamento`) —
  espelha a mesma prioridade de status que o backend usa (`_derivar_status`) para mostrar,
  durante a digitação, como a fatura ficará após o pagamento. Nunca persistido.
- **Densidade proposital** — valor pago/restante e uma `ProgressBar` de quitação agora
  aparecem tanto no `ProximaFaturaCard` quanto no `FaturaDrawer`, sempre visíveis (não só
  dentro do formulário de pagamento) — reflete a diretriz explícita de priorizar quem usa o
  sistema todo dia.

Validado com `tsc -b` e `vite build` limpos, sem nenhuma mudança de backend nesta etapa.

## 🛠️ Estabilização e Polimento de Overlays (pós-F11)

Etapa exclusivamente de correção de bugs e consistência — sem funcionalidade nova, sem
mudança de regra de negócio ou API. Arquitetura completa em
`docs/design-system.md`, seção 28.

**Bug crítico relatado (ColorPicker/IconPicker "tela fica praticamente toda preta") — causa
raiz identificada, não corrigida por tentativa:** `RichPicker`, em viewport móvel (abaixo de
768px), renderizava seu próprio backdrop (`bg-bg/60 backdrop-blur-lg`) — idêntico ao do
`FormDialog` que já o contém — empilhado por cima. Dois véus de 60% de opacidade + blur juntos
compõem para ~84%, cobrindo até o conteúdo do próprio `FormDialog`. Violava a regra que o
projeto já tinha documentado (`docs/analise-arquitetural-overlays.md`: Tier 1 nunca tem
backdrop, Tier 2 nunca empilha sobre Tier 2). Corrigido removendo o escurecimento do wrapper
mobile do `RichPicker` — confirmado por auditoria que `RichPicker`/`ColorPicker`/`IconPicker`/
`BankPicker`/`CardBrandPicker` são usados 100% das vezes dentro de um `FormDialog` já aberto,
nunca de forma autônoma, então a tela já estava escurecida por ele.

**Segunda instância do mesmo bug, em qualquer viewport:** `FaturaDrawer` abria um
`ConfirmAction` (backdrop próprio) para "Fechar ciclo"/"Excluir fatura" com o próprio `Drawer`
já aberto — mesmo empilhamento de dois backdrops Tier 2. Esta é provavelmente a causa real de
"não consigo registrar movimentações pela Fatura" relatada: o pagamento já havia sido
implementado no Refinamento anterior, mas o fluxo passa por "Fechar ciclo" primeiro, e
confirmar essa ação disparava o mesmo bug. Corrigido substituindo o conteúdo do `Drawer`
inline (mesma técnica que `FormDialog` já usa para "Descartar alterações?"), em vez de abrir
um `ConfirmAction` separado.

**Outras correções:**

- **`DateInput`** (usado por `DateField` — campo "Data" de Transação, "Data do pagamento" de
  Fatura) foi o único popover do projeto ainda com `position: absolute` e um `useEffect`
  próprio de clique-fora/`Esc` — esquecido na migração do Refinamento de Pickers/Performance.
  Migrado para `useFloatingPanel`, mesmo padrão de todos os outros.
- **Escala de z-index formal** (`--z-tier2: 50`, `--z-tier1: 60`, `--z-toast: 70` em
  `index.css`) — antes, todo overlay usava a mesma classe `z-50` solta, e Tier 1 aparecer acima
  de Tier 2 funcionava só por coincidência da ordem de montagem no DOM. Agora é garantia
  estrutural, incluindo toasts sempre acima de qualquer overlay aberto.

**Componentes revisados:** `RichPicker`, `ConfirmAction`, `FaturaDrawer`, `DateInput`,
`FormDialog`, `Drawer`, `SearchSelect`, `MultiSelectField`, `Select`, `ColumnVisibility`,
`Tooltip`, `ToastContext`, além de uma auditoria de consistência em `ContaFormDialog`/
`CartaoFormDialog`/`TagFormDialog`/`TransacaoFormDialog` (nenhum tinha overlay customizado
próprio ou `ConfirmAction` aninhado — só `FaturaDrawer` tinha esse padrão).

**Nenhuma limitação real de backend encontrada** — a integração Fatura↔Transação já existia
por completo desde o Refinamento anterior; o problema relatado era inteiramente de frontend
(o bug de empilhamento de overlays acima).

**Correção adicional (2ª rodada, achada por reprodução em vídeo em viewport desktop):** o
empilhamento de backdrop acima era um bug real, mas não era a causa raiz principal — o vídeo
mostrou o mesmo travamento em tela larga, onde aquele bug não se aplicava. A causa raiz de
verdade era um **loop infinito de render em `useFloatingPanel`**: `RichPicker`/
`ColumnVisibility`/`DateInput` passam uma função `panelWidth` inline (recriada a cada render),
e essa função estava nas dependências do `useCallback` interno do hook — cada render recriava
a função de recálculo, o que disparava o efeito de novo, que chamava `setRect` com um objeto
novo, gerando outro render, indefinidamente, até o React travar com "Maximum update depth
exceeded". Sem nenhum `ErrorBoundary` no projeto, esse erro derrubava a aplicação inteira (tela
em branco/preta, dependendo do tema). Corrigido guardando as opções numa `ref` e tornando a
função de recálculo estável para sempre. Esse era o bug que afetava TODO uso de
`ColorPicker`/`IconPicker`/`BankPicker`/`CardBrandPicker`/`ColumnVisibility`, em qualquer
viewport — desde que o hook foi criado no Refinamento de Pickers/Performance.

Adicionado também um `ErrorBoundary` de topo (`components/layout/ErrorBoundary.tsx`), inédito
no projeto: não previne bugs futuros, mas garante que uma exceção de render não tratada nunca
mais derrube a aplicação inteira em silêncio.

Validado com `tsc -b` e `vite build` limpos.

## 🧭 Refinamento de UX, Onboarding, Dashboard e Cartões

Etapa de polimento de produto (não uma etapa de CRUD novo), pedida explicitamente como
"pense como um Product Designer, não apenas como um desenvolvedor". Documento de arquitetura
prévio (`docs/analise-arquitetural-refinamento-ux-dashboard-cartoes.md`) cobrindo 13 frentes,
aprovado antes de qualquer código — mesma convenção de sempre.

**Dashboard como hub de navegação.** Cada `StatCard`/card de domínio/evento da Agenda Financeira
agora navega para a tela mais próxima do dado, sem nenhum botão novo visível — o próprio card é
a superfície clicável (`role="link"` + teclado, mesmo padrão já usado em `CartaoResumoCard`).
Saldo total/Patrimônio líquido → `/contas`; Entradas/Saídas/Fluxo de caixa → `/transacoes`;
Contas/Saldo por conta → `/contas`; cada linha de Cartões/Faturas → `/cartoes/:id`; eventos da
Agenda → a rota do `origem_tipo` quando resolvível sem uma chamada extra (`CONTA`, `CARTAO`,
`TRANSACAO`). Metas/Financiamentos/Empréstimos **permanecem sem link** — nenhuma dessas três
entidades tem rota própria no frontend ainda (só existem via Central Financeira, sem CRUD/tela
dedicada); documentado como deferido até essa etapa acontecer, não uma meia-solução.

**Fusão Entradas × Saídas.** `VisaoMensalCard` (seção própria de 8 colunas, duas barras grandes)
duplicava visualmente os mesmos três números que já apareciam no Resumo Financeiro logo acima
(`entradas_mes`/`saidas_mes`/`fluxo_caixa_mes` vs. `entradas`/`saidas`/`fluxo_caixa` de
`visao-mensal` — mesmo dado, dois endpoints, já documentado como intencional desde a Etapa F3).
Removido como seção própria; a comparação virou uma mini-barra compacta embutida no rodapé do
`StatCard` "Fluxo de caixa" — reduz uma seção inteira do grid sem perder a informação.

**Cards mais inteligentes.** `MetasCard` ganhou cor por urgência de prazo (`tonePorPrazo`, mesma
régua semântica já usada em Cartões) no campo de prazo da meta.

**Categorias padrão do sistema.** Nova migração Alembic (dado, não schema) insere 13 categorias-pai
+ subcategorias com `usuario_id = NULL` (Alimentação, Transporte, Moradia, Saúde, Educação, Lazer,
Compras, Pets, Assinaturas, Investimentos, Presentes, Trabalho, Renda). A arquitetura de "categoria
de sistema" já existia no `model Categoria` desde o início do projeto (`usuario_id` nulo =
compartilhada por todos, `CategoriaService` já tratava visibilidade/edição corretamente) — só nunca
tinha sido populada. Migração idempotente (não duplica se já houver categoria de sistema). Usuário
continua podendo editar/desativar/criar categorias próprias normalmente.

**Correção de inconsistência real.** Um `TODO(categoria-em-uso)` em `CategoriaService.desativar()`,
escrito antes do CRUD de Transação existir, propunha bloquear a desativação de uma categoria com
transação vinculada. Revisitado agora que Transação existe: a conclusão é que esse bloqueio **não**
deveria ser adicionado — `ContaService.desativar()` (mesmo padrão) também nunca bloqueia por
transação vinculada, e é o próprio objetivo do soft delete permitir que uma categoria em uso
histórico saia das listas de escolha sem apagar nada (`Transacao.categoria_id` é `ondelete=SET
NULL`, não `CASCADE`). TODO removido, nenhuma regra nova adicionada.

**Onboarding: sugestão de próximo passo.** Quando o usuário já tem ao menos uma Conta mas nenhum
Cartão ainda, um banner leve e dispensável por natureza (não modal, não bloqueia nada) sugere
"Cadastre seu primeiro cartão" com link direto — evita o usuário voltar ao Dashboard e só ver
cards vazios sem saber o que fazer a seguir.

**Ajuste de saldo inicial de fatura.** Novo botão em `/cartoes/:id` ("Registrar saldo já gasto
neste cartão") abre o `TransacaoFormDialog` já existente, pré-preenchido (cartão atual, tipo
despesa, descrição sugerida "Saldo inicial (ajuste)") — permite a quem já usava aquele cartão
antes de entrar no sistema registrar, num único lançamento, o quanto já está gasto no ciclo aberto,
sem precisar recriar compra por compra. Reaproveita 100% da `Transacao`/resolução de fatura aberta
já existentes; nenhum endpoint ou regra de negócio novos.

**Duas "limitações" investigadas — confirmadas como regras de negócio, não bugs.** (1) Não é
possível lançar uma transação num ciclo de fatura já fechado: `FaturaService.resolver_fatura_aberta`
rejeita isso de propósito (`valor_total` congelado no fechamento é um documento financeiro
histórico). (2) Não é possível excluir certas faturas: `FaturaService.excluir()` só permite excluir
fatura ainda `ABERTA` e sem nenhuma transação vinculada — proteção de histórico financeiro, mesmo
racional já aplicado à exclusão definitiva de Conta/Categoria/Tag/Cartão (Etapa F10). Nenhuma das
duas foi alterada.

**Identificado e explicitamente NÃO implementado (exige decisão de modelagem).** Importar uma
fatura já **fechada** de antes do usuário começar a usar o sistema (ex.: um ciclo anterior ainda
com saldo devedor) exigiria aceitar `status`/`valor_total` vindos do cliente na criação — hoje
`FaturaService.criar()` só sabe criar faturas `ABERTA`, com valores sempre calculados. Isso seria
uma mudança de regra de negócio real, então fica documentada e fora do escopo desta etapa,
aguardando uma decisão futura dedicada (`docs/analise-arquitetural-refinamento-ux-dashboard-cartoes.md`,
seção 6.4).

**Encontrado na auditoria, sinalizado para uma etapa futura.** O placeholder "Histórico de compras
deste cartão ficará disponível aqui quando o CRUD de Transação existir" em `CartaoDetalhePage` está
obsoleto — o CRUD de Transação já existe (Etapa F11) — mas implementar a listagem de verdade (com
paginação/filtro adequados) é maior que o escopo de polimento desta etapa; não implementado agora
para não improvisar uma versão incompleta.

Validado com `tsc -b`, `vite build` e os testes de backend relevantes (Categoria, Conta, Cartão,
Fatura, Transação, Central Financeira — todos passando) antes de considerar a etapa concluída.

## 🎨 Auditoria de Identidade Visual — harmonização de paleta

Pedido: a paleta de cores "ficou bagunçada" — muitas cores concorrendo, hierarquia pouco clara.
Antes de qualquer mudança, releitura de `docs/design-system.md`/`docs/motion-principles.md` e
auditoria de todo o código por cor fora do sistema de tokens (`text-red-500`, `bg-blue-600` etc.
do Tailwind puro) — **zero ocorrências em todo o projeto**. A disciplina de tokens já era
seguida à risca; o problema real estava em dois pontos concretos, não nos tokens em si.

**Causa raiz real: `CartaoVisual`.** O gradiente de marca de cada instituição (cor real
pública do banco) era o fundo INTEIRO do cartão em saturação total — com 2-3 cartões de
instituições diferentes lado a lado (grid de `/cartoes`, Dashboard), várias cores fortes
competiam na mesma tela, o oposto da filosofia "confiança silenciosa" do Design System.
Corrigido sem alterar nenhuma cor de marca (`lib/cardThemes.ts` continua com os hex reais de
cada instituição): o cartão agora sempre tem uma base escura padrão por baixo, com o gradiente
de marca aplicado por cima como uma tinta translúcida (`opacity: 0.55`, mistura `soft-light`)
— a identidade ainda é reconhecível, só sem competir com badges/chips/barra de progresso.
Efeito colateral corrigido junto: a cor de texto calibrada por instituição (pensada para o
fundo antigo, saturado) parou de ser usada — 2 variantes (Banco do Brasil, Neon) ficariam
ilegíveis sobre a nova base escura; agora todo cartão usa a mesma cor de texto clara e
consistente.

**Segundo achado: badge "Sistema" com cor de interação.** Na tabela de Categorias, o badge que
marca uma categoria de sistema usava a cor de acento (reservada para ações/navegação) — ficou
ainda mais evidente depois do seed de categorias padrão desta mesma etapa (13+ categorias novas
mostrando esse badge repetidamente). Corrigido para o tone neutro (cinza), consistente com o
badge de "ativo/inativo" já usado no resto do projeto.

**Decisão: os valores dos tokens de cor não foram alterados.** A auditoria não encontrou
evidência de que a paleta central (acento, positivo/negativo/pendente/informativo, superfícies)
precisasse de re-tonalização — já passa nos testes de contraste (WCAG AA) documentados desde a
Etapa F2. O problema era pontual (dois componentes), não estrutural.

Validado com `tsc -b` e `vite build` limpos.

## 💱 CRUD de Transferências (Frontend) + Calendário Financeiro

Duas etapas implementadas juntas por pedido do usuário. Análise prévia em
`docs/analise-arquitetural-transferencias-frontend.md`.

**CRUD de Transferências (frontend).** Backend já existia por completo (criar/listar/
obter/cancelar, sem `PATCH`/`DELETE` — campos estruturais são imutáveis, cancelamento é soft
delete). Camada de dados nova (`types/schemas/services/hooks/transferencia*`) segue 1:1 o
molde de Transação. A experiência foi desenhada para comunicar "mover dinheiro entre contas",
não um formulário genérico: dois `AccountSelect` lado a lado com uma seta entre eles (animação
só na entrada, hover, durante o salvamento e na confirmação — **nunca em loop infinito**, pedido
explícito), botão de trocar origem/destino, e um preview textual da movimentação (Origem −Valor
→ +Valor Destino) antes de confirmar. Tabela em `/transferencias` mostra origem→destino com a
mesma seta (estática) como indicador de direção. Cancelamento usa a linguagem "Cancelar
transferência" (nunca "Excluir" — o backend não tem exclusão física), com a confirmação
explicando que a movimentação será revertida nos saldos das duas contas preservando o histórico,
e um toggle "Mostrar transferências canceladas" desabilitado por padrão.

**Gap real encontrado e resolvido: Agenda Financeira nunca incluía Transferência.** O enum
`TipoEntidadeReferenciavel` não tinha esse valor (adicionado — mudança aditiva em enum Python,
sem migration, já que só vira coluna real de banco em `Alerta`, feature ainda não implementada).
Mas o problema ia além do enum: `/central-financeira/agenda` só olha "Transação PENDENTE nos
próximos N dias" + "Fatura com vencimento futuro" — nunca incluiu Transferência, Meta
(`data_alvo`) nem o fechamento de fatura (só o vencimento), e não distinguia receita/despesa por
cor. Resolvido com um endpoint **novo e irmão** (não uma substituição):
`GET /central-financeira/calendario?ano=&mes=` +
`CentralFinanceiraService.calendario_financeiro`, que reaproveita os Services já existentes
(Transação, Fatura, Transferência, Meta) e devolve todo evento do mês — qualquer status, os dois
eventos de Fatura (fechamento e vencimento, cores diferentes), Transferência ativa e Meta com
prazo no mês. Um novo discriminador `CategoriaEventoCalendario` (schema-only, sem coluna de
banco) decide a cor do indicador, separado de `TipoEntidadeReferenciavel` (que decide a rota de
navegação) — um mesmo evento de Transação pode ser RECEITA ou DESPESA, coisa que
`TipoEntidadeReferenciavel` sozinho não capturava. `/central-financeira/agenda` (widget do
Dashboard) permanece intacto, sem nenhuma mudança de contrato.

**Calendário Financeiro (`/calendario`).** Substituiu a ideia original de "lista de eventos" por
um calendário mensal navegável de verdade — grade de semanas (domingo a sábado, dias fora do mês
esmaecidos), indicadores em formato de **pontos pequenos** por dia (nunca o dia inteiro pintado,
pedido explícito), até 4 categorias distintas visíveis por dia com "+N" para o excesso. Clicar num
dia abre um Drawer lateral com todos os eventos daquele dia (tipo, descrição, valor, status) e
link direto para a tela correspondente quando existe rota conhecida (Fatura/Transação →
Cartões/Transações; Transferência → Transferências) — mapa `origemNavegacao.ts` extraído para ser
compartilhado com o widget de Agenda do Dashboard (nenhuma lógica duplicada). Painel de resumo do
mês (derivado 100% client-side dos mesmos eventos já carregados, sem chamada nova): receitas/
despesas previstas, "Fluxo do mês" (rotulado com precisão — não é o saldo bancário projetado das
contas, só receitas menos despesas dos eventos do mês), dia mais movimentado, próximo vencimento,
próxima entrada. Navegação entre meses com transição horizontal (Motion), atalho "Hoje".

**Simplificação deliberada de cor:** o pedido original imaginava 8 cores (incluindo
Financiamento/Empréstimo com cor própria), mas esses dois já são `Transacao` (RECEITA ou
DESPESA) no modelo real — dar cor própria a eles exigiria 2 tokens novos só para esta tela,
contrariando o princípio "cor é sempre significado fixo, reaproveitado em todo o sistema" do
Design System. Ficaram agrupados em RECEITA/DESPESA (mesma cor de qualquer transação); o ícone
de origem dentro do Drawer já distingue a origem exata.

Validado com `tsc -b`, `vite build` e suíte de testes de backend completa (unit + todos os
arquivos de integração) — nenhuma regressão.

**Pedidos adicionais registrados durante esta etapa** (fila priorizada pelo usuário do mais
demorado ao mais rápido): compra parcelada no cartão, exclusão de Fatura fechada, import de
Fatura histórica, onboarding de Financiamento/Empréstimo (CRUD completo + parcelas já pagas) e
edição livre de categorias do sistema — todos implementados, ver seções abaixo, cada um com sua
própria investigação de backend antes de qualquer código.

## 🛒 Compra parcelada no cartão (dentro do formulário de Transação)

Primeiro item da fila registrada na etapa anterior. Backend de `Parcelamento` já existia por
completo e sem limitação real (`criar`/`obter`/`listar`/`cancelar`, gera as N `Transacao` reais
de forma eager na criação, `DESPESA` sempre, sem `tag_ids`/`status` no schema — decisão do
backend) — nenhuma mudança de backend foi necessária, só camada de dados nova no frontend
(`types/services/hooks/parcelamento*`, seguindo o mesmo molde de `transferencia*`) e integração
no formulário existente.

Pedido explícito era "de forma intuitiva, sem atrapalhar a experiência padrão já existente":
o toggle "À vista / Parcelado" só aparece quando a origem é Cartão de crédito **e** em modo
criação (uma parcela já gerada nunca "vira" um parcelamento novo — editar continua 100% como
antes). Escolher "Parcelado" revela um campo "Em quantas vezes" e um preview client-side
("Nx de R$ Y", cálculo simples de exibição — o backend arredonda de verdade ao dividir
`valor_total`, absorvendo o resto na última parcela); some o seletor de Tags nesse modo, porque
`ParcelamentoCreate` não aceita tags — omitir é mais honesto que mostrar um campo que seria
silenciosamente ignorado. Trocar a origem de volta para Conta reseta o toggle para "À vista"
automaticamente. Ao submeter parcelado, a chamada desvia inteira para `POST /parcelamentos` em
vez de `POST /transacoes`; a invalidação de queries reaproveita `invalidarTransacoes` (mesmo
efeito sobre saldo/limite/Dashboard de uma transação normal, já que Parcelamento gera
Transação de verdade).

Validado com `tsc -b` e `vite build` (sem alteração de backend, suíte de testes de backend não
precisou ser re-executada).

## 🗑️ Excluir Fatura mesmo já fechada (regra relaxada)

Segundo item da fila. Pedido: "o usuário pode ter fechado uma fatura de forma enganada" e
ficava sem jeito de desfazer, já que `Fatura` não tem "reabrir" nem soft delete. Investigação
confirmou que a regra antiga (`FaturaService.excluir`) exigia DUAS condições ao mesmo tempo:
status `ABERTA` **e** nenhuma transação vinculada (nem compra, nem pagamento). A segunda
condição é a que realmente protege histórico financeiro real; a primeira (status) bloqueava
até um ciclo vazio fechado sem querer.

Mudança aplicada (backend, leve — não exigiu perguntar antes, como o usuário havia pedido só
para o caso de mudança pesada): `excluir()` agora permite excluir uma fatura em **qualquer
status**, desde que continue sem nenhuma transação vinculada. Uma fatura com compras ou
pagamentos reais continua permanentemente protegida contra hard delete, fechada ou não — essa
parte da regra não mudou, porque cascatear/desvincular transações reais seria a mudança
"mais pesada" que o usuário pediu para eu confirmar antes de implementar (não foi necessária
aqui, já que o caso coberto é sempre um ciclo vazio). Texto de confirmação do frontend
(`FaturaDrawer.tsx`) atualizado para refletir a nova regra. Testes unitários e de integração
atualizados (fechada+vazia → permitido; fechada+com transação → continua bloqueado) e suíte
completa validada sem regressão.

## 📥 Importar Fatura histórica (onboarding)

Terceiro item da fila, direto do exemplo do usuário: "só o valor da fatura que ele já
realizou o pagamento anteriormente". Investigação confirmou uma restrição estrutural real —
`FaturaCreate` sempre nasce `ABERTA` e `valor_total` é sempre derivado de `Transacao` reais
(nunca aceito do cliente); não havia como registrar "esta fatura já aconteceu e já foi paga"
sem recriar cada compra individualmente.

Resolvido com um novo modo de criação, sibling de `POST /faturas`: `POST /faturas/importar`
(`FaturaImportarCreate` → `cartao_id`, `mes_referencia`, `valor_total`). A fatura nasce já
`FECHADA`, com `valor_total` informado diretamente — única exceção deliberada e documentada ao
invariante "valor_total nunca vem do cliente" (`POST /faturas` continua 100% inalterado). Nova
coluna `Fatura.importada` (migration `b3a7f0c1d9e2`) marca esse registro como histórico, só
para o frontend exibir o selo "Importada" (`FaturaDrawer`, lista de faturas do Cartão) —
nenhum cálculo de `FaturaService._com_valores_calculados` muda por causa dela. Depois de
importada, o usuário usa o fluxo normal de "Registrar pagamento" (já aceita `data` no passado)
para lançar o quanto já pagou, se for o caso — sem duplicar essa lógica.

Frontend: toggle "Este ciclo já aconteceu (e já foi pago) antes de eu usar o app" dentro do
mesmo formulário inline de "Nova fatura" em `/cartoes/:id` — ligar o toggle revela o campo de
valor total e troca a chamada para `POST /faturas/importar`, sem criar uma tela separada.

Validado com testes unitários e de integração (nasce fechada, valor informado, duplicidade,
posse entre usuários, pagamento normal depois, exclusão de uma importada vazia) e suíte
completa sem regressão, `tsc -b`/`vite build` limpos.

## 🏗️ Onboarding de Financiamento/Empréstimo (parcelas já pagas + CRUD completo)

Quarto item da fila. Pedido original era só "adicionar o campo parcelas já pagas" — mas a
investigação revelou uma limitação real bem maior: Financiamento e Empréstimo nunca tiveram
NENHUMA tela de criação no frontend (só o card de resumo, somente leitura, do Dashboard). Não
havia onde colocar o campo sem construir o CRUD inteiro primeiro. Perguntado ao usuário, que
escolheu construir o CRUD completo agora.

**Backend (leve, sem migration):** novo campo opcional `parcelas_ja_pagas` em
`FinanciamentoCreate`/`EmprestimoCreate` (default 0 = comportamento de sempre). Em vez de
duplicar a lógica de decremento de `saldo_devedor`/transição para `QUITADO`,
`FinanciamentoService.criar`/`EmprestimoService.criar` simplesmente chamam `pagar_parcela` em
loop (parcela 1, 2, ..., N) logo após gerar o cronograma — reaproveitando 100% da mesma ação já
testada que o usuário aciona manualmente depois. Validado que `parcelas_ja_pagas` não pode
exceder `num_parcelas` (422).

**Frontend (novo, comparável em tamanho à etapa de Transferências):** páginas `/financiamentos`
e `/emprestimos`, cada uma com grid de cards clicáveis (saldo devedor, status, instituição —
mesmo espírito de `/cartoes`) + toggle "Mostrar quitados" desabilitado por padrão + botão "Novo
financiamento/empréstimo" abrindo um `FormDialog` de criação completo (conta, valor, taxa de
juros/CET como percentual com conversão automática para a fração de 4 casas que o backend
espera, sistema de amortização, número de parcelas, categoria opcional, e a seção "Parcelas já
pagas antes de usar o app" no rodapé). Clicar num card abre um Drawer com o contrato (saldo
devedor, taxa, sistema, início) e o cronograma completo de parcelas (reaproveita
`GET /transacoes?financiamento_id=`/`?emprestimo_id=`, sem endpoint novo), cada parcela pendente
com um botão "Pagar" — parcelas podem ser pagas fora de ordem, o backend não exige sequência.

Decisão deliberada: a listagem usa o endpoint próprio (`GET /financiamentos`/`/emprestimos`,
`apenas_ativos` configurável), não o agregador `/central-financeira/financiamentos` que já
alimenta o card do Dashboard — esse agregador hardcoda `apenas_ativos=True` no backend e nunca
mostraria um contrato QUITADO, o que seria errado para uma tela cujo propósito é ser o lar de
TODOS os contratos.

Validado com testes unitários e de integração (decremento de saldo, transições PAGO/QUITADO,
limite de `parcelas_ja_pagas`) para as duas entidades, suíte completa sem regressão,
`tsc -b`/`vite build` limpos.

## ✏️ Edição livre de categorias do sistema

Quinto e último item da fila. Pedido: "seria interessante o usuário poder editar o que ele
quiser da categoria". Investigação encontrou a causa real do bloqueio:
`CategoriaService._buscar_editavel` recusava com 403 QUALQUER escrita (`atualizar`/`desativar`/
`excluir`) numa categoria de sistema, porque `usuario_id IS NULL` é **uma única linha
compartilhada por todos os usuários** (não uma cópia por usuário) — comentário explícito nesse
sentido já existia no model desde a criação da entidade.

Achado apresentado ao usuário antes de implementar: edição direta da linha compartilhada é
simples, mas se o banco tiver mais de um usuário cadastrado um dia, a edição de um usuário muda
a categoria pra todos; a alternativa (copiar a categoria de sistema para uma própria ao editar)
resolveria isso mas é bem mais pesada (o que fazer com transações já vinculadas à original?).
Usuário escolheu a edição direta.

Implementado: `CategoriaService.atualizar` agora usa `_buscar_visivel` (a mesma checagem de
leitura) em vez de `_buscar_editavel` — nome/tipo/cor/icone/categoria_pai_id de uma categoria de
sistema podem ser editados por qualquer usuário autenticado. Uma exceção citada permanece
dentro do próprio `atualizar()`: `PATCH {"ativo": false}` numa categoria de sistema continua
levantando 403, porque desativá-la tiraria a categoria de TODO MUNDO, não só de quem editou —
isso nunca foi pedido, e é o mesmo motivo pelo qual `desativar()`/`excluir()` (hard delete)
continuam bloqueadas por inteiro para categoria de sistema, sem alteração. Frontend: a ação
"Editar" na listagem de Categorias deixou de ficar escondida para `e_do_sistema`, e o
`CategoriaFormDialog` não força mais modo somente-leitura para elas — "Desativar"/"Excluir"
continuam escondidas, com um aviso no formulário deixando claro que a edição de uma categoria de
sistema vale para todos os usuários.

Validado com a suíte de testes de backend relevante (unit + integração de Categoria).

## 🗑️ Excluir Financiamento/Empréstimo + formulário simplificado + parcela com juros

Três pedidos rápidos feitos em sequência logo após a etapa de Onboarding acima.

**Excluir Financiamento/Empréstimo** ("está faltando a opção de apagar financiamento"):
nenhuma das duas entidades tinha `DELETE` no backend. Investigação encontrou uma diferença
real em relação à Fatura: Financiamento/Empréstimo geram TODAS as N parcelas de uma vez já na
criação, então a regra "só exclui sem nenhuma transação vinculada" nunca seria satisfeita — não
dava para reaproveitá-la. Perguntado ao usuário, que escolheu exclusão sempre permitida (mesmo
com parcelas já pagas): as parcelas nunca são apagadas, só perdem o vínculo com o contrato e
viram despesas/receita avulsas comuns na conta. Achado real ao implementar: o
`ondelete=SET NULL` do banco em `Transacao.financiamento_id`/`emprestimo_id` sozinho **não**
bastava — `ck_transacao_numero_parcela_condiz_com_contrato` exige que `numero_parcela` só exista
se algum id de contrato também existir, e o cascade do banco zerava só o id do contrato, deixando
`numero_parcela` órfão e violando a CHECK. Corrigido desvinculando os dois campos explicitamente
no Service antes de excluir o contrato. `DELETE /financiamentos/{id}` e `DELETE /emprestimos/{id}`
novos, com ação "Excluir" no `FinanciamentoDrawer`/`EmprestimoDrawer` (confirmação inline, mesmo
padrão de `FaturaDrawer` — nunca um `ConfirmAction` por cima de um Drawer já aberto).

**Formulário de Financiamento simplificado** ("não peça informações burocráticas, apenas o valor
da parcela, quantidade de parcelas totais e pagas, data, instituição financeira, bem financiado,
nome e se permite quitação antecipada"): removidos do formulário os campos valor financiado,
entrada, taxa de juros, CET, sistema de amortização, número de contrato e categoria — nenhum
usuário pensa em "financiamento" como uma fórmula de amortização, pensa em "pago R$X por mês".
No lugar, um único campo "Valor da parcela". `financiamentoFormValuesParaCriacao` reconstrói o
payload completo que o backend ainda espera: `valor_financiado = valor_parcela × num_parcelas`
(multiplicação em centavos, sem risco de ponto flutuante) e `taxa_juros = 0` — com taxa zero, o
cronograma PRICE degenera em parcelas fixas e idênticas ao valor digitado
(`test_cronograma_price_sem_juros_degenera_em_divisao_simples`, já validado no backend desde a
etapa de Financiamento). Nenhuma mudança de backend foi necessária. `conta_id` continua no
formulário mesmo não tendo sido citado no pedido — é a única informação estruturalmente
obrigatória (`FinanciamentoService._validar_conta_obrigatoria`) que não é burocracia.

**Valor de parcela customizado em compra parcelada no cartão** ("permita que o usuário escolha
também o valor da parcela, caso ele não escolha, seja o valor calculado pelo sistema... ajuda
caso a compra tenha sido parcelada com juros ou sem juros"): achado real ao investigar —
`Parcelamento` já tinha um campo `taxa_juros`, mas ele é puramente informativo, nunca usado para
calcular o valor de cada parcela (`_dividir_valor` sempre divide `valor_total` igualmente, com o
resto absorvido pela última). Adicionado `valor_parcela` opcional em `ParcelamentoCreate`
(Pydantic-only, sem coluna nova/sem migration): quando informado, TODAS as N parcelas nascem com
exatamente esse valor (sem a última virar um "plug" de arredondamento — faz sentido só quando o
sistema está calculando a divisão, não quando o valor já é um dado conhecido e fixo cobrado pela
loja/operadora). `valor_total` continua sendo gravado como o usuário digitou, mesmo quando a soma
das parcelas não fecha exatamente nele (esperado: é o preço do juro embutido). Frontend: novo
`CurrencyField` opcional "Valor da parcela" no toggle Parcelado do `TransacaoFormDialog`, preview
"Nx de R$ Y" reflete o valor customizado quando presente.

Validado com testes unitários e de integração das três entidades e suíte completa de backend
sem regressão, `tsc -b`/`vite build` limpos.

## 🔎 Varredura de bugs críticos: "Falha de conexão com o servidor" + Dashboard fora do ar

Pedido do usuário: Calendário mostrando "Falha de conexão com o servidor" e Dashboard fora do
ar, com uma varredura completa do projeto atrás de bugs de desempenho/compatibilidade.

**Causa raiz nº 1 (a que derrubou o site): banco real desatualizado.** A migration que criou
`Fatura.importada` (etapa de importação histórica, feita mais cedo nesta mesma sessão) só tinha
sido testada contra bancos SQLite descartáveis — nunca foi de fato aplicada no
`backend/financas.db` real, o arquivo que o backend em produção usa. Esse projeto não tem
auto-migração no startup (nenhum `alembic upgrade head` automático quando o processo sobe), então
`alembic upgrade head` precisa ser rodado manualmente contra o banco real depois de qualquer
migration nova — passo que ficou faltando. Resultado: toda consulta que tocava `Fatura`
(exatamente o que o Dashboard e o Calendário fazem) levantava
`OperationalError: no such column: faturas.importada`, uma exceção não tratada. Corrigido:
backup do banco real (`financas.db.backup-pre-b3a7f0c1d9e2`) e `alembic upgrade head` aplicado
diretamente nele. Verificado com `alembic check` (zero divergência entre models e banco) e
consultas diretas em todas as tabelas principais — todas as 12 faturas existentes já tinham
`importada` preenchido corretamente pelo `server_default` da migration, nenhum dado órfão.

**Causa raiz nº 2 (por que virou "falha de conexão" em vez de um erro normal): CORS +
exceção não mapeada.** Esse projeto não tinha nenhum handler para exceção genérica — só as 5
exceções de domínio (`NotFoundError`, `BusinessRuleError`, etc.) tinham tradução para HTTP.
Qualquer outra exceção (como a `OperationalError` acima, mas isso vale para qualquer bug futuro
não previsto) sobe crua até o `ServerErrorMiddleware` do Starlette, que fica POR FORA do
`CORSMiddleware` registrado em `main.py` — a resposta 500 sai sem os headers de CORS, o
navegador bloqueia a resposta como violação de CORS, e `fetch()` (`httpClient.ts`) cai no
`catch` genérico que mostra literalmente "Falha de conexão com o servidor.", mesmo com o
backend rodando perfeitamente. Corrigido com uma rede de segurança definitiva: um
`@app.exception_handler(Exception)` em `main.py` que loga a exceção real (com stack trace) e
devolve um 500 comum, o que garante que o `CORSMiddleware` sempre vê uma resposta normal e
aplica os headers certos. Isso não muda nenhuma regra de negócio (as exceções de domínio
continuam com prioridade nos handlers específicos) — é só a garantia de que um bug futuro
qualquer nunca mais vai se disfarçar de "problema de rede/conexão".

**Achado adicional durante a varredura: testes-bomba-relógio.** `test_status_fechada_sem_
pagamento`/`test_status_parcialmente_paga` (unit) e os equivalentes de integração em
`test_fatura_flow.py` usavam `mes_referencia="2026-07-01"` fixo — a data de vencimento
resultante (17/07/2026) virou passado assim que o relógio real passou dessa data, fazendo
`FaturaService._derivar_status` calcular `ATRASADA` em vez do esperado, quebrando os testes sem
nenhuma mudança de código (a lógica de produção estava e continua correta). Corrigido com um
helper que sempre usa o mês seguinte ao atual, eliminando esse tipo de teste frágil.

**Restante da varredura**: cadeia de migrations Alembic íntegra (`alembic heads` só mostra uma
head), rotas todas registradas sem conflito em `main.py`, CORS/`vite.config.ts`/build do
frontend sem problema de configuração, `dist` já atualizado em relação ao código-fonte,
`CentralFinanceiraService` (usado pelo Dashboard) já era estruturalmente cuidadoso com
performance (loops só sobre coleções pequenas por natureza — cartões/contratos de uma pessoa —
nunca uma agregação em Python sobre a tabela inteira). Nenhum outro problema estrutural
encontrado.

**Ação necessária do usuário**: reiniciar o backend (`parar.ps1` seguido de `iniciar.ps1`) para
o processo já rodando carregar o banco corrigido e o novo handler de exceção.

Validado com suíte completa de backend (510 unit + 357 integração, 867 testes, 100% passando
após as correções), `tsc -b` limpo. `vite build` completo não pôde ser executado neste ambiente
de sandbox (falta um binário nativo do Rollup específico de Linux que não está instalado neste
container) — `tsc -b` já cobre a validação de tipos, que é a fonte mais comum de erro de build;
o `dist` já publicado foi confirmado como mais novo que todo o código-fonte atual.

## 🔗 Excluir uma parcela cancela a compra parcelada inteira

Achado do usuário: "ao excluir uma transação parcelada no cartão, a fatura atual muda mas as
próximas e o saldo não resetam". Causa raiz: uma parcela de `Parcelamento` não é uma transação
isolada — é uma de N linhas geradas ATOMICAMENTE por `ParcelamentoService._gerar_parcelas` no
momento da compra, cada uma já com `fatura_id` resolvido (inclusive as futuras).
`TransacaoService.excluir()` apagava só a linha clicada (pelo único ponto de entrada que a UI
oferece hoje — não existe uma tela dedicada de "cancelar parcelamento"), deixando as outras N-1
completamente intocadas: faturas futuras continuavam cobrando o valor cheio de uma compra já
removida, e `Parcelamento.ativo` continuava `True`.

Corrigido criando `TransacaoService.cancelar_parcelas_do_parcelamento()` — ponto único que
cancela o parcelamento inteiro (remove as parcelas ainda destravadas, preserva as que já
viraram passado numa fatura fechada, marca `ativo=False`), chamado tanto por `excluir()` (quando
qualquer parcela isolada é apagada pelo endpoint genérico de Transação) quanto por
`ParcelamentoService.cancelar()` (ação dedicada), que agora delega para lá em vez de duplicar o
loop. A trava de "não mexe em fatura fechada" continua valendo para a transação clicada
diretamente (levanta o mesmo erro de sempre); só as parcelas irmãs destravadas são canceladas em
cascata quando a exclusão é de fato permitida. Frontend: diálogo de confirmação de exclusão em
`/transacoes` avisa explicitamente quando a transação faz parte de uma compra parcelada, deixando
claro que todas as parcelas restantes serão canceladas.

Validado com testes unitários (`TransacaoService`/`ParcelamentoService`) e de integração novos
cobrindo os três cenários (cascata completa, preservação de parcela em fatura fechada, trava na
parcela clicada), suíte completa de backend sem regressão.

## 🎨 Cartões: gradiente de marca em saturação total (reversão da harmonização)

Pedido do usuário: as cores dos cartões (base escura + tinta translúcida `soft-light`, decisão
da Auditoria de Identidade Visual) não estavam legais visualmente — projeto de uso pessoal, nunca
vai ao ar, sem preocupação de direito autoral sobre usar a cor de marca real de cada instituição
em saturação total. Revertido: `CartaoVisual` volta a usar `tema.gradiente` diretamente como
fundo (não mais uma base escura fixa) e `tema.corTexto` como cor do texto (calibrada por
instituição em `lib/cardThemes.ts`, não mais sempre `--color-text-primary`). `StatusChip`
(fundo sólido, não translúcido) continua garantindo contraste do texto de prazo independente da
cor de fundo do cartão. `tsc -b` limpo.

## 📊 Repaginação do painel de acompanhamento (dashboard/)

Pedido do usuário: "está muito ruim de visualizar as informações". Causa raiz real: o painel
(`dashboard/index.html`/`app.js`/`style.css`, HTML/CSS/JS estático que lê `project-status.json`)
cresceu para 39 entregas concluídas no Kanban e um histórico de dezenas de itens — cada entrega
com uma descrição de parágrafo inteiro (documentação verbosa é o padrão deste projeto). O
layout original renderizava tudo isso como cards de Kanban tradicionais, virando uma parede de
texto impossível de escanear, e o chip de "Testes backend" (uma string cada vez mais longa)
transbordava do card.

Corrigido sem tocar em nenhum dado do JSON, só em como é exibido: a coluna "Concluído" do
Kanban virou uma seção própria abaixo do quadro ativo (backlog/em desenvolvimento/revisão) —
uma lista searchável e colapsável por padrão, cada entrega mostrando só título + categoria +
data até ser clicada (parágrafo completo aparece então), com botões "Expandir tudo"/"Recolher
tudo". Mesmo tratamento no Changelog: títulos longos cortam em 3 linhas com "Ver mais", e um
campo de busca filtra por texto. Roadmap: fases já concluídas (`status: "done"`) nascem
recolhidas — só o badge e o título, sem competir por atenção com o que está em andamento.
Chips de qualidade truncam com reticências e mostram o texto completo no hover (`title`).
Nova barra de navegação por âncoras (Visão geral/Áreas/Roadmap/Funcionalidades/Tarefas/
Histórico/Arquitetura) com scroll suave, e uma faixa de estatísticas rápidas na Visão Geral
(entregas concluídas, itens no histórico, entidades prontas) para responder "quanto já foi
feito" sem precisar rolar a página inteira.

## ✏️ Financiamento/Empréstimo: corrigir parcela + total já pago

Pedido do usuário: depois de registrar um Financiamento/Empréstimo, não dava para corrigir
valor/data de uma parcela digitados errado, nem ver quanto já foi pago no total. Achado real ao
investigar antes de escrever qualquer código novo: o backend já permitia isso —
`TransacaoService.atualizar()` só bloqueia o campo `status` quando `financiamento_id`/
`emprestimo_id` está preenchido (protege `saldo_devedor` de desincronizar de uma parcela marcada
paga por fora do Service dono); `valor`/`data` nunca foram travados ali, e `saldo_devedor` é
derivado do cronograma determinístico (posição da parcela na amortização PRICE/SAC), nunca do
valor gravado na Transacao em si — corrigir um valor/data digitado errado é só correção de
registro histórico, não recálculo de amortização. Faltava só a UI.

Criado `ParcelaContratoEditForm` (compartilhado entre `FinanciamentoDrawer` e `EmprestimoDrawer`,
reaproveita 100% o `PATCH /transacoes/{id}` genérico via `useAtualizarTransacao`) — um ícone de
lápis por parcela (paga ou não) substitui o conteúdo do Drawer pelo formulário de correção, mesmo
padrão já usado pela confirmação de exclusão (nunca abre um `FormDialog` por cima de um Drawer já
aberto). "Total já pago" (soma de `valor` das parcelas com `status === "PAGO"`) passou a aparecer
ao lado do contador "X/Y parcelas pagas" em ambos os Drawers. `tsc -b` limpo.

## 💰 Saldo da conta não é mais afetado por parcelas de contrato anteriores ao uso do app

Bug relatado pelo usuário: o Dashboard mostrava saldo negativo numa conta vinculada a um
Financiamento que já existia antes dele começar a usar o app — dado "fake" na visão dele, porque
o parcelamento real já tinha sido descontado da vida financeira dele muito antes de qualquer
conta ser cadastrada aqui. Instrução explícita: "deixe por conta do usuário decidir se ele tá com
saldo negativo ou não, evite deduções com base em informações resgatadas do passado financeiro
antes do uso do app".

Causa raiz real: `ContaRepository.somar_transacoes_pagas` soma TODA transação `PAGO` da conta,
sem distinguir uma parcela paga organicamente pelo botão "Pagar" da UI de uma parcela importada
pelo campo "parcelas já pagas" no onboarding do Financiamento/Empréstimo (`FinanciamentoService.
criar()`/`EmprestimoService.criar()`) — essa segunda categoria representa dinheiro que já tinha
saído da vida financeira do usuário ANTES de qualquer conta existir no app, mas ainda assim
gerava uma `Transacao` `PAGO` real vinculada à conta, sendo contada duas vezes contra o saldo.

Corrigido com o mesmo padrão já usado em `Fatura.importada`: nova coluna `Transacao.importada`
(bool, `server_default=false`, migration `c4d8e1a2f6b7`) marcada `True` só pelo loop de onboarding
"parcelas_ja_pagas" de `FinanciamentoService.criar()`/`EmprestimoService.criar()` — nunca por um
pagamento real feito pela UI depois. `ContaRepository.somar_transacoes_pagas` passou a excluir
`importada=True` da soma. As métricas de progresso do contrato (parcelas pagas/total pago,
`CentralFinanceiraService`/Drawers) ficam intocadas — usam `TransacaoRepository.listar_do_usuario`
diretamente, nunca `somar_transacoes_pagas`, então continuam contando o histórico completo do
contrato normalmente; só o saldo da Conta deixa de sofrer a dedução retroativa.

Migração já aplicada na base real do usuário, incluindo o backfill único necessário: as 13
parcelas de Financiamento já pagas antes desta coluna existir foram marcadas `importada=True`
(essa é a única explicação possível para uma parcela de contrato de crédito já estar `PAGO`
nesta base — o botão "Pagar" da UI e o próprio campo "parcelas já pagas" acabaram de ser criados
nesta mesma sessão de trabalho). Saldo da conta afetada voltou de -R$ 11.937,38 para R$ 0,00.
Suíte completa de backend (513 unit + integração) sem regressão, `tsc -b` limpo.

## 🎨 Refinamento de UX/UI (sem funcionalidade nova, exceto onde indicado)

Pedido explícito do usuário: melhorar qualidade visual/experiência do Dashboard, Categorias,
Calendário e Pickers, mantendo toda a arquitetura atual, sem novos CRUDs. Separado abaixo em
**bugs corrigidos** (comportamento errado, não uma questão de gosto) e **melhorias de UX**
(o que já funcionava, mas podia ser melhor):

**Bugs corrigidos:**
- **Valores estourando os cards do Dashboard** (`ResumoFinanceiroSection`/`StatCard`): a causa
  raiz real era o limiar de `tamanhoValorHero` (`utils/format.ts`) manter `text-display` (44px)
  para qualquer valor de até 11 caracteres, sem considerar que os 3 cards do meio
  ("Entradas"/"Saídas"/"Fluxo de caixa") são bem mais estreitos (2/12 colunas) que os 2 das pontas
  (3/12). Um valor como "R$ 1.005,84" (11 caracteres) vazava por cima do card vizinho. Corrigido
  com dois mecanismos combinados, nenhum sendo "só diminuir a fonte uniformemente": (1) limiares de
  `tamanhoValorHero` recalibrados pelo pior caso real (card mais estreito) — praticamente todo
  valor de 3-4 dígitos com centavos agora cai em `text-h1`, não mais `text-display`; (2)
  `formatMoneyInteligente`/`formatMoneyCompacto` (novo, `Intl.NumberFormat` com `notation:
  "compact"`) compacta valores a partir de R$ 100 mil para "R$ 1,2 mi"/"R$ 123,5 mil" — o valor
  cheio continua disponível no atributo `title` (aparece no hover). As duas pontas (Saldo total/
  Patrimônio líquido) também ganharam `col-span-2` no mobile (linha inteira cada, em vez de
  dividir a grade 2 colunas com os outros três).
- **Bento grid do Dashboard "esticando" cards vazios**: o CSS Grid padrão estica cada célula para
  a altura da linha inteira — com densidade de conteúdo tão variável entre os 6 cards de entidade
  (Contas/Cartões/Faturas/Financiamentos/Empréstimos/Metas), um card com poucos itens ficava
  esticado com um vazio grande embaixo enquanto o vizinho mais denso "parecia apertado" na mesma
  altura. Corrigido com `items-start` nas duas grades do Dashboard (`ResumoFinanceiroSection` e
  a grade de 6 cards) — cada card agora só ocupa a própria altura de conteúdo.

**Melhorias de UX:**
- **Categorias como grupos recolhíveis**: cada categoria pai com subcategorias ganhou um chevron
  clicável (expandir/recolher) na coluna "Nome" da tabela — `filtrarCategoriasVisiveis`
  (`categoriaTableColumns.tsx`) esconde os filhos de um pai recolhido sem tocar em busca/filtro/
  ordenação já existentes do `DataTable` (só filtra o array `data` recebido). Estado de
  recolhimento persiste em `sessionStorage` ("lembrar durante a sessão", nunca `localStorage` —
  diferente da ordem da Sidebar, que é uma preferência permanente, recolher é uma escolha
  exploratória de agora). Botões "Expandir tudo"/"Recolher tudo" ao lado do filtro de inativas.
- **Calendário: navegação direta de mês/ano** (`MesAnoSeletor`, novo componente): o rótulo estático
  "Julho de 2026" virou um botão que abre um painel com stepper de ano + grid dos 12 meses —
  escolher um mês distante deixa de exigir dezenas de cliques nas setas. Mesma mecânica de
  posicionamento (`useFloatingPanel`, Tier 1) e mesmo padrão de fechar imediatamente ao selecionar
  (nunca um passo extra de confirmação) de todo o resto da família de pickers do projeto. Botão
  "Hoje" já existia, mantido como está.
- **Calendário: células mais quadradas** (`CalendarioMensal`): `aspect-square` no lugar de uma
  altura mínima fixa (`min-h`) — grade mais equilibrada, mais parecida com Google
  Calendar/Notion Calendar/Windows Calendar, como pedido.
- **Financiamento/Empréstimo, Categorias e outros Pickers (Data/Cor/Ícone/Instituição/Bandeira)**:
  auditados a pedido do usuário ("diversos componentes exigem dois cliques para concluir uma
  seleção") — `RichPicker`/`DateInput`/`Select`/`SearchSelect` (a base de todos esses pickers) já
  fecham e aplicam a seleção num único clique desde a etapa de Refinamento de Pickers/Performance;
  nenhum passo extra de confirmação foi encontrado em nenhum deles. Nenhuma mudança de código
  necessária aqui — só confirmação de que o comportamento pedido já existe.

`tsc -b` limpo. `vite build` não pôde ser executado neste ambiente de sandbox (falta o binário
nativo `@rollup/rollup-linux-x64-gnu`, mesma limitação de plataforma já documentada em etapas
anteriores) — rode `npm run build` dentro de `frontend/` na sua máquina Windows e reinicie
(`parar.ps1` + `iniciar.ps1`) para ver todas as mudanças desta etapa (incluindo a correção de saldo
e a edição de parcela das duas etapas anteriores, que também ainda não foram para o build).

**Ajustes feitos depois, no mesmo dia, a partir de feedback direto do usuário:**
- **"Patrimônio líquido" removido do Dashboard** — usuário achou "não útil no momento".
  `ResumoFinanceiroSection` caiu de 5 para 4 `StatCard`s, o que permitiu simplificar a grade de
  pesos 3-2-2-2-3 em 12 colunas para uma grade simples e igual (`grid-cols-2` no mobile,
  `grid-cols-4` a partir de `md`) — o dado continua disponível em
  `CentralFinanceiraService`/`data.patrimonio_liquido` se precisar voltar no futuro.
- **Categorias: recolher pelo NOME inteiro, não por um ícone à parte** — 1ª versão do item 4 só
  tornava um chevron pequeno clicável; ajustado a pedido do usuário para a linha inteira do nome
  (chevron + selo + texto) ser a superfície clicável — clicar em "Alimentação" já recolhe
  "Delivery"/"Mercado"/"Padaria"/"Restaurantes" para dentro dela.
- **Categorias: coluna "Categoria pai" removida** — usuário achou "inútil"; a indentação + conector
  visual (`CornerDownRight`) já comunicam a hierarquia sem precisar de uma coluna à parte.
  `buildCategoriaTableColumns` ficou só com Nome/Tipo/Status.
- **Fatura: bug de UX na exclusão (versão inicial, depois substituída pela regra abaixo)** — o
  Drawer deixava confirmar "Excluir fatura" mesmo quando a fatura já tinha compra/pagamento
  vinculado, só para falhar depois com um toast de erro. Corrigido na hora expondo
  `FaturaRead.pode_excluir`, escondendo o botão de antemão quando a exclusão sempre falharia -
  ver o item **"Excluir fatura mesmo com transação vinculada"** logo abaixo, que trocou a regra de
  base e tornou esse campo desnecessário (removido).

## 🗑️ Excluir fatura mesmo com transação vinculada (compra ou pagamento)

Pedido explícito do usuário: uma fatura já parcialmente/totalmente paga (ou com compra lançada)
não podia ser excluída de jeito nenhum - ruim quando o valor foi cadastrado errado e o usuário só
percebe depois de já ter uma transação ali, sem nenhuma forma de desfazer.

- **Nova regra**: `FaturaService.excluir()` não bloqueia mais por `existe_transacao_vinculada` -
  hard delete sempre permitido, independente de status ou histórico.
- **O que muda de verdade**: `FaturaRepository.desvincular_transacoes()` (novo) zera
  `fatura_id`/`fatura_paga_id` de toda transação vinculada ANTES de apagar a fatura - a transação
  em si nunca é apagada, só perde o vínculo com o ciclo excluído. É a versão em código do que a FK
  já declara (`ondelete="SET NULL"`) mas que o SQLite deste projeto não executa sozinho (a conexão
  nunca liga `PRAGMA foreign_keys=ON`), então sem esse método a transação ficaria com um
  `fatura_id` "pendurado", apontando para uma linha que deixou de existir.
- Campo `FaturaRead.pode_excluir` e o repositório `existe_transacao_vinculada` foram **removidos**
  (não fazem mais sentido - a exclusão agora é sempre permitida). O botão "Excluir fatura" no
  Drawer voltou a aparecer sempre, com o texto de confirmação atualizado explicando que transações
  vinculadas só são desvinculadas, nunca apagadas.
- Testes: 1 teste de integração antigo virou 3 novos (aberta/fechada com compra vinculada,
  e um cobrindo especificamente o caso relatado - fatura com pagamento registrado), todos
  verificando que a transação sobrevive com `fatura_id`/`fatura_paga_id` de volta a `null`.
  Suíte completa (backend) sem regressão.

## 🖼️ Logos reais de bandeira (Visa/Mastercard) e de instituição financeira (bancos)

Pedido explícito do usuário, com imagens de referência/repositórios fornecidos na conversa.

- **Bandeiras** (`BandeiraBadge`, `CardBrandPicker`): Visa e Mastercard ganharam recriações em SVG
  fiéis às cores oficiais (`components/ui/brandLogos.tsx`) - mark de duas bolas
  (vermelho/dourado) da Mastercard e wordmark itálico da Visa, sobre um selo branco (as demais 5
  bandeiras continuam com o monograma de sempre).
- **Instituições** (`InstitutionBadge`, `BankPicker`, `CartaoVisual`): 15 das 17 instituições do
  registry (`lib/institutions.ts`) ganharam `logoUrl` apontando para um SVG oficial real, copiado
  do repositório [`rzmt/logos-bancos-br`](https://github.com/rzmt/logos-bancos-br) (avaliado contra
  `Tgentil/Bancos-em-SVG` e escolhido por ter proveniência rastreável - cada logo vem do diretório
  público de participantes do Open Finance Brasil, com URI/SHA-256/data documentados, aviso de
  marca registrada e processo de takedown; o outro repositório não tinha nenhuma licença ou
  proveniência documentada). Arquivos e origem completa em
  `frontend/src/assets/institutions/NOTICE.md`. Wise/PayPal (internacionais, fora do escopo do
  dataset) continuam só com monograma.

## 📅 Calendário: revertido para o formato original

Depois de três iterações tentando "quadrado" (primeiro esticando a coluna inteira, depois um
tamanho fixo centralizado sem linhas de grade, depois um tamanho fixo com linhas de grade só
parcialmente satisfatório), o usuário decidiu que a primeira versão de todas - células
retangulares (`min-h-[4.5rem]`/`sm:min-h-[5.5rem]`), grade cheia largura com linhas finas entre
os dias (`gap-px` + `bg-border-subtle`) e o card com fundo (`bg-surface-2`) envolvendo legenda +
grade - já era a melhor solução. `CalendarioMensal.tsx` e `CalendarioPage.tsx` voltaram exatamente
a esse estado.

## 🎯 CRUD de Meta (Frontend, Etapa F12)

Décima primeira entidade com CRUD real no frontend. Backend já existia completo e fechado (ver
seção "CRUD de Meta" acima e `docs/analise-arquitetural-meta.md`/`docs/revisao-tecnica-meta.md`);
esta etapa só constrói a experiência sobre o que já estava pronto, sem tocar em nenhuma regra de
negócio. Análise completa em `docs/analise-arquitetural-metas-frontend.md`.

- **`MetaSelect` em `TransacaoFormDialog` — a peça obrigatória, não um extra.** Sem um jeito de
  marcar uma Transação com `meta_id`, nenhuma Meta jamais acumularia progresso de verdade (o
  backend já validava/filtrava por `meta_id` desde a etapa de Meta, mas o formulário nunca
  expunha o campo). Campo opcional "Meta", visível em qualquer combinação de
  tipo/origem (RECEITA soma como aporte, DESPESA subtrai como retirada), oculto no modo
  Parcelado (`ParcelamentoCreate` não aceita `meta_id`, mesmo tratamento de `tag_ids`).
- **`/metas` — grid de cards, nunca tabela** (pedido explícito: "cada Meta deve parecer um
  objetivo em andamento, não apenas um registro"). Cada `MetaResumoCard` mostra, sem precisar
  abrir nada: percentual, valor acumulado, valor restante, prazo e situação
  (Em andamento/Concluída/Atrasada/Desativada, derivada client-side de `percentual`/`data_alvo`
  já calculados pelo backend — nunca reproduzidos) + uma frase de "velocidade para atingir"
  (ritmo médio de aporte por mês, projeção 100% client-side sobre `valor_acumulado`/`criado_em`,
  nunca uma regra de negócio nova). Clicar no card **expande inline** o histórico recente de
  aportes (em vez de navegar para outra tela) — reusa a mesma `queryKey` de
  `GET /transacoes?meta_id=`, então já é invalidado de graça por qualquer mutation de Transação.
- **Filtros rápidos** (Todas/Em andamento/Concluídas/Atrasadas/Desativadas, com contagem) e
  **ordenação** (mais próxima da conclusão, mais distante, vencimento, maior/menor valor) — 100%
  client-side sobre uma única listagem (`useMetas(false)`, sempre todas), mesmo raciocínio de
  volume baixo já usado em Cartão/Financiamento/Empréstimo — nenhum parâmetro novo de API.
- **Exclusão definitiva (hard delete), pedido explícito do usuário** — `MetaActionBar` ganhou um
  botão "Excluir" além de "Desativar/Reativar" (soft delete, que continua existindo). Novo
  `MetaService.excluir()`/`DELETE /metas/{id}/permanente`: nunca bloqueado por aportes vinculados
  (mesma regra de `FaturaService.excluir`, 2026-07-24) — `MetaRepository.desvincular_transacoes`
  zera `Transacao.meta_id` das transações desta meta antes de apagar a linha, a transação em si
  nunca é removida (só perde o vínculo). 8 testes novos (unit + integration).
- **Backend, uma linha aditiva**: `MetaRead` ganhou `criado_em` (coluna que já existia via
  `TimestampMixin`, nunca antes exposta em nenhum Read) — só para o Frontend calcular a
  velocidade de aporte; nenhum Service/Router mudou, suíte de Meta (55 testes) sem regressão.
- **Dashboard**: `MetasCard` ganha navegação para `/metas` (fechando a lacuna que o próprio
  componente já documentava desde a etapa de Refinamento) e reordena metas "em destaque" (perto
  de concluir ≥80%, ou vencendo em ≤14 dias) para o topo, com um rótulo curto — integração
  discreta pedida pelo usuário, mesmo endpoint/componente, só reordenação + classificação sobre
  dado já calculado.

## 🗓️ Popup de mês/ano em toda navegação por período

Pedido do usuário: o seletor de mês/ano com popup (stepper de ano + grid de 12 meses) criado para
o Calendário Financeiro ficou bom o bastante para virar padrão em qualquer navegação por data do
app. `PeriodoSeletor` (compartilhado por `DashboardPage` e `TransacoesPage`) trocou o rótulo
estático "Julho de 2026" pelo mesmo `MesAnoSeletor` já usado em `CalendarioPage` — as duas telas
ganham o popup automaticamente, sem nenhum componente novo.

## 💳 Cartão: saldo já utilizado, independente de transações

Pedido do usuário (correção de uma tentativa anterior): poder informar quanto do limite de um
cartão já está comprometido **sem criar nenhuma Transacao** — a primeira tentativa (ver "descoberta
do ajuste", abaixo) só melhorou a visibilidade de um botão que criava um lançamento `DESPESA` real;
o usuário deixou explícito que queria um número declarado diretamente, do jeito que
`Conta.saldo_inicial` já funciona (um valor somado ao cálculo real, nunca uma linha na ledger).

- **Backend**: nova coluna `Fatura.ajuste_manual` (`Numeric(12,2)`, default `0`, migração
  `d2a4e6f8c1b3`). Novo `FaturaService.ajustar_saldo_inicial()` / `PATCH
  /faturas/{id}/ajuste-manual` — só permitido com a fatura **ABERTA** (uma fatura fechada já tem
  `valor_total` congelado; ajustar um ciclo histórico é o que `FaturaImportarCreate` resolve, de
  outro jeito). `_com_valores_calculados` soma `ajuste_manual` a `valor_total_calculado` enquanto
  ABERTA; `fechar()` o congela dentro de `valor_total` uma única vez, nunca mais somado depois.
  `CartaoRepository.somar_gastos_nao_pagos` (usada por `CartaoService._com_limite_disponivel`)
  ganhou um segundo termo somando `Fatura.ajuste_manual` de toda fatura não paga do cartão — sem
  isso, o ajuste apareceria em `FaturaRead.valor_total` mas nunca reduziria `limite_disponivel`
  (essa query soma `Transacao.valor` diretamente, nunca lê `valor_total`). 17 testes novos
  (unit + integration), incluindo verificação ponta a ponta do impacto em `limite_disponivel`.
- **Frontend**: `CartaoDetalhePage` — o botão (agora "Informar saldo já utilizado") abre
  `AjusteSaldoInicialDialog` em vez do antigo `TransacaoFormDialog` pré-preenchido. Um único
  `CurrencyField`; se o cartão ainda não tem nenhuma fatura ABERTA (ex.: cartão recém-criado), o
  próprio submit cria o ciclo do mês atual antes de aplicar o ajuste — o usuário nunca precisa
  passar por "Nova fatura" primeiro. `FaturaDrawer` mostra o valor declarado (quando > 0 e ainda
  ABERTA) para transparência.

### Tentativa anterior (insuficiente): descoberta do ajuste via Transação

Botão "Registrar saldo já gasto neste cartão" em `CartaoDetalhePage` (Etapa de Refinamento de
UX/Dashboard/Cartões) abria `TransacaoFormDialog` pré-preenchido — criava um lançamento `DESPESA`
real no ciclo aberto. `CartaoFormDialog` ganhou `onCriado` e `CartoesPage` passou a navegar direto
para `/cartoes/:id` do cartão recém-criado, só para tornar esse botão mais fácil de achar. Isso
resolvia a descoberta, mas não o pedido real: o usuário queria um número declarado, sem nenhuma
transação — daí o mecanismo acima (`ajuste_manual`), que substitui este botão por completo.

## 🎯 Refinamento de Metas (planejamento, planejado x realizado, previsão, celebração, histórico)

Pedido explícito do usuário: enriquecer a experiência de `/metas` usando os dados já existentes,
sem alterar nenhuma regra de negócio validada — ver `docs/analise-arquitetural-metas-refinamento.md`
para as fórmulas exatas e as decisões documentadas.

- **Backend, tudo transiente exceto dois campos.** `Meta` ganha duas colunas persistidas:
  `frequencia_contribuicao` (`FrequenciaContribuicao`: DIÁRIA/SEMANAL/QUINZENAL/MENSAL, escolha do
  usuário, opcional) e `concluida_em` (data, gravada **uma única vez** por `MetaService._com_progresso`
  na primeira vez que `percentual` cruza 100% — nunca desfeita depois, mesmo que caia de novo).
  Todo o resto é calculado a cada leitura, no mesmo padrão de `valor_acumulado`/`percentual`:
  `contribuicao_sugerida_por_periodo` (quanto guardar por período para chegar no prazo),
  `valor_planejado_ate_hoje`/`diferenca_planejado_realizado` (projeção linear `criado_em`→`data_alvo`
  comparada ao acumulado real), `situacao_planejamento` (ADIANTADO/DENTRO_DO_PLANEJADO/ATRASADO, banda
  de tolerância de 2%) e `data_prevista_conclusao` (extrapolação do ritmo médio desde `criado_em`,
  só exibida quando há dados suficientes para ser confiável).
- **`calcularVelocidadeMeta` (frontend) removida.** Era uma métrica de apresentação equivalente,
  mas mais limitada, que a nova matemática do backend supera — mantê-la ao lado dos novos campos
  seria a duplicação de lógica que o pedido pede para evitar.
- **`MetaFormDialog`** ganha o seletor opcional "Frequência de contribuição". **`MetaResumoCard`**
  ganha: badge de situação do planejamento + frase "você está R$X acima/abaixo do planejado",
  frase de contribuição sugerida, frase de previsão de conclusão, e o histórico expandido (criada
  em / concluída em / tempo até concluir, além dos aportes que já existiam).
- **Celebração, uma exceção documentada.** `docs/design-system.md` registrava deliberadamente que a
  conclusão de uma Meta não teria confete — o pedido desta etapa pede confete/badge/mensagem
  explicitamente, tratado como atualização consciente dessa decisão, só para este momento. Burst
  pequeno (~14 partículas, cores só dos tokens semânticos já existentes), badge e frase de
  parabéns, ~1.6s, sem som (nenhuma infra de áudio no projeto; adicionar uma só para isto
  contradiria "elegante, não exagerado"). Disparada uma única vez por Meta via
  `useCelebracaoMeta`/`localStorage` (`meta-celebrada-{id}`) — `concluida_em` é o fato de negócio,
  "já mostrei" é puro estado de UI, nunca persistido no backend.
- **Dashboard sem duplicar lógica.** `types/centralFinanceira.ts::MetaRead` era uma cópia manual
  desatualizada — o backend de `/central-financeira/metas` já reusa `app.schemas.meta.MetaRead`
  literalmente, então o tipo passou a ser reexportado de `types/meta.ts` (mesmo padrão de
  `ContaRead` desde a Etapa F6), sem nenhuma alteração de backend. `MetasCard` passou a usar
  `situacao_planejamento === "ATRASADO"` (vindo pronto do backend) como sinal primário de urgência,
  mantendo a heurística antiga de proximidade de prazo só como fallback para metas sem essa
  informação.
- **Validação**: 545 testes unit + 38 integration de Meta + 26 de Central Financeira (sem
  regressão), `tsc -b` e `vite build` limpos.

## 🔄 Metas: aportes/resgates viram Transferência (não mais Transação)

Pedido do usuário (verbatim): "refatore o módulo de Metas para que os aportes e resgates sejam
tratados como transferências internas, e não como despesas ou receitas. Isso deixa o patrimônio
consistente, evita distorções nos relatórios e aproxima o sistema do funcionamento de aplicativos
financeiros mais robustos." Análise completa em
`docs/analise-arquitetural-metas-transferencias.md`. Duas decisões confirmadas explicitamente com
o usuário antes da implementação: **cofrinho automático** (cada Meta ganha uma Conta dedicada e
oculta, criada pelo próprio sistema) e **congelar histórico** (aportes antigos via `Transacao`
continuam contando, mas não é mais possível criar um novo assim).

- **`Meta.conta_id` deixa de ser opcional/organizacional e vira obrigatório/automático.**
  `MetaService.criar()` provisiona um "cofrinho" — uma `Conta` nova com `oculta=True` (coluna
  nova) — em toda Meta criada; `conta_id` some de `MetaCreate`/`MetaUpdate` (não é mais escolha do
  usuário), mas continua em `MetaRead` (sempre preenchido) para o Frontend montar o payload de
  aporte/resgate. Migração de dados (`f2a5c8e1b3d7`) provisiona um cofrinho retroativo para toda
  Meta já existente, sem apagar nada.
- **`Conta.oculta` (nova coluna) esconde o cofrinho de toda listagem normal**, sem exigir nenhuma
  mudança no Frontend: `ContaRepository.listar_do_usuario` ganhou `apenas_visiveis: bool = True`
  (default oculta os cofrinhos), e `GET /contas` nunca precisou de um parâmetro novo — o cofrinho
  simplesmente não aparece em `AccountSelect`/`ContasPage`. Continua contando no patrimônio total:
  `CentralFinanceiraService` é o único chamador que passa `apenas_visiveis=False`.
  `valor_acumulado` de uma Meta passa a somar DUAS fontes, sem nenhuma fórmula nova: o histórico
  legado (`MetaRepository.somar_transacoes_pagas`, congelado) + o saldo do cofrinho
  (`ContaRepository.somar_transferencias`, a mesma query que já calcula saldo de qualquer Conta).
- **Aporte/resgate reaproveita 100% `POST /transferencias` — nenhum endpoint novo.** Um aporte é
  só uma `Transferencia` com `conta_destino_id = meta.conta_id`; um resgate, `conta_origem_id =
  meta.conta_id`. `GET /transferencias` ganhou um filtro genérico `conta_id` (não específico de
  Meta) para o Frontend montar o histórico do cofrinho.
- **`Transacao.meta_id`: escrita removida, leitura preservada.** `TransacaoCreate`/`TransacaoUpdate`
  perdem o campo `meta_id` — não é mais possível, pela API, marcar uma Transação nova com uma
  Meta. A coluna, `TransacaoRead.meta_id` e o filtro `GET /transacoes?meta_id=` continuam intactos,
  sustentando o histórico legado congelado.
- **Frontend**: `MetaFormDialog` perde o `AccountSelect` de conta dedicada; `TransacaoFormDialog`
  perde o `MetaSelect` (componente removido do projeto, sem mais nenhum consumidor). Novo
  `MetaAporteDialog` — versão enxuta de `TransferenciaFormDialog` com um único `AccountSelect` (a
  Meta em si nunca aparece como opção, é sempre o lado implícito da transferência); reaproveita
  `useCriarTransferencia` sem nenhuma mutação nova. `MetaActionBar` ganha "Aportar"/"Resgatar"
  (só em Meta ativa). `MetaResumoCard` mescla o histórico legado (`Transacao.meta_id`) com o novo
  (`Transferencia` do cofrinho) numa única lista ordenada por data.
- **Nada é reescrito.** Toda Transação/Transferência histórica permanece exatamente como está;
  nenhuma fórmula do Refinamento de Metas anterior (planejado x realizado, previsão, celebração)
  muda — só a fonte de `valor_acumulado` que elas consomem.
- **Validação**: 921 testes de backend (538 unit + 383 integration), 100% passando; `tsc -b` e
  `vite build` limpos.

## 🌟 Sprint de Refinamento Premium — Etapa 1: Cartão (Estado Inicial) + bug do limite pós-pagamento

Pedido do usuário: uma sprint de 18 frentes (bug fixes, UX/UI, consistência, preparação de
arquitetura), sem criar novas regras de negócio. Análise completa em
`docs/analise-arquitetural-sprint-refinamento-premium.md` — dado o tamanho, a sprint é executada em
etapas; esta primeira etapa cobre as duas frentes de maior impacto/risco (um bug real e um fluxo
confuso), com investigação e correção completas.

- **Bug corrigido: limite disponível não voltava depois de pagar uma fatura.** Causa raiz:
  `CartaoRepository.somar_gastos_nao_pagos` comparava com a coluna `Fatura.status`, que por design
  nunca grava `PAGA` de verdade (só `ABERTA`/`FECHADA` são persistidas — `PAGA` é sempre derivado
  em runtime por `FaturaService`). `FaturaService.ids_faturas_pagas()` agora é a única fonte de
  verdade sobre "o que está pago" (reusa o mesmo cálculo já existente, não duplica a regra);
  `CartaoService` passou a depender de `FaturaService` para repassar esse conjunto à Repository.
  Um teste de integração existente mascarava o bug (forçava `status=PAGA` direto no banco, um
  estado que o fluxo real nunca produz) — reescrito para passar pelo fluxo real (fechar fatura +
  `POST /pagamentos`). 5 testes unitários novos cobrindo `ids_faturas_pagas`.
- **"Estado Inicial do Cartão" — redesenho do fluxo de "saldo já utilizado".** Antes, declarar o
  saldo já usado ao cadastrar um cartão (quando ainda não havia fatura aberta) criava, nos
  bastidores, uma `Fatura` do mês corrente só para guardar `Fatura.ajuste_manual` — confuso
  ("o sistema criou uma fatura sozinho"). Novo campo `Cartao.saldo_inicial_utilizado` (migração
  `a1b2c3d4e5f6`) declara esse valor direto no Cartão, sem nenhuma Fatura/Transacao por trás,
  consumindo `limite_disponivel` permanentemente até o usuário editar/zerar. `CartaoFormDialog`
  ganha o campo só no modo de criação; `AjusteSaldoInicialDialog` agora tem dois modos: sem fatura
  aberta, edita `Cartao.saldo_inicial_utilizado` (`PATCH /cartoes/{id}`); com fatura aberta,
  continua editando `Fatura.ajuste_manual` do ciclo (uso legítimo e diferente, não mais usado como
  mecanismo de onboarding).
- **Validação**: 543 testes unitários (5 novos) + suíte de integração completa, 100% passando;
  `tsc -b` e `vite build` limpos; migração testada em banco SQLite limpo.
- **Restante da sprint** (Dashboard de Cartões, revisão completa do Dashboard, Calendário,
  Categorias por usuário, Dashboard personalizável, Command Palette, Central de Atividades,
  auditoria final de experiência) segue em etapas subsequentes desta mesma sprint — decisões
  preliminares e sequenciamento documentados na seção final de
  `docs/analise-arquitetural-sprint-refinamento-premium.md`.

## 🌟 Sprint de Refinamento Premium — Etapa 2: Dashboard de Cartões agregado + Dashboard executivo + Card "Hoje"

Continuação da sprint (itens 3, 6-14 do escopo original). Investigação e decisão completas em
`docs/analise-arquitetural-sprint-refinamento-premium.md`, seção "3/6-14".

- **Problema identificado**: 6 dos cards do Dashboard (`ContasCard`, `CartoesCard`, `FaturasCard`,
  `FinanciamentosCard`, `EmprestimosCard`, `MetasCard`) renderizavam listas item-a-item — "coleção
  de mini-CRUDs" em vez de um resumo executivo.
- **Dashboard de Cartões agregado (backend)**: novo método
  `CentralFinanceiraService.resumo_cartoes_agregado` (limite total/disponível/usado, % geral,
  contagem de cartões, faturas em aberto, próximos 3 vencimentos) e rota
  `GET /central-financeira/cartoes/agregado`. Só soma/conta/ordena sobre o que `CartaoService` já
  calcula — nenhuma fórmula nova, mesmas 3 regras estruturais de sempre do
  `CentralFinanceiraService`. 2 testes de integração novos.
- **Cards do Dashboard viraram resumos**: `ContasCard` (saldo total + contagem + top 3 contas,
  fundido com `SaldoPorContaCard`, removido); `CartoesCard` (consome o agregado novo); `MetasCard`
  (contagem, progresso médio, meta mais perto de concluir, contagem de atrasadas); `FaturasCard`
  (só mostra atrasadas ou vencendo nos próximos 10 dias — o resto continua em `/cartoes/:id`).
  `FinanciamentosCard`/`EmprestimosCard` ganharam navegação para `/financiamentos`/`/emprestimos`
  (antes eram os únicos cards sem destino).
- **Card "Hoje"** (novo, `HojeCard.tsx`): reaproveita `calendario_financeiro` — mesmo endpoint já
  usado pelo Calendário Financeiro, zero lógica nova — filtrando client-side só os eventos de hoje.
  Usa o mesmo mapa de ícones/rotas de `AgendaFinanceiraCard`, para as duas seções nunca divergirem
  sobre o que é clicável. Fica logo após os indicadores gerais e some sozinho quando não há eventos
  no dia.
- **Validação**: 543 testes unitários passando, `tsc -b` e `vite build` limpos.
- **Restante da sprint** (Calendário, Categorias por usuário, Dashboard personalizável, Command
  Palette, Central de Atividades, auditoria final) segue em etapas subsequentes.

## 🌟 Sprint de Refinamento Premium — Etapa 3: Categorias padrão ocultáveis por usuário

Continuação da sprint (item 4 do escopo original). Decisão completa em
`docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 4.

- **Problema**: categoria de sistema é uma única linha global, compartilhada por todos os
  usuários - `desativar()`/`excluir()` sempre bloquearam 100% para ela (tudo ou nada), sem forma de
  um usuário parar de ver uma categoria de sistema que não usa, sem afetar os demais.
- **Nova tabela `CategoriaOcultaUsuario`** (`categorias_ocultas_usuario`, migração `b2c3d4e5f6a7`):
  registra, por usuário, quais categorias de sistema ele pediu para não ver mais. Não é uma
  exclusão de verdade - a linha de `Categoria` nunca é tocada, permanece intocada para todos os
  outros usuários. `desativar()`/`excluir()` continuam bloqueando 100% para sistema (nenhuma
  mudança ali); esta é uma quarta operação nova e distinta.
- **Backend**: `CategoriaRepository.ocultar_para_usuario`/`reexibir_para_usuario` (idempotentes) +
  `existe_transacao_vinculada_do_usuario` (bloqueia ocultar se o próprio usuário já usa a categoria
  em transações); `listar_visiveis_do_usuario` ganha `incluir_ocultas` (exclui por padrão via NOT
  EXISTS). Rotas novas: `DELETE /categorias/{id}/ocultar`, `POST /categorias/{id}/reexibir`.
- **Frontend**: `CategoriasPage` ganha as ações "Ocultar para mim" (só em categoria de sistema) e
  "Reexibir", mais o toggle "Mostrar categorias ocultas por você" para encontrar e reverter.
- **Validação**: 9 testes unitários + 9 de integração novos, 552 testes unitários e a suíte de
  integração completa (392 testes) passando; `tsc -b` e `vite build` limpos.
- **Restante da sprint** (Calendário, Dashboard personalizável, Command Palette, Central de
  Atividades, auditoria final) segue em etapas subsequentes.

## 🌟 Sprint de Refinamento Premium — Etapa 4: Calendário sem poluição de parcelas

Continuação da sprint (item 5 do escopo original). Puramente de apresentação, sem mudança de
backend — decisão em `docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 5.

- **Problema**: quando 2+ Parcelamentos diferentes têm parcela vencendo no mesmo dia, cada um
  aparecia como uma linha isolada no Drawer do dia, indistinguível de uma despesa avulsa.
- **Solução**: `EventoDiaDrawer` agora consolida 2+ eventos de Parcelamento do mesmo dia num único
  cartão recolhido ("N parcelas de compras parceladas — total"), com um clique para expandir e ver
  cada parcela individualmente. Um único evento de parcelamento no dia continua aparecendo normal.
  `origem_id` (já = `parcelamento_id`) foi suficiente para agrupar — nenhum campo novo no schema.
- **Validação**: `tsc -b` e `vite build` limpos.
- **Restante da sprint** (Dashboard personalizável, Command Palette, Central de Atividades,
  auditoria final) segue em etapas subsequentes.

## 🌟 Sprint de Refinamento Premium — Etapa 5: Dashboard personalizável

Continuação da sprint (item 15 do escopo original). Decisão em
`docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 15.

- **O quê**: os 6 cards do Bento Grid (Contas/Cartões/Faturas/Financiamentos/Empréstimos/Metas)
  agora podem ser reordenados (arrastar) e mostrados/ocultados via o botão "Personalizar" no
  cabeçalho do Dashboard, que abre um Drawer com a lista de cards.
- **Sem backend novo, sem biblioteca nova**: a preferência é puramente client-side, persistida em
  `localStorage` (`lib/dashboardLayout.ts`, mesmo padrão de `lib/cardThemes.ts`), tolerante a dado
  corrompido/desatualizado (sempre cai de volta ao padrão). Drag-and-drop implementado com a API
  nativa do HTML5 (`draggable`), sem adicionar peso de bundle por uma preferência cosmética. Botão
  "Restaurar padrão" sempre disponível.
- **Validação**: `tsc -b` e `vite build` limpos.
- **Restante da sprint** (Command Palette, Central de Atividades, auditoria final) segue em etapas
  subsequentes.

## 🌟 Sprint de Refinamento Premium — Etapa 6: Command Palette (Ctrl/Cmd+K)

Continuação da sprint (item 16 do escopo original). Decisão em
`docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 16.

- **`Ctrl+K`/`Cmd+K`** abre um modal de busca+navegação disponível em qualquer rota autenticada
  (montado uma vez em `AppLayout`). Reaproveita `NAV_ITEMS` (já usado por Sidebar/MobileNav) como
  índice de resultados — nenhuma lista de rotas duplicada — e `destacarTrecho`/`modalBackdrop`/
  `modalPanel` já existentes, nenhum padrão visual novo.
- **Navegação por teclado**: `↑`/`↓` move a seleção, `Enter` navega, `Esc` fecha.
- **Arquitetura extensível**: resultado tem um discriminador `tipo` (hoje só `"navegacao"`) desenhado
  para aceitar tipos novos no futuro (ações rápidas, pular direto para uma entidade específica) sem
  refatoração — só a navegação pedida foi implementada agora.
- **Validação**: `tsc -b` e `vite build` limpos.
- **Restante da sprint** (Central de Atividades, auditoria final) segue em etapas subsequentes.

## 🌟 Sprint de Refinamento Premium — Etapa 7: Central de Atividades

Continuação da sprint (item 17 do escopo original). Decisão em
`docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 17.

- **Feed cronológico** combinando Transação, Transferência e Meta concluída — sem nenhuma tabela
  de auditoria nova: cada fonte já expõe seu próprio timestamp (`criado_em`/`concluida_em`), lidos
  via os Services de domínio já existentes (`TransacaoService.listar`,
  `TransferenciaService.listar`, `MetaService.listar`) e combinados/ordenados em Python por
  `CentralFinanceiraService.atividades_recentes` (regras 1 e 3 do Service, nunca uma query nova).
- **Nova rota `GET /central-financeira/atividades`** (`limit` opcional, padrão 30), schema
  `AtividadeRecente`/`CentralAtividadesRead` reaproveitando `TipoEntidadeReferenciavel` (mesmo
  discriminador de `EventoCalendario`/`EventoAgenda`) — zero enum novo.
- **`AtividadesRecentesDrawer`**, aberto por um novo botão no `Header` (ícone, disponível em
  qualquer rota), reaproveita `ICONE_POR_ORIGEM`/`ROTA_POR_ORIGEM` de `origemNavegacao.ts` para
  ícone e link "Ver detalhes" de cada item — mesmo padrão visual do `EventoDiaDrawer`.
- **Testes de integração**: ordenação cronológica combinada, isolamento entre usuários, exclusão
  de transferência cancelada, parâmetro `limit`, meta concluída via aporte (cofrinho) — 8 testes
  novos, todos passando.
- **Validação**: testes de integração (36/36 no arquivo da Central Financeira), `tsc -b` e
  `vite build` limpos.
- **Restante da sprint** (auditoria final de experiência premium, validação final) segue em
  etapas subsequentes.

## 🌟 Sprint de Refinamento Premium — Etapa 8: Auditoria final de experiência premium

Continuação da sprint (item 18 do escopo original). Decisão em
`docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 18.

- **Auditoria de consistência** em todas as páginas de produção (Dashboard, Contas, Cartões,
  Financiamentos, Empréstimos, Transações, Transferências, Metas, Categorias, Tags, Calendário)
  contra estado vazio, loading, erro, responsividade, padding e cabeçalho — base já madura, só
  pequenas divergências reais encontradas.
- **Ajustes aplicados** (presentation-only, nenhuma regra de negócio nova): subtítulo do
  cabeçalho do Dashboard padronizado (`mt-1`); botão de ação ("Novo/Nova X") adicionado ao
  estado vazio de Contas, Categorias, Tags, Transferências, Transações, Financiamentos e
  Empréstimos (reaproveitando o mesmo handler de criação já usado pelo botão do cabeçalho);
  busca de `MetasPage` trocada pelo `SearchBar` compartilhado (antes reimplementava manualmente
  e só aparecia com 5+ metas).
- **Lacunas conhecidas, documentadas e não corrigidas nesta etapa**: onboarding do Calendário
  para conta zerada e o placeholder de histórico de compras em `CartaoDetalhePage` (dependem de
  extensão de escopo maior — filtro por cartão em `/transacoes` — não de um ajuste pontual).
- **Validação**: `tsc -b` e `vite build` limpos.

## 🗺️ Próximas etapas (não implementadas ainda)

- CRUD de `Alerta`, a última entidade de domínio pendente, seguindo o mesmo padrão do
  `Conta`/`Categoria`/`Tag`/`Cartão`/`Fatura`/`Transação`/`Parcelamento`/`Transferência`/
  `Conta Recorrente`/`Financiamento`/`Empréstimo`/`Meta`/`Anexo` — `parcelamento_id`,
  `origem_recorrente_id`, `financiamento_id` e `emprestimo_id` têm validação de posse em
  `TransacaoService`; `meta_id` teve sua ESCRITA removida de `TransacaoCreate`/`TransacaoUpdate`
  no Refatoramento de Metas/Transferências (aportes/resgates viram `Transferencia`, não
  `Transacao`) — a coluna e a leitura (`TransacaoRead.meta_id`, filtro `GET
  /transacoes?meta_id=`) continuam sustentando o histórico legado congelado. Não resta nenhum
  vínculo manual NOVO aceito sem checagem. `TipoEntidadeReferenciavel` (enum polimórfico) já
  existe, reservado para `Alerta` referenciar qualquer entidade — ver
  `docs/analise-arquitetural-anexo.md`
- `ContratoCreditoMixin.conta_id` permanece `nullable=True` no banco por decisão
  deliberada — obrigatoriedade é regra de negócio, validada redundantemente em
  `FinanciamentoService.criar()` e `EmprestimoService.criar()` (ver Conflito 2 da seção "CRUD
  de Financiamento" e `docs/analise-arquitetural-emprestimo.md`); não é mais um item em
  aberto
- Suporte a `FrequenciaRecorrencia.SEMANAL`/`ANUAL` em `ContaRecorrente` — fora de escopo por
  decisão explícita do usuário nesta etapa (YAGNI); o enum já existe, só falta a lógica de
  datas correspondente quando houver uso real
- Bloqueio de exclusão de `Categoria` em uso por `Transacao` (marcador
  `# TODO(categoria-em-uso)` já no lugar certo em `CategoriaService.desativar()`)
- Avaliar bloqueio de desativação de `Cartão` com fatura em aberto (mesmo espírito do
  bloqueio já aplicado a `Categoria` em uso, ver TODO acima) — ainda não implementado por
  não ter sido pedido explicitamente em nenhuma etapa até agora