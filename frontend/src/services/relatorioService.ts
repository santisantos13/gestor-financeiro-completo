/**
 * Funções finas — um por endpoint de `/relatorios/*`. Diferente de todo
 * outro service do projeto, a resposta não é JSON: `httpClient.baixarArquivo`
 * devolve `{ blob, nomeArquivo }` (o nome real vem do `Content-Disposition`
 * do backend, ex. `relatorio-2026-07.csv`). Consumido exclusivamente por
 * `hooks/useRelatorioQueries.ts`.
 */
import { httpClient } from "../api/httpClient";

export const relatorioService = {
  baixarCsv: (ano?: number, mes?: number) =>
    httpClient.baixarArquivo("/relatorios/csv", { ano, mes }, "relatorio.csv"),

  baixarPdf: (ano?: number, mes?: number) =>
    httpClient.baixarArquivo("/relatorios/pdf", { ano, mes }, "relatorio.pdf"),
};
