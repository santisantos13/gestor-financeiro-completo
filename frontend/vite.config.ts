/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  // `test` é lido só pelo Vitest (`npm test` -> `vitest run`) - inerte para
  // `vite build`/`vite dev`, nunca executado no build de produção. Sem
  // globals (docs/analise-arquitetural-testes-frontend.md): cada teste
  // importa describe/it/expect/vi explicitamente de "vitest", em vez de
  // exigir `"types": ["vitest/globals"]` no tsconfig.json raiz (o mesmo
  // usado por `tsc -b` no build de produção).
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
  },
});
