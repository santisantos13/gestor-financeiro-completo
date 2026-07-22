/**
 * Versão exibida no Header (docs/versionamento.md) — "Alpha {APP_VERSION}".
 *
 * Histórico: as duas primeiras tentativas de obter isso automaticamente a
 * partir de `package.json` em tempo de build (via `vite.config.ts` define,
 * primeiro com `import { version } from "./package.json"`, depois com
 * `process.env.npm_package_version`) funcionavam neste ambiente de
 * desenvolvimento mas quebravam em produção no Render (`__APP_VERSION__ is
 * not defined`, app inteiro derrubado pelo ErrorBoundary) - confirmado
 * DUAS vezes com o site real, sem conseguir reproduzir a causa exata aqui
 * (sem acesso aos logs de build do Render). Depois da segunda falha, a
 * decisão foi parar de tentar injetar isso via build e usar uma constante
 * de código-fonte simples - zero dependência de como cada ambiente
 * resolve `vite.config.ts`/variáveis de ambiente de build, então não tem
 * como divergir entre este sandbox e produção.
 *
 * Custo aceito: `APP_VERSION` aqui precisa ser atualizada manualmente em
 * conjunto com o campo "version" de `package.json` a cada bump (mesmo
 * commit) - ver checklist em docs/versionamento.md.
 */
export const APP_VERSION = "0.3.2";
