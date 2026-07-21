# Deploy pré-alfa — Finanças Pessoais

Data: 2026-07-21

## 1. Objetivo

Colocar o projeto no ar como uma **pré-alfa para usuários selecionados**,
usando a infraestrutura mais barata possível sem comprometer a integridade
dos dados financeiros reais que esses usuários vão inserir. Não é um
lançamento público: contas são criadas manualmente pelo próprio
desenvolvedor (Sant), sem cadastro self-service divulgado.

## 2. Decisões tomadas

Três decisões foram tomadas explicitamente antes de qualquer código ser
alterado:

1. **Hospedagem**: Render (PaaS), plano free para os dois serviços
   (backend e frontend).
2. **Banco de dados**: Postgres gerenciado **externo e gratuito** (Neon ou
   Supabase) — não o SQLite local nem o Postgres pago do Render.
3. **Autenticação**: continua sendo o sistema já existente (email/senha,
   JWT) — as contas dos usuários selecionados são criadas manualmente,
   sem abrir cadastro público.

### 2.1 Por que não SQLite em produção

O plano free do Render **não tem disco persistente** (isso é um recurso
pago, ~$0.25/GB/mês). Um serviço free roda em um filesystem efêmero: a
cada novo deploy (e possivelmente a cada reinício por inatividade), o
arquivo `financas.db` seria perdido. Como esta pré-alfa vai guardar dados
financeiros reais de usuários reais, isso é inaceitável mesmo em fase
inicial — perder os dados de alguém que confiou o próprio extrato
bancário no app seria pior do que não ter lançado ainda.

### 2.2 Por que Postgres externo, não o do Render

Render também vende Postgres gerenciado, mas é pago. Neon e Supabase têm
planos gratuitos permanentes (diferente do Render/Railway/Fly.io, que em
2026 não têm mais free tier real para o *compute* em si — pesquisado
nesta sessão antes de decidir). Rodar o backend no Render (free) e o
banco no Neon/Supabase (free) mantém o custo total em zero para a fase de
pré-alfa.

## 3. Trabalho de código realizado

### 3.1 Validação real contra Postgres

Antes de recomendar Postgres, todas as migrations do Alembic (do início
do projeto até a mais recente, expansão de Contas Recorrentes) foram
rodadas de ponta a ponta contra um Postgres real (instância efêmera criada
no ambiente de trabalho só para este teste, depois descartada). Isso
revelou **6 bugs de portabilidade** que existiam desde o início do
projeto e nunca tinham aparecido porque o projeto sempre rodou sobre
SQLite:

| Migration | Problema | Causa |
|---|---|---|
| `7c04a41962ca` (papel do usuário) | `UndefinedObject: type "tipopapel" does not exist` | `op.add_column` sozinho não cria o tipo ENUM nativo no Postgres — só `create_table` faz isso automaticamente |
| `d6639c25b68c` (bandeira do cartão) | mesmo erro, para o tipo `bandeira` | mesma causa |
| `e7c1a2b9d4f6` (frequência de contribuição de Meta) | mesmo erro, para `frequenciacontribuicao` | mesma causa |
| `9152217acac1` (status da fatura) | valor novo (`PARCIALMENTE_PAGA`) nunca era adicionado ao tipo nativo já existente | `ALTER COLUMN ... TYPE` com o mesmo nome de tipo não amplia um ENUM Postgres sozinho — precisa de `ALTER TYPE ... ADD VALUE` explícito |
| `c8d1e4f7a2b5` (expansão de Contas Recorrentes) | as 5 frequências novas (DIÁRIA, QUINZENAL, BIMESTRAL, TRIMESTRAL, SEMESTRAL) nunca tinham sido adicionadas ao tipo nativo `frequenciarecorrencia` (criado com só 3 valores na migration inicial) | mesma causa do item anterior — gap que existia desde a expansão de Contas Recorrentes (sessão anterior), só nunca tinha sido percebido |
| `7544876ab513` (seed de categorias) e `f2a5c8e1b3d7` (conta oculta/cofrinho) | `UndefinedFunction: last_insert_rowid()` e `column is of type boolean but expression is of type integer` | SQL cru usando `last_insert_rowid()` (função exclusiva do SQLite) e literais `1`/`0` para colunas boolean (Postgres exige `true`/`false`) |

