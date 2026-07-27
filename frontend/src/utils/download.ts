/**
 * Dispara o download de um `Blob` já em memória (vindo de
 * `httpClient.baixarArquivo`) no navegador - único lugar do frontend que
 * cria um link `<a download>` temporário, para Relatórios (CSV/PDF) nunca
 * duplicar esse mecanismo se ganhar um terceiro formato de export no
 * futuro.
 */
export function baixarBlob(blob: Blob, nomeArquivo: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
