# Versionamento

Pedido do usuário (2026-07-22): exibir a versão do app no Header (ao lado do
menu do usuário) e mantê-la crescendo a cada mudança feita no projeto.

## Onde vive

**Duas cópias mantidas manualmente em sincronia** (não uma única fonte
injetada em build, como na primeira versão desta feature — ver "Histórico"
abaixo):

- `frontend/package.json`, campo `"version"` — convenção padrão do
  ecossistema npm, usada por ferramentas/CI.
- `frontend/src/version.ts`, constante `APP_VERSION` — é isso que
  `components/layout/Header.tsx` de fato importa e exibe (`Alpha
  {APP_VERSION}` num selo discreto, visível a partir de `md`).

Sempre que a versão for bumped, os DOIS lugares mudam no mesmo commit.

Prefixo **"Alpha"** enquanto o projeto não tiver um primeiro release
estável (1.0.0) publicado — não é parte do número semântico em si.

## Histórico: por que não é injetada automaticamente do package.json

As duas primeiras tentativas desta feature usavam `vite.config.ts` (`define`)
para ler `package.json` em tempo de build e injetar como constante global
`__APP_VERSION__` — primeiro via `import { version } from "./package.json"`,
depois via `process.env.npm_package_version`. As duas funcionavam neste
ambiente de desenvolvimento/build, mas QUEBRARAM em produção no Render
(`ReferenceError: __APP_VERSION__ is not defined`, app inteiro derrubado
pelo ErrorBoundary) — confirmado diretamente contra o site real nas duas
vezes, sem conseguir identificar a causa exata (sem acesso aos logs de
build do Render). Depois da segunda falha, a decisão foi parar de depender
de qualquer mecanismo de build/ambiente para isso e usar uma constante de
código-fonte simples (`version.ts`), ao custo de precisar bump-ar dois
arquivos em vez de um.

## Convenção de bump (a seguir em toda sessão futura)

- **Patch** (`0.1.0` → `0.1.1` → `0.1.2` ...): a cada ajuste, correção de
  bug ou pequena melhoria — a maioria das mudanças do dia a dia.
- **Minor** (`0.1.x` → `0.2.0`, reseta o patch para `0`): a cada CRUD novo
  (uma entidade de domínio completa) ou funcionalidade grande (ex.: a
  Etapa de Gráficos, a expansão de Contas Recorrentes). Regra prática:
  se o trabalho gerou (ou merece) um novo `docs/analise-arquitetural-*.md`
  próprio, é minor: senão, é patch.
- **Major** (`X.0.0`): fora de escopo por ora — só quando o projeto sair
  do estágio "Alpha".

Sempre que uma mudança for concluída e validada (testes/build passando),
bump o campo `version` de `frontend/package.json` de acordo com a regra
acima, como parte do mesmo commit.
