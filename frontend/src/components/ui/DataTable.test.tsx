/**
 * Fluxo crítico de tabela (docs/analise-arquitetural-testes-frontend.md) —
 * `DataTable` isolado, sem nenhum mock: `data` é uma prop estática, então
 * busca/ordenação/paginação rodam 100% em memória. Sem `renderWithProviders`
 * de propósito (nenhum dos 3 alvos originais precisa de Router/Auth/Toast;
 * `DataTable` também não).
 *
 * Nota importante: como o Vitest não carrega o CSS do Tailwind, as classes
 * `hidden md:block` (tabela desktop) e `md:hidden` (lista de cards mobile)
 * não escondem nada de verdade no jsdom — as duas "visões" ficam no DOM ao
 * mesmo tempo. Por isso todo teste aqui escopa as buscas em
 * `within(screen.getByRole("table"))`, que só existe na visão desktop.
 */
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable } from "./DataTable";
import type { ColumnDef } from "../../types/table";

interface Item {
  id: number;
  nome: string;
  valor: number;
}

const columns: ColumnDef<Item>[] = [
  { key: "nome", header: "Nome", accessor: (row) => row.nome, sortable: true },
  { key: "valor", header: "Valor", accessor: (row) => row.valor, sortable: true, align: "right" },
];

const data: Item[] = [
  { id: 1, nome: "Banana", valor: 30 },
  { id: 2, nome: "Maçã", valor: 10 },
  { id: 3, nome: "Uva", valor: 20 },
];

function nomesNaOrdemDaTabela(): string[] {
  const table = screen.getByRole("table");
  const linhas = within(table).getAllByRole("row").slice(1); // pula o cabeçalho
  return linhas.map((linha) => within(linha).getAllByRole("cell")[0].textContent ?? "");
}

describe("DataTable", () => {
  it("filtra as linhas pela busca textual", async () => {
    const user = userEvent.setup();
    render(<DataTable data={data} columns={columns} getRowId={(row) => row.id} searchable />);

    const table = screen.getByRole("table");
    expect(within(table).getByText("Banana")).toBeInTheDocument();
    expect(within(table).getByText("Maçã")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: "Buscar..." }), "ban");

    expect(within(table).getByText("Banana")).toBeInTheDocument();
    expect(within(table).queryByText("Maçã")).not.toBeInTheDocument();
    expect(within(table).queryByText("Uva")).not.toBeInTheDocument();
  });

  it("ordena por coluna numérica ao clicar no cabeçalho, alternando asc/desc/nenhum", async () => {
    const user = userEvent.setup();
    render(<DataTable data={data} columns={columns} getRowId={(row) => row.id} />);

    // Sem ordenação: nasce na ordem de `data`.
    expect(nomesNaOrdemDaTabela()).toEqual(["Banana", "Maçã", "Uva"]);

    await user.click(screen.getByRole("button", { name: "Valor" }));
    expect(nomesNaOrdemDaTabela()).toEqual(["Maçã", "Uva", "Banana"]); // asc: 10, 20, 30

    await user.click(screen.getByRole("button", { name: "Valor" }));
    expect(nomesNaOrdemDaTabela()).toEqual(["Banana", "Uva", "Maçã"]); // desc: 30, 20, 10

    await user.click(screen.getByRole("button", { name: "Valor" }));
    expect(nomesNaOrdemDaTabela()).toEqual(["Banana", "Maçã", "Uva"]); // volta à ordem original
  });

  it("pagina os resultados client-side", async () => {
    const user = userEvent.setup();
    render(<DataTable data={data} columns={columns} getRowId={(row) => row.id} pageSize={2} />);

    expect(nomesNaOrdemDaTabela()).toEqual(["Banana", "Maçã"]);
    expect(screen.getByText(/Mostrando/)).toHaveTextContent("Mostrando 1–2 de 3");

    await user.click(screen.getByRole("button", { name: "Próxima página" }));

    expect(nomesNaOrdemDaTabela()).toEqual(["Uva"]);
    expect(screen.getByText(/Mostrando/)).toHaveTextContent("Mostrando 3–3 de 3");
    expect(screen.getByRole("button", { name: "Próxima página" })).toBeDisabled();
  });
});
