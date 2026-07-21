# Auditoria técnica — Finanças Pessoais

Relatório de estado do projeto, cobrindo tudo que foi construído até aqui: backend
(encerrado, exceto correções pontuais), frontend (Etapa F1 concluída, Design System
projetado e ainda não implementado), banco de dados e documentação. Avaliação honesta,
sem inflar o que ainda não existe.

## 1. Visão geral do projeto

**Objetivo principal:** sistema de finanças pessoais multi-usuário (arquitetura preparada
para múltiplos usuários isolados, mas de uso real por uma única pessoa) que centraliza
contas, cartões, faturas, transações, parcelamentos, dívidas formais (financiamento/
empréstimo) e metas de economia num só lugar, com uma camada de agregação (Central
Financeira) que dá uma visão consolidada sem exigir cálculo manual em planilha.

**Problema que resolve:** hoje é comum gerenciar vida financeira espalhada entre app do
banco, app do cartão, planilha manual e memória — nenhum desses dá uma visão unificada de
saldo real, dívida total e fluxo de caixa do mês. O projeto resolve isso modelando o domínio
financeiro completo (incluindo casos que apps genéricos não cobrem bem, como cronograma de
amortização PRICE/SAC de um financiamento) e devolvendo essa visão consolidada via API.

**Maturidade atual:** **backend em nível de MVP maduro / quase produção para o escopo de uso
pessoal** (14 entidades completas, testado, documentado); **frontend em estágio de
protótipo inicial** (só autenticação funciona; nenhuma tela de negócio existe ainda). Como
produto utilizável ponta a ponta por um usuário final, o projeto está em **fase de
protótipo** — o backend sozinho não é "o produto", e o frontend ainda não expõe nenhuma
funcionalidade financeira de fato.

## 2. Tudo que já foi implementado

### Backend

**Arquitetura:** `Router → Service → Repository` estrito, sem exceção em nenhuma das 14
entidades. `Router` só traduz HTTP↔Schema e chama um método do Service; `Service` concentra
toda regra de negócio e nunca importa nada de FastAPI; `Repository` é a única camada que
toca SQLAlchemy, com uma classe genérica (`SQLAlchemyRepository[ModelType]`) reutilizada por
toda entidade e Repositories específicos só quando precisam de query própria (agregação,
busca por nome, etc.). Exceções de domínio (`NotFoundError`, `BusinessRuleError`,
`ConflictError`, `NaoAutenticadoError`, `AcessoNegadoError`) são traduzidas para HTTP num
único lugar (`app/main.py`), então nenhum Router tem `try/except`.

**Linguagem/frameworks:** Python + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + pytest.

**Banco de dados:** SQLite (arquivo único) — escolha deliberada para um app de uso pessoal
sem necessidade de escala (ver seção 3).

**Models existentes (16 tabelas):** `Usuario`, `SessaoUsuario` (infraestrutura de auth) e 14
entidades de domínio: `Conta`, `Categoria`, `Tag`, `Cartao`, `Fatura`, `Transacao`,
`Parcelamento`, `Transferencia`, `ContaRecorrente`, `Financiamento`, `Emprestimo`, `Meta`,
`Anexo`, mais a tabela associativa `transacao_tag` (N-N). `Alerta` existe só como
model/enum esqueleto — **sem Repository, Service, Schema ou Router** (não implementado).

**Relacionamentos:** `Transacao` é o hub central — toda entrada/saída real de dinheiro passa
por ela (`tipo` distingue RECEITA/DESPESA em vez de duas tabelas). Pertence a `Conta` OU
`Cartao` (nunca os dois, `CHECK` constraint), a no máximo um de
`Parcelamento`/`Financiamento`/`Emprestimo`, opcionalmente a `Categoria`, N-N com `Tag`,
opcionalmente a `Meta`. `Fatura` pertence a `Cartao`; `Cartao` aponta para a `Conta` que paga
a fatura. `Categoria` é hierárquica (auto-relacionamento pai/filho). `Anexo` pertence sempre
a uma `Transacao` (posse transitiva, sem `usuario_id` próprio). `Financiamento`/`Emprestimo`
compartilham campos via `ContratoCreditoMixin` mas são tabelas separadas.

