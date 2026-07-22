import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { version } from "./package.json";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  // Versão exibida no Header (docs/versionamento.md) — lida do
  // package.json em tempo de BUILD (nunca hardcoded em dois lugares),
  // injetada como constante global `__APP_VERSION__` substituída
  // estaticamente pelo Vite/esbuild (nenhum fetch em runtime). Sem
  // dependência de Node (`node:fs`/`@types/node`) de propósito - este
  // projeto de frontend não tinha nenhuma até agora.
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
});
