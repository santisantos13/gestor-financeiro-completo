/**
 * Melhorias de Gráficos (2026-07-26): cobre as 4 peças novas mais
 * relevantes desta página - (1) total + variação vs mês anterior
 * (`ResumoGastosMes`, busca um segundo `graficosPeriodo`), (2) drill-down
 * de categoria/conta para `/transacoes` (com `categoria_id`/`conta_id` +
 * período na URL) e de cartão para `/cartoes/:id`, (3) atalho "Baixar
 * relatório" para `/relatorios?ano=&mes=`, (4) toggle "Comparar com mês
 * anterior" trocando o donut por `GastosComparativoChart`. Mocka
 * `centralFinanceiraService` (todos os 3 métodos que a página usa) -
 * "Evolução do saldo"/"Entradas x Saídas" não são o foco aqui, só precisam
 * de um retorno válido para não ficar em loading infinito.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useParams, useSearchParams } from "react-router-dom";
import { renderWithProviders } from "../../test/renderWithProviders";
import { GraficosPage } from "./GraficosPage";
import { centralFinanceiraService } from "../../services/centralFinanceiraService";

vi.mock("../../services/centralFinanceiraService", () => ({
  centralFinanceiraService: {
    graficosTendencias: vi.fn(),
    graficosPeriodo: vi.fn(),
    saldoConsolidado: vi.fn(),
  },
}));

function DestinoTransacoes() {
  const [params] = useSearchParams();
  return <p>Transações destino: {params.toString()}</p>;
}
function DestinoCartaoDetalhe() {
  const { id } = useParams();
  return <p>Cartão detalhe: {id}</p>;
}
function DestinoRelatorios() {
  const [params] = useSearchParams();
  return <p>Relatórios destino: {params.toString()}</p>;
}

function renderGraficosPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/graficos" element={<GraficosPage />} />
      <Route path="/transacoes" element={<DestinoTransacoes />} />
      <Route path="/cartoes/:id" element={<DestinoCartaoDetalhe />} />
      <Route path="/relatorios" element={<DestinoRelatorios />} />
    </Routes>,
    { initialEntries: ["/graficos"] },
  );
}

const TENDENCIAS_VAZIAS = { meses: [] };
const SALDO_CONSOLIDADO_VAZIO = { saldo_total: "0", contas: [] };

// Data do sandbox é 2026-07-26 (env) - o período inicial da página é
// sempre o mês atual, então os mocks abaixo cobrem exatamente jul/2026
// (atual) e jun/2026 (anterior, via `mesAnterior`).
const PERIODO_JULHO = {
  ano: 2026,
  mes: 7,
  gastos_por_categoria: [
    { categoria_id: 1, categoria_nome: "Mercado", categoria_cor: null, categoria_icone: null, total: "800.00" },
    { categoria_id: 2, categoria_nome: "Lazer", categoria_cor: null, categoria_icone: null, total: "200.00" },
  ],
  gastos_por_cartao: [{ cartao_id: 5, cartao_nome: "Nubank", total: "300.00" }],
  gastos_por_conta: [{ conta_id: 3, conta_nome: "Conta Corrente", total: "700.00" }],
};
const PERIODO_JUNHO = {
  ano: 2026,
  mes: 6,
  gastos_por_categoria: [
    { categoria_id: 1, categoria_nome: "Mercado", categoria_cor: null, categoria_icone: null, total: "500.00" },
  ],
  gastos_por_cartao: [],
  gastos_por_conta: [{ conta_id: 3, conta_nome: "Conta Corrente", total: "500.00" }],
};

describe("GraficosPage", () => {
  beforeEach(() => {
    vi.mocked(centralFinanceiraService.graficosTendencias).mockReset().mockResolvedValue(TENDENCIAS_VAZIAS);
    vi.mocked(centralFinanceiraService.saldoConsolidado).mockReset().mockResolvedValue(SALDO_CONSOLIDADO_VAZIO);
    vi.mocked(centralFinanceiraService.graficosPeriodo)
      .mockReset()
      .mockImplementation((ano?: number, mes?: number) =>
        Promise.resolve(mes === 6 ? PERIODO_JUNHO : PERIODO_JULHO),
      );
  });

  it("mostra o total gasto do mês com a variação vs mês anterior", async () => {
    renderGraficosPage();

    // Total de jul/2026: 800 + 200 = 1000,00 (soma de gastos_por_categoria)
    expect(await screen.findByText("R$ 1.000,00")).toBeInTheDocument();
    // Anterior (jun/2026): 500,00 - variação de +100%
    expect(await screen.findByText("100.0%")).toBeInTheDocument();
    expect(screen.getByText(/vs R\$ 500,00 no mês anterior/)).toBeInTheDocument();
  });

  it("leva para /transacoes filtrado ao clicar numa categoria", async () => {
    const user = userEvent.setup();
    renderGraficosPage();

    await user.click(await screen.findByText("Mercado"));

    const destino = await screen.findByText(/Transações destino:/);
    expect(destino.textContent).toContain("categoria_id=1");
    expect(destino.textContent).toContain("ano=2026");
    expect(destino.textContent).toContain("mes=7");
  });

  it("leva para /transacoes filtrado ao clicar numa conta", async () => {
    const user = userEvent.setup();
    renderGraficosPage();

    await user.click(await screen.findByText("Conta Corrente"));

    const destino = await screen.findByText(/Transações destino:/);
    expect(destino.textContent).toContain("conta_id=3");
  });

  it("leva para /cartoes/:id (nunca /transacoes) ao clicar num cartão", async () => {
    const user = userEvent.setup();
    renderGraficosPage();

    await user.click(await screen.findByText("Nubank"));

    expect(await screen.findByText("Cartão detalhe: 5")).toBeInTheDocument();
  });

  it("leva para /relatorios com o mês selecionado ao clicar em 'Baixar relatório'", async () => {
    const user = userEvent.setup();
    renderGraficosPage();

    await screen.findByText("R$ 1.000,00");
    await user.click(screen.getByRole("button", { name: /Baixar relatório/ }));

    const destino = await screen.findByText(/Relatórios destino:/);
    expect(destino.textContent).toContain("ano=2026");
    expect(destino.textContent).toContain("mes=7");
  });

  it("troca para a visão comparativa ao ativar 'Comparar com mês anterior'", async () => {
    const user = userEvent.setup();
    renderGraficosPage();

    await screen.findByText("R$ 1.000,00");
    await user.click(screen.getByRole("switch", { name: "Comparar com mês anterior" }));

    // GastosComparativoChart mostra a legenda com os rótulos dos 2 períodos -
    // uma vez por seção (categoria/cartão/conta), por isso `findAllByText`.
    expect(await screen.findAllByText("Julho/2026")).toHaveLength(3);
    expect(screen.getAllByText("Junho/2026")).toHaveLength(3);
  });
});