Todos os 6 pontos foram corrigidos diretamente nos arquivos de migration
já existentes (não em migrations novas) — são bugs de portabilidade, não
mudanças de modelagem, então corrigir o arquivo original é o tratamento
correto (essas migrations nunca rodaram em produção real, só em
desenvolvimento). Downgrades não foram auditados com o mesmo rigor (só a
direção `upgrade` importa para o deploy).

Após as correções, a suíte completa de migrations rodou limpa contra um
Postgres real, e um smoke test cobrindo especificamente os pontos
corrigidos (usuário com papel, cartão com bandeira, conta recorrente com
cada uma das 8 frequências e cada status, fatura com status
PARCIALMENTE_PAGA, meta com frequência de contribuição) passou sem
nenhum erro. A suíte de testes completa (611 unitários + 452 de
integração) também foi re-executada contra SQLite para confirmar que
nada quebrou no caminho de desenvolvimento local.

### 3.2 Driver Postgres

`psycopg2-binary==2.9.9` adicionado a `backend/requirements.txt`. Não é
necessário declarar `+psycopg2` na `DATABASE_URL` — o SQLAlchemy já usa
esse driver por padrão para qualquer URL `postgresql://...`.

`app/db/session.py` não precisou de nenhuma mudança: o
`connect_args={"check_same_thread": False}` já era condicional a
`DATABASE_URL.startswith("sqlite")`, então em produção (Postgres) esse
ajuste simplesmente não se aplica, sem precisar de nenhum `if` novo.

### 3.3 Arquivos de deploy

`render.yaml` (raiz do projeto) — Blueprint do Render com dois serviços:

- **`financas-backend`**: runtime Python nativo (sem Docker), roda
  `alembic upgrade head` antes de subir o `uvicorn` a cada deploy.
  `SECRET_KEY`, `DATABASE_URL` e `CORS_ORIGINS` ficam marcadas
  `sync: false` — nunca vão para o repositório, são preenchidas
  manualmente no dashboard do Render.
- **`financas-frontend`**: site estático (build do Vite), com uma regra
  de rewrite `/* -> /index.html` (obrigatória porque o app usa
  `BrowserRouter` do React Router — sem essa regra, atualizar a página em
  qualquer rota que não seja `/` retornaria 404). `VITE_API_URL` também
  fica `sync: false`.

### 3.4 Frontend

Nenhuma mudança de código foi necessária: `frontend/src/api/httpClient.ts`
já lia a URL base de `import.meta.env.VITE_API_URL`, sem nenhum valor
hardcoded de fallback. Só falta configurar essa variável no Render
(ver seção 4).

### 3.5 Repositório Git

O projeto não tinha nenhum repositório Git até esta etapa — condição
necessária para o Render (ou qualquer PaaS) conseguir buscar o código.
Foram feitos:

- `git init` na raiz do projeto.
- Ajustes no `.gitignore` raiz: os backups manuais do banco
  (`financas.db.backup-*`, `financas.db.bak-*`) não eram cobertos pelo
  padrão `*.db` já existente (esse padrão só bate com nomes que
  *terminam* em `.db`) — corrigido antes do primeiro commit, para nunca
  versionar snapshots do banco com dados financeiros reais. Também
  adicionados `.backend.pid`/`.frontend.pid` (estado de processo local)
  e os arquivos temporários que o próprio Vite gera ao carregar
  `vite.config.ts` (`vite.config.*.timestamp-*.mjs`), que tinham ficado
  soltos no diretório do frontend.
- Primeiro commit feito (570 arquivos, working tree limpo depois).

**Ainda falta**: criar o repositório remoto (GitHub) e dar `git push` —
isso exige a autenticação do próprio Sant (GitHub CLI ou navegador), não
pode ser feito por mim. Ver checklist na seção 5.

## 4. O que falta configurar manualmente (não pode ser automatizado)