**Autenticação/autorização:** JWT (HS256) de vida curta (15 min) para access token; refresh
token opaco (não-JWT), armazenado com hash SHA-256, vida de 30 dias, com **rotation** (cada
uso invalida o token e emite um novo) e suporte a múltiplas sessões/dispositivos
simultâneos. Logout escopado (uma sessão) e global (todas as sessões). Senha com bcrypt
(fator de custo 12). Autorização por papel (`TipoPapel`, hoje só `USER`, arquitetura já
preparada para mais). Isolamento multi-tenant: toda entidade filtra por `usuario_id` (direto
ou transitivo) e devolve 404 uniforme tanto para "não existe" quanto para "é de outro
usuário" — proteção deliberada contra enumeração/BOLA (OWASP API Security Top 10).

**APIs/endpoints:** 15 routers (`auth` + 13 entidades de domínio + `anexo` +
`central-financeira`), cobrindo CRUD completo onde faz sentido (algumas entidades não têm
`PATCH`/`DELETE` por decisão de design — ex. `Parcelamento`, `Financiamento`, `Emprestimo`,
`Transferencia`) mais ações dedicadas (`POST /financiamentos/{id}/parcelas/{n}/pagar`,
`POST /faturas/{id}/pagamentos`, `POST /contas-recorrentes/{id}/gerar-ocorrencias-pendentes`).
`Central Financeira` expõe 11 endpoints agregadores somente-leitura (resumo geral, saldo
consolidado, resumos por entidade, agenda financeira, visão mensal, indicadores) — camada de
orquestração sem Repository próprio, reaproveitando os Services já existentes.

**Validações:** Pydantic valida formato/tipo em toda entrada; Services validam posse cruzada
(ex. categoria pertence ao usuário, cartão está ativo), regras estruturais (conta XOR
cartão, faixa/duplicidade de `numero_parcela`, `valor_entrada` < `valor_financiado`) e
travas de imutabilidade (transação de fatura fechada, status de parcela de contrato de
crédito só muda pela ação dedicada de pagamento).

**Migrations:** Alembic, uma migration por mudança de schema, cada uma validada em ciclo
completo `upgrade → downgrade → upgrade → check` contra banco descartável antes de ser
aceita — inclusive um caso real (documentado em `revisao-tecnica-anexo.md`) em que só o
ciclo completo pegou uma corrupção que `upgrade`+`check` isolados não detectavam.

**Regras de negócio de destaque:** saldo (`Conta.saldo_atual`), status/valor de `Fatura` e
progresso de `Meta` são **sempre calculados, nunca armazenados** — única exceção é
`saldo_devedor` de `Financiamento`/`Emprestimo` (armazenado e mutado só via `pagar_parcela`,
porque PRICE/SAC não é uma soma simples). Cronograma de amortização PRICE/SAC centralizado
em `app/core/amortizacao.py`, compartilhado pelas duas entidades de crédito. Resolução
automática de fatura aberta ao lançar uma compra no cartão. Geração *eager* de parcelas
(Parcelamento/Financiamento/Empréstimo) vs. geração *lazy* de ocorrências
(Conta Recorrente, só quando pedido via ação dedicada — nunca por scheduler).

### Frontend

**Stack:** React 18 + TypeScript 5 + Vite 5 + Tailwind 3 + React Router 7 + TanStack Query 5
+ React Hook Form 7 + Zod 4 + `fetch` nativo (sem axios). Aprovadas e ainda não instaladas:
`motion` (Framer Motion) e `lucide-react`, para a próxima etapa.

