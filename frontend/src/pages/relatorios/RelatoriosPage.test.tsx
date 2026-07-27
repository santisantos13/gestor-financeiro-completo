/**
 * Fluxo de Relatórios: preview do período (mesmos dados de `/graficos`) +
 * download de CSV/PDF. Mocka `centralFinanceiraService` (preview) e
 * `relatorioService` (download) — `utils/download.baixarBlob` também é
 * mockado, já que em jsdom `URL.createObjectURL` não existe e o teste não
 * precisa validar o mecanismo de download em si, só que ele é chamado com o
 * blob/nome de arquivo devolvidos pelo service.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/renderWithProviders";
import { RelatoriosPage } from "./RelatoriosPage";
import { centralFinanceiraService } from "../../services/centralFinanceiraService";
import { relatorioService } from "../../services/relatorioService";
import { baixarBlob } from "../../utils/download";

vi.mock("../../services/centralFinanceiraService", () => ({
  centralFinanceiraService: {
    visaoMensal: vi.fn(),
    graficosPeriodo: vi.fn(),
  },
}));
vi.mock("../../services/relatorioService", () => ({
  relatorioService: {
    baixarCsv: vi.fn(),
    baixarPdf: vi.fn(),
  },
}));
vi.mock("../../utils/download", () => ({
  baixarBlob: vi.fn(),
}));

const VISAO_MENSAL = { ano: 2026, mes: 7, entradas: "5000.00", saidas: "3200.00", fluxo_caixa: "1800.00" };
const GRAFICOS_PERIODO = {
  ano: 2026,
  mes: 7,
  gastos_por_categoria: [{ categoria_id: 1, categoria_nome: "Mercado", categoria_cor: null, categoria_icone: null, total: "800.00" }],
  gastos_por_cartao: [],
  gastos_por_conta: [],
};

describe("RelatoriosPage", () => {
  beforeEach(() => {
    vi.mocked(centralFinanceiraService.visaoMensal).mockReset().mockResolvedValue(VISAO_MENSAL);
    vi.mocked(centralFinanceiraService.graficosPeriodo).mockReset().mockResolvedValue(GRAFICOS_PERIODO);
    vi.mocked(relatorioService.baixarCsv).mockReset();
    vi.mocked(relatorioService.baixarPdf).mockReset();
    vi.mocked(baixarBlob).mockReset();
  });

  it("mostra o resumo do período (entradas, saídas, saldo) vindo dos mesmos hooks de Gráficos", async () => {
    renderWithProviders(<RelatoriosPage />);

    expect(await screen.findByText("R$ 5.000,00")).toBeInTheDocument();
    expect(screen.getByText("R$ 3.200,00")).toBeInTheDocument();
    expect(screen.getByText("R$ 1.800,00")).toBeInTheDocument();
  });

  it("baixa o CSV ao clicar em 'Baixar CSV'", async () => {
    const blob = new Blob(["conteudo"]);
    vi.mocked(relatorioService.baixarCsv).mockResolvedValueOnce({ blob, nomeArquivo: "relatorio-2026-07.csv" });
    const user = userEvent.setup();
    renderWithProviders(<RelatoriosPage />);
    await screen.findByText("R$ 5.000,00");

    await user.click(screen.getByRole("button", { name: /Baixar CSV/ }));

    await vi.waitFor(() => expect(relatorioService.baixarCsv).toHaveBeenCalledWith(2026, 7));
    await vi.waitFor(() => expect(baixarBlob).toHaveBeenCalledWith(blob, "relatorio-2026-07.csv"));
  });

  it("baixa o PDF ao clicar em 'Baixar PDF'", async () => {
    const blob = new Blob(["conteudo"]);
    vi.mocked(relatorioService.baixarPdf).mockResolvedValueOnce({ blob, nomeArquivo: "relatorio-2026-07.pdf" });
    const user = userEvent.setup();
    renderWithProviders(<RelatoriosPage />);
    await screen.findByText("R$ 5.000,00");

    await user.click(screen.getByRole("button", { name: /Baixar PDF/ }));

    await vi.waitFor(() => expect(relatorioService.baixarPdf).toHaveBeenCalledWith(2026, 7));
    await vi.waitFor(() => expect(baixarBlob).toHaveBeenCalledWith(blob, "relatorio-2026-07.pdf"));
  });

  it("mostra erro sem baixar nada quando o download falha", async () => {
    vi.mocked(relatorioService.baixarCsv).mockRejectedValueOnce({ status: 500, detail: "Falha ao gerar relatório." });
    const user = userEvent.setup();
    renderWithProviders(<RelatoriosPage />);
    await screen.findByText("R$ 5.000,00");

    await user.click(screen.getByRole("button", { name: /Baixar CSV/ }));

    expect(await screen.findByText("Falha ao gerar relatório.")).toBeInTheDocument();
    expect(baixarBlob).not.toHaveBeenCalled();
  });
});
