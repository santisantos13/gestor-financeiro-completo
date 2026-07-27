/**
 * Wrappers de `useMutation` para `/relatorios/*` - modelados como mutation
 * (não `useQuery`) mesmo sendo `GET` no backend: o resultado nunca é
 * cacheado/exibido em tela, é um efeito colateral único (baixar um
 * arquivo) toda vez que o botão é clicado, mesmo raciocínio de outras
 * "ações" do projeto (`useExcluirFaturasEmLote`). Cada hook só busca o
 * arquivo - quem chama decide o que fazer com o resultado (a página
 * dispara `baixarBlob` e mostra o toast de erro, mesmo padrão de
 * `AlertaFormDialog`/`TagFormDialog`: hook fino, componente decide o
 * feedback).
 */
import { useMutation } from "@tanstack/react-query";
import { relatorioService } from "../services/relatorioService";

export function useBaixarRelatorioCsv() {
  return useMutation({
    mutationFn: ({ ano, mes }: { ano?: number; mes?: number }) => relatorioService.baixarCsv(ano, mes),
  });
}

export function useBaixarRelatorioPdf() {
  return useMutation({
    mutationFn: ({ ano, mes }: { ano?: number; mes?: number }) => relatorioService.baixarPdf(ano, mes),
  });
}