**Estrutura de páginas/componentes:** esqueleto completo de pastas criado
(`api/`, `types/`, `schemas/`, `services/`, `contexts/`, `hooks/`, `components/{ui,layout,
domain}`, `layouts/`, `pages/`, `routes/`, `utils/`), mas **só o fluxo de autenticação está
implementado dentro dele**: `LoginPage`, `RegistrarPage`, `AuthLayout`, `AppLayout` (casca
mínima, sem navegação real ainda), `ProtectedRoute`, e uma `DashboardPage` que é hoje um
placeholder ("Olá, {nome}") — nenhuma tela de Conta/Cartão/Transação/etc. existe.

**Design system:** **documentado por completo** (`docs/design-system.md` — identidade
visual, tokens de cor/tipografia/espaçamento/radius/sombra/blur/motion, padrões de
dashboard/formulário/tabela/gráfico, acessibilidade, responsividade) mas **zero
implementado em código** — o app ainda roda com Tailwind no default (cinza/branco), não com
os tokens definidos no documento.

**Responsividade:** breakpoints e comportamento mobile definidos no documento de design;
não implementados (nenhum componente foi testado/ajustado para telas pequenas ainda).

**Animações/microinterações:** especificadas em detalhe (durações, curvas de easing,
presets de spring do Framer Motion, regras de `prefers-reduced-motion`); não implementadas —
a UI hoje não tem nenhuma transição além do default do navegador.

**Estados e gerenciamento de dados:** decisão arquitetural fechada e parcialmente
implementada — React Query é a única infraestrutura de estado de servidor (sem
Redux/Zustand/Context para dado de entidade); hoje só cobre o fluxo de autenticação
(`AuthContext` usa `useQuery`/`useMutation` para `/auth/me`, login, registro, logout). Nenhum
hook de entidade de domínio (`useContasQuery` etc.) existe ainda.

**Integrações com backend:** só `/auth/*` foi integrado e validado ponta a ponta (inclusive
testado manualmente contra o backend real: registro, login, refresh com rotation, reuso de
token antigo rejeitado, 401/422 nos dois formatos de erro, CORS). Os outros 14 routers do
backend (incluindo Central Financeira, que já está pronta para consumo) ainda não têm
nenhuma chamada correspondente no frontend.

### Banco de dados

**Tabelas existentes:** 16 no total — `usuarios`, `sessoes_usuario`, `contas`, `categorias`,
`tags`, `transacao_tag`, `cartoes`, `faturas`, `transacoes`, `parcelamentos`,
`transferencias`, `contas_recorrentes`, `financiamentos`, `emprestimos`, `metas`, `anexos`.

**Estrutura atual:** normalizada, sem duplicação de dado financeiro entre tabelas (tudo
converge para `Transacao`). Uso extensivo de `CHECK`/`UNIQUE` constraints como segunda
camada de defesa das mesmas regras já validadas no Service (ex. `CHECK` de conta XOR cartão
em `Transacao`, `UNIQUE(usuario_id, descricao)` em `Meta`) — redundância deliberada,
documentada, não acidental.

**O que está bem definido:** isolamento multi-tenant consistente em toda tabela; separação
clara entre dado armazenado e dado calculado (seção 2, Backend); `ContratoCreditoMixin`
evita duplicar definição de coluna entre `Financiamento`/`Emprestimo` sem forçar as duas
entidades a compartilhar Service; toda FK com `ondelete` pensado explicitamente (cascade
físico de `Anexo` ao excluir sua `Transacao`, por exemplo).

**Possíveis problemas de modelagem:**
- **SQLite não suporta `ALTER TABLE` nativo de forma completa** — toda migration deste
  projeto precisou de `batch_alter_table` manual (recria a tabela inteira por trás dos
  panos). Funciona e está bem testado, mas é atrito recorrente documentado em várias
  revisões técnicas, não uma limitação zero-custo.
- **SQLite não é adequado para escrita concorrente de múltiplos processos/conexões
  simultâneas.** Não é um problema hoje (uso single-user), mas é o limite real de "até onde
  esta escolha de banco escala" — se o projeto um dia precisar de acesso simultâneo real
  (ex. app mobile + web ao mesmo tempo), migrar para Postgres seria necessário.
