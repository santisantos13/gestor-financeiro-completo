# Análise arquitetural — pipeline de CI (GitHub Actions)

## 0. Pedido do usuário

Fechar o item "Deploy" do roadmap - backlog `t8`: rodar a suíte de testes (backend + frontend)
automaticamente a cada mudança, em vez de depender de alguém lembrar de rodar `pytest`/`npm test`
manualmente antes de cada `git push`.

## 1. Escolha: GitHub Actions, sem novo serviço externo

O repositório já vive no GitHub (`santisantos13/gestor-financeiro-completo`) - GitHub Actions é
gratuito para repositórios (minutos generosos, de sobra para uma suíte deste tamanho, hoje ~5-6
minutos de execução total) e não exige cadastro em mais um serviço de terceiro (diferente de
Render/Supabase/cron-job.org, já em uso por outras partes do projeto). Nenhuma outra opção
(CircleCI, Travis, etc.) foi considerada por não trazer nenhuma vantagem que justificasse sair do
próprio GitHub.

## 2. O que o pipeline faz (e o que NÃO faz)

`.github/workflows/ci.yml` - dois jobs independentes, rodando em paralelo:

- **`backend`**: `pip install -r requirements-dev.txt` (traz `pytest`/`pytest-cov`/`httpx` +
  tudo de `requirements.txt` via `-r`) seguido de `pytest -q` - toda a suíte (1159 testes:
  662 unit + 497 integração, contagem via `pytest --collect-only` em 2026-07-28, já refletindo o
  trabalho desta sessão). Python 3.11.9 - mesma versão declarada em `render.yaml`
  (`PYTHON_VERSION`), para o CI validar contra o mesmo runtime que roda em produção.
- **`frontend`**: `npm ci` (instala EXATAMENTE o que está em `package-lock.json`, mais
  determinístico que `npm install` para CI) seguido de `npx tsc -b` (checagem de tipos estrita do
  projeto inteiro), `npm test` (suíte Vitest) e `npm run build` (build de produção real via Vite -
  confirma que o bundle gera sem erro, não só que os tipos batem).

**Gatilho**: todo `push` na branch `main` e toda abertura/atualização de Pull Request - cobre
tanto "acabei de commitar direto" (fluxo atual deste projeto, sem PRs) quanto um fluxo futuro com
PRs, sem precisar reconfigurar nada.

**O que este pipeline deliberadamente NÃO faz** (fora de escopo, YAGNI):
- Não faz deploy. Continua 100% manual (`git push` disparando o auto-deploy já configurado no
  próprio Render, via `render.yaml`) - o CI só decide se o código está "verde", nunca decide
  publicar nada.
- Não calcula/publica cobertura de teste (`pytest-cov` já está instalado, mas nenhum gate de
  cobertura mínima foi pedido).
- Não roda lint/formatter (nenhuma ferramenta desse tipo existe hoje no projeto - adicionar um
  gate para uma ferramenta que não existe seria inventar uma regra nova sem pedido).

## 3. Variáveis de ambiente necessárias só para o CI passar

- **Backend**: `SECRET_KEY` não tem valor padrão em `app/core/config.py` de propósito (a aplicação
  nem sobe sem essa variável - nunca existe um segredo hardcoded/inseguro "só pra funcionar"). O
  workflow define uma string qualquer (`chave-de-teste-usada-somente-no-ci`) só para os testes
  conseguirem assinar/validar JWT em memória - nunca é o segredo real de produção, que continua
  vivendo só como variável de ambiente no dashboard do Render (`sync: false` em `render.yaml`).
  `DATABASE_URL` não precisa ser definida: todo teste de integração sobrescreve `get_db` com um
  SQLite em memória (`tests/integration/conftest.py`) antes de qualquer requisição.
- **Frontend**: `VITE_API_URL` recebe um valor qualquer (`https://ci-build-nao-publicado.invalid`)
  só para o `vite build` não falhar por variável ausente - este job nunca publica o bundle gerado,
  então o valor não importa de verdade.

## 4. Validação

O próprio pipeline É a validação - não há "teste do teste". Confirmado localmente antes de
commitar: `pytest -q` (suíte completa, 1159 testes) e `npx tsc -b` (checagem de tipos estrita do
projeto inteiro) passam limpos neste sandbox (2026-07-28). `npm test`/`npm run build` NÃO puderam
ser revalidados nesta sessão por uma limitação pontual do ambiente sandbox (spawn de processo
filho travando ao rodar Vitest/esbuild em produção aqui - não é um problema do código, `tsc -b`
já garante que os tipos/imports estão corretos) - o primeiro push vai confirmar os 4 passos do
pipeline (pytest, tsc, vitest, vite build) rodando de verdade no GitHub, num ambiente sem essa
limitação.