Estas ações exigem contas/credenciais pessoais e por isso precisam ser
feitas por Sant diretamente:

1. Criar conta no Neon **ou** Supabase (grátis) e provisionar um banco
   Postgres. Copiar a *connection string* (formato
   `postgresql://usuario:senha@host/banco?sslmode=require`).
2. Criar repositório no GitHub e rodar `git push` (comandos exatos na
   seção 5).
3. Criar conta no Render, conectar o repositório, e criar o Blueprint a
   partir do `render.yaml` já commitado.
4. Preencher no dashboard do Render as variáveis marcadas `sync: false`:
   `SECRET_KEY` (gerar uma nova, nunca reaproveitar a do `.env` local),
   `DATABASE_URL` (do passo 1), `CORS_ORIGINS` (URL do frontend, só
   depois que o Render atribuir a URL definitiva) e `VITE_API_URL` (URL
   do backend, mesma ressalva).
5. Criar manualmente, via `/registrar` do próprio app já no ar, a conta
   de cada usuário selecionado para a pré-alfa.

## 5. Checklist de execução (ordem sugerida)

Ver mensagem de resposta desta sessão para o passo a passo completo com
os comandos exatos — este documento registra o *porquê* de cada decisão;
o checklist operacional fica mais fácil de manter atualizado fora do
histórico do doc arquitetural.

## 6. Limitações conhecidas desta pré-alfa

- **Cold start**: o plano free do Render "dorme" o backend após 15
  minutos sem tráfego; a primeira requisição depois disso demora
  30–60 segundos para acordar o serviço. Aceitável para uma pré-alfa
  com poucos usuários avisados sobre isso; não seria para uma versão
  pública.
- **Sem backup automático do Postgres externo**: os planos free do
  Neon/Supabase têm políticas de retenção limitadas (variam por
  provedor). Não é backup no sentido de disaster recovery — para essa
  fase, o risco foi considerado aceitável dado o volume pequeno de
  usuários e dados.
- **Sem observabilidade dedicada**: logs ficam só no dashboard do Render
  (retenção limitada no free tier). Nenhum alerta proativo de erro foi
  configurado nesta etapa.
- **Downgrades de migration não auditados para Postgres**: só o caminho
  `upgrade` (o único que roda em produção) foi validado linha a linha.

## 7. Execução real do deploy — problemas encontrados e resolvidos

A validação da seção 3.1 rodou contra um Postgres genérico efêmero, então
não pegou dois problemas específicos do Supabase e um erro de digitação -
registrados aqui para a próxima vez (ou se um novo usuário selecionado
precisar de outra instância):

1. **Conexão direta do Supabase é IPv6-only** (a menos que se pague o
   add-on de IPv4) e o Render não tem saída IPv6 - `psycopg2` falhava com
   `Network is unreachable`. Resolvido usando o **Transaction pooler** do
   Supabase (host `aws-N-<regiao>.pooler.supabase.com`, porta `6543`,
   usuário no formato `postgres.<project-ref>`, não só `postgres`) - essa
   é a via de conexão IPv4 recomendada pelo próprio Supabase para
   plataformas externas.
2. **`configparser` do Alembic quebra com senha percent-encoded**: `%3F`
   (por exemplo) é interpretado como início de uma interpolação
   (`%(nome)s`), levantando `ValueError: invalid interpolation syntax`
   mesmo só ao *armazenar* o valor. Corrigido em `alembic/env.py`
   escapando `%` como `%%` antes de `config.set_main_option` (o
   configparser decodifica de volta ao ler).
3. **CORS_ORIGINS precisa bater EXATAMENTE com a URL do frontend** (sem
   barra final, protocolo+host idênticos) - qualquer divergência de um
   caractere (fonte do dashboard pode confundir "0" com "o", por exemplo)
   quebra silenciosamente com "blocked by CORS policy" no console do
   navegador. Mais seguro sempre copiar a URL com o botão de copiar do
   Render em vez de digitar/ler visualmente.

Com os três ajustes, o deploy ficou estável: backend e frontend "Live" no
Render, login/registro funcionando de ponta a ponta contra o Postgres do
Supabase.
