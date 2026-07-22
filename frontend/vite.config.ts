import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `process` não tem tipo aqui de propósito - este projeto de frontend
// nunca teve `@types/node` (decisão deliberada, ver comentário abaixo) e
// esse shim mínimo evita adicionar a dependência só por causa desta linha.
declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  // Versão exibida no Header (docs/versionamento.md) — injetada como
  // constante global `__APP_VERSION__` substituída estaticamente pelo
  // Vite/esbuild (nenhum fetch em runtime).
  //
  // `process.env.npm_package_version` (em vez do import direto de
  // `package.json` usado na primeira versão desta feature) - o import
  // funcionava neste sandbox mas quebrava em produção no Render
  // (`__APP_VERSION__ is not defined` em runtime, ErrorBoundary disparando
  // na tela toda): o import de JSON num `vite.config.ts` ESM depende de
  // como cada ambiente resolve module loading, algo que variou entre este
  // sandbox e o build real do Render sem explicação identificável nos
  // logs disponíveis. `npm_package_version` é preenchido pelo PRÓPRIO npm
  // sempre que um script roda via `npm run <algo>` (é exatamente como
  // `buildCommand: "npm install && npm run build"` do render.yaml invoca
  // isso) - não depende de nenhum loader/bundler, mecanismo bem mais
  // simples e portável entre ambientes. Sem dependência de Node
  // (`node:fs`/`@types/node`) de propósito - este projeto de frontend não
  // tinha nenhuma até agora.
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version ?? "0.0.0"),
  },
});
