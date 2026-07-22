/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** Injetada por `vite.config.ts` (`define`) a partir da `version` de
 * `package.json` — ver docs/versionamento.md. Usada por
 * `components/layout/Header.tsx` para exibir "Alpha {versão}". */
declare const __APP_VERSION__: string;
