# Versionamento

Pedido do usuário (2026-07-22): exibir a versão do app no Header (ao lado do
menu do usuário) e mantê-la crescendo a cada mudança feita no projeto.

## Onde vive

A versão é o campo `"version"` de `frontend/package.json` — única fonte de
verdade, nunca duplicada em outro arquivo. `vite.config.ts` lê esse valor em
tempo de build e injeta como constante global `__APP_VERSION__` (ver
`define` em `vite.config.ts` e a declaração de tipo em `src/vite-env.d.ts`).
`components/layout/Header.tsx` exibe `Alpha {__APP_VERSION__}` num selo
discreto, visível a partir de `md` (mesmo breakpoint do resto do Header).

Prefixo **"Alpha"** enquanto o projeto não tiver um primeiro release
estável (1.0.0) publicado — não é parte do número semântico em si.

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