- **Sem índices explícitos além dos implícitos de PK/FK/UNIQUE** — não há, por exemplo, um
  índice composto em `(usuario_id, data)` de `Transacao` para acelerar os filtros mais
  comuns. Irrelevante no volume de dado de um usuário único; passaria a importar se o volume
  de transações crescesse muito (anos de histórico).
- **`Alerta` ficou pela metade** — o enum `TipoEntidadeReferenciavel` e o model existem no
  banco, mas sem Service/Router; é uma tabela "fantasma" hoje (existe fisicamente, nunca é
  escrita por nenhum código).

### Documentação

**Documentos criados:** `README.md` (arquitetura, modelo de domínio, autenticação, como
rodar, suíte de testes), ~15 `docs/analise-arquitetural-<entidade>.md` (uma por entidade,
escritas **antes** do código correspondente), ~14 `docs/revisao-tecnica-<entidade>.md`
(revisão crítica **depois** do código, caçando problemas reais — não uma formalidade),
`docs/decisao-performance-saldo.md`, `docs/analise-arquitetural-central-financeira.md` +
`docs/revisao-tecnica-central-financeira.md`, `docs/analise-arquitetural-frontend.md` (duas
revisões, incorporando feedback), `docs/design-system.md`, e este relatório.

**Decisões arquiteturais importantes:** cobertas em detalhe na seção 3.

**Padrões utilizados:** o ciclo **análise → implementação → teste → revisão técnica crítica**
se repete de forma idêntica em toda entidade do backend, sem exceção — é o padrão mais
consistente do projeto inteiro e o que mais diferencia este trabalho de um CRUD comum (ver
seção 8).

## 3. Decisões arquiteturais importantes tomadas

**`Transacao` como entidade central, não um apêndice de cada módulo.** Em vez de cada
funcionalidade (cartão, financiamento, meta) guardar seu próprio histórico de movimentação,
toda entrada/saída real de dinheiro é uma linha em `Transacao`, e as outras entidades
*geram* ou *referenciam* transações (`Parcelamento` gera uma `Transacao` por parcela,
`Meta` soma `Transacao`s com `meta_id` apontando para ela). Motivo: evita duplicação de dado
financeiro e garante que "quanto dinheiro entrou/saiu" tenha uma única fonte de verdade,
mesmo quando a origem é diferente (compra parcelada vs. parcela de financiamento vs.
transferência).

**Parcelamento ≠ Financiamento ≠ Empréstimo — três entidades, não um campo `tipo`.**
`Parcelamento` é uma compra dividida (cartão ou loja), sem contrato de crédito formal.
`Financiamento` é um contrato de crédito atrelado a um bem, com sistema de amortização
(PRICE/SAC) e entrada opcional. `Empréstimo` tem a mesma estrutura de contrato
(`ContratoCreditoMixin` compartilhado) mas propósito geral e **sempre** gera uma transação de
RECEITA no desembolso (diferente da entrada opcional do Financiamento). Motivo: são
entidades com relação diferente com `Transacao` e propensas a ganhar regras próprias no
futuro (ex. margem consignável só existe em empréstimo consignado) — modelar como um `tipo`
único obrigaria a lógica condicional a se espalhar por todo `Service`, o oposto de
baixo acoplamento.

**"Calculado, nunca armazenado", com uma única exceção documentada.** Saldo de conta, status/
valor de fatura, progresso de meta — todos calculados em tempo real a partir de `Transacao`,
nunca guardados numa coluna que poderia desincronizar. A exceção (`saldo_devedor` de
Financiamento/Empréstimo) existe porque PRICE/SAC não é uma soma simples de transações — o
Service que sabe decrementar esse valor (`pagar_parcela`) é o único ponto de escrita, nunca
editável por fora. Motivo: elimina uma classe inteira de bug ("saldo desatualizado") ao
custo de recalcular em toda leitura — aceitável no volume de dado de um usuário único.

**Redesenho do CRUD de Anexo, de polimórfico para posse transitiva.** O model original
(especulativo, do desenho inicial do domínio) usava `entidade_tipo`/`entidade_id`
polimórfico, igual a `Alerta`. Quando a regra real foi dada ("Anexo pertence sempre a uma
Transação"), o desenho foi simplificado: sem `usuario_id` próprio, posse sempre validada
delegando para `TransacaoService.obter()`. Motivo: o polimorfismo nunca tinha sido
exercitado por nenhum código real: manter um desenho especulativo que a regra de negócio
real contradiz é dívida técnica sem benefício, então foi trocado antes de acumular mais
código em cima dele.

**Central Financeira como orquestração pura, sem Repository próprio.** Em vez de uma camada
elaborada com abstrações por seção (o desenho especulativo original cogitava um
`CardProvider`/Protocol por tipo de card do dashboard), a implementação final é um único
Service que injeta os 8 Services de domínio existentes e só compõe o resultado deles — zero
SQL direto, zero regra de negócio nova, zero duplicação de cálculo (um filtro `status` e uma
agregação `SUM` foram as únicas duas adições mecânicas a `TransacaoService`, para não somar
em Python o que o banco já faz melhor). Motivo: para exatamente 11 endpoints conhecidos, a
abstração elaborada seria over-engineering — o Service único, mais simples, entrega o mesmo
resultado com menos superfície para manter.

**Frontend com duas camadas, não três.** O backend tem Router→Service→Repository porque tem
três responsabilidades genuinamente distintas. O frontend não tem regra de negócio nenhuma
(está toda no backend) — replicar três camadas seria abstração sem função real. Ficou:
acesso a dado (`api/`+`services/`+`types/`+`schemas/`) e apresentação
(`hooks/`+`components/`+`pages/`+`layouts/`), com React Query como a única infraestrutura de
estado de servidor (sem Redux/Zustand/Context de entidade).

**Dark-only na interface, sem toggle claro/escuro.** Decisão tomada na etapa de Design
System, reinterpretando uma exclusão de escopo anterior ("dark mode fora de escopo" foi lido
como "não construir uma feature de alternância", não como "a interface é obrigatoriamente
clara"). Motivo: as referências visuais pedidas (Linear, Raycast, Vercel, Framer) são todas
dark-first, e suportar só um tema é literalmente menos trabalho que suportar dois — sinalizado
explicitamente para validação por ser a reinterpretação mais forte do documento.

## 4. Estado atual do projeto

| Funcionalidade | Status | % concluído | Observações |
|---|---|---|---|
| Cadastro/login | 🟢 Funcional ponta a ponta | 90% | Backend + frontend completos e validados contra o servidor real; falta "esqueci minha senha" (não existe em nenhuma camada) e tela de "sair de todos os dispositivos" (endpoint existe, sem UI) |
| Dashboard financeiro | 🟡 Backend pronto, frontend não iniciado | 25% | 11 endpoints de agregação prontos e testados; `DashboardPage` é um placeholder sem nenhum dado real |
| Cadastro de receitas | 🟡 Backend pronto, frontend não iniciado | 35% | É parte do CRUD de `Transacao` (`tipo=RECEITA`), 100% funcional via API, zero tela |
| Cadastro de despesas | 🟡 Backend pronto, frontend não iniciado | 35% | Mesma base de `Transacao` (`tipo=DESPESA`) |
| Categorias | 🟡 Backend pronto, frontend não iniciado | 35% | CRUD completo + hierarquia no backend, zero tela |
| Contas bancárias | 🟡 Backend pronto, frontend não iniciado | 35% | CRUD + cálculo de saldo prontos, zero tela |
| Cartões | 🟡 Backend pronto, frontend não iniciado | 35% | CRUD + `limite_disponivel` calculado, zero tela |
| Faturas | 🟡 Backend pronto, frontend não iniciado | 35% | Ciclo completo (fechar, pagar parcial/total) no backend, zero tela |
| Parcelamentos | 🟡 Backend pronto, frontend não iniciado | 35% | Geração eager de parcelas funcional, zero tela |
| Financiamentos | 🟡 Backend pronto, frontend não iniciado | 35% | Cronograma PRICE/SAC completo, zero tela |
| Metas | 🟡 Backend pronto, frontend não iniciado | 35% | Progresso calculado, zero tela |
| Alertas | 🔴 Não implementado | 5% | Só model/enum existem no banco; sem Repository/Service/Router/Schema em lugar nenhum |
| Anexos | 🟡 Backend pronto, frontend não iniciado | 35% | Posse transitiva via Transação, zero tela de upload/listagem |
| Relatórios | 🔴 Não implementado | 10% | Nenhuma feature de exportação (PDF/CSV) existe; o dado para gerar relatórios já existe via Central Financeira |
| Gráficos | 🔴 Não implementado | 5% | Nenhuma lib de gráfico escolhida ainda (decisão adiada pra Etapa F5); dado numérico já disponível via API |
| Configurações | 🔴 Não implementado | 10% | Sem tela de perfil/preferências; `logout-todas` existe só como endpoint |
| Segurança | 🟡 Base sólida, hardening pendente | 60% | JWT+rotation+bcrypt+BOLA-safe muito bem feitos; falta rate limiting (TODO no código), headers de segurança, HTTPS/produção |
| Deploy | 🔴 Não iniciado | 0% | Sem Docker, sem CI/CD, sem ambiente de produção configurado |

## 5. Percentual real de conclusão

**Projeto completo: ~38%**

- **Backend: 85%** — 14 de 15 entidades com CRUD completo, testado (788 testes) e
  documentado; falta só `Alerta` e hardening de produção (rate limiting). Para o escopo de
  uso pessoal que o projeto se propõe, está muito perto do teto.
- **Frontend: 10%** — só o fluxo de autenticação e o esqueleto de pastas existem. Nenhuma
  tela de negócio (a parte que o usuário final realmente usa todo dia) foi construída.
- **Banco de dados: 88%** — schema maduro, normalizado, migrations validadas em ciclo
  completo. O teto de 100% não é atingido por uma limitação estrutural conhecida (SQLite
  não escala para escrita concorrente), não por descuido de modelagem.
- **UX/UI: 12%** — o *plano* de design (`docs/design-system.md`) é extremamente maduro e
  detalhado; a *implementação visual* é praticamente zero (a aplicação hoje usa Tailwind
  default, sem nenhum dos tokens definidos). A nota reflete o que existe rodando, não o que
  está no papel.
- **Testes: ~55%** — backend com cobertura muito acima da média (unit + integração para
  toda regra de negócio e todo fluxo HTTP); frontend com **zero** teste automatizado (decisão
  consciente de adiar, registrada em `docs/analise-arquitetural-frontend.md`, mas ainda uma
  lacuna real).
- **Segurança: 60%** — os fundamentos (hash de senha, JWT com rotation, isolamento
  multi-tenant anti-BOLA) estão muito bem implementados; falta rate limiting, cabeçalhos de
  segurança HTTP, gestão de segredo além de `.env` manual, e qualquer configuração pensada
  para exposição fora de `localhost`.
- **Deploy/produção: 0%** — nenhum Dockerfile, pipeline de CI/CD, ambiente de hospedagem ou
  estratégia de backup do banco existe até agora.

O número geral (38%) não é a média simples das sete categorias — é ponderado pelo que
importa para "o sistema já é usável por um usuário final": um backend excelente que ninguém
consegue operar sem uma API client (Postman/curl) ainda não é um produto utilizável no dia a
dia, e é exatamente aí que o projeto está agora.

## 6. O que falta para chegar em 100%

### Obrigatório para MVP funcional
*(o que impede o sistema de ser realmente usado hoje)*

- Implementar o Design System em código (tokens Tailwind, componentes base) — Etapa F2.
- Sistema de formulários reutilizável (`FormField`, `MoneyInput`, `DateInput`, selects de
  domínio, `FormDialog`, `DeleteDialog`) — Etapa F3.
- Sistema de tabelas reutilizável (`DataTable`, filtro/ordenação/paginação client-side,
  estados vazio/loading) — Etapa F4.
- Dashboard real consumindo `/central-financeira/*` — Etapa F5.
- Telas de CRUD para as 13 entidades de domínio (Conta, Categoria, Tag, Cartão, Fatura,
  Transação, Parcelamento, Transferência, Conta Recorrente, Financiamento, Empréstimo, Meta,
  Anexo) — Etapa F6 em diante, já roteirizadas na ordem de implementação do backend.
- Decisão explícita sobre `Alerta`: implementar (backend + frontend) ou descartar
  formalmente do escopo — hoje é uma pendência "no limbo".

### Importante antes de produção
*(qualidade, segurança e estabilidade, mesmo sendo uso pessoal)*

- Rate limiting em `/auth/login` e `/auth/refresh` (já marcado como `TODO` no código).
- Testes automatizados de frontend, ao menos para o fluxo crítico (autenticação, submissão
  de formulário, tabela).
- Estratégia de backup do arquivo SQLite (hoje é um único arquivo local sem rotina de
  cópia).
- Logging/observabilidade mínima além do log local (algo tão simples quanto rotação de
  arquivo de log já ajudaria).
- Definir e documentar onde/como o app roda fora do `localhost` (mesmo que seja "um VPS
  pessoal" ou "Docker Compose na própria máquina") — hoje não há resposta para "como eu
  acesso isso do celular".
- HTTPS se o acesso deixar de ser só `localhost`.
- CI mínimo (rodar a suíte de 788 testes automaticamente a cada mudança, em vez de manual).

### Melhorias futuras
*(features extras, não bloqueiam uso diário)*

- Relatórios exportáveis (PDF/CSV).
- Gráficos avançados no dashboard (biblioteca de charting ainda não escolhida).
- Notificações reais de `Alerta` (push/email), se a entidade for implementada.
- Importação de extrato bancário (OFX/CSV) para reduzir lançamento manual.
- PWA/uso offline no celular.
- Toggle claro/escuro (hoje dark-only por decisão deliberada, ver seção 3).

## 7. Próximas etapas recomendadas

**Fase 1 — Fundação visual**
- Implementar `docs/design-system.md` em código (tokens, `tailwind.config.js`, componentes
  base) — Etapa F2.
- Sistema de formulários (Etapa F3) e sistema de tabelas (Etapa F4).

**Fase 2 — Dashboard**
- Etapa F5: Dashboard real consumindo os 11 endpoints da Central Financeira, com os
  `StatCard`s e o gráfico de fluxo de caixa definidos no Design System.

**Fase 3 — CRUD completo no frontend**
- Etapa F6 em diante, uma entidade por vez, mesma ordem do backend: Conta → Categoria → Tag
  → Cartão → Fatura → Transação → Parcelamento → Transferência → Conta Recorrente →
  Financiamento → Empréstimo → Meta → Anexo.

**Fase 4 — Fechar a lacuna do `Alerta`**
- Decidir implementar (análise arquitetural + backend + frontend, mesmo ciclo das outras 13
  entidades) ou remover formalmente do escopo documentado.

**Fase 5 — Hardening pré-produção**
- Rate limiting, testes de frontend, backup de banco, logging básico, CI mínimo.

**Fase 6 — Deploy**
- Escolher e configurar um ambiente real (Docker Compose/VPS/PaaS), HTTPS, variáveis de
  ambiente de produção, backup automatizado do SQLite (ou migração para Postgres se o
  ambiente escolhido pedir).

**Fase 7 — Melhorias (opcional, pós-uso real)**
- Relatórios exportáveis, gráficos avançados, importação de extrato, notificações.
