/**
 * Fluxo crítico de formulário (docs/analise-arquitetural-testes-frontend.md)
 * — `TagFormDialog` escolhido por ser o schema mais simples do projeto
 * (`nome`/`cor`, sem `CategorySelect`/`IconPicker`/hierarquia). Mocka
 * `tagService` (a camada que `useCriarTag`/`useAtualizarTag` de fato
 * chamam), nunca `httpClient`.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { TagFormDialog } from "./TagFormDialog";
import { tagService } from "../../../services/tagService";

vi.mock("../../../services/tagService", () => ({
  tagService: {
    listar: vi.fn().mockResolvedValue([]),
    obter: vi.fn(),
    criar: vi.fn(),
    atualizar: vi.fn(),
    desativar: vi.fn(),
    obterUso: vi.fn(),
    excluirPermanente: vi.fn(),
  },
}));

describe("TagFormDialog", () => {
  beforeEach(() => {
    vi.mocked(tagService.criar).mockReset();
  });

  it("mostra erro de validação e não chama a API quando o nome está vazio", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TagFormDialog open tag={null} onClose={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Criar tag" }));

    expect(await screen.findByText("Informe o nome da tag.")).toBeInTheDocument();
    expect(tagService.criar).not.toHaveBeenCalled();
  });

  it("cria a tag com sucesso e fecha o diálogo", async () => {
    vi.mocked(tagService.criar).mockResolvedValueOnce({
      id: 1,
      nome: "viagem-2026",
      cor: null,
      ativo: true,
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<TagFormDialog open tag={null} onClose={onClose} />);

    await user.type(screen.getByLabelText("Nome"), "viagem-2026");
    await user.click(screen.getByRole("button", { name: "Criar tag" }));

    await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(vi.mocked(tagService.criar).mock.calls[0][0]).toEqual({
      nome: "viagem-2026",
      cor: null,
    });
  });

  it("mapeia erro 422 da API para o campo correspondente", async () => {
    vi.mocked(tagService.criar).mockRejectedValueOnce({
      status: 422,
      detail: [{ loc: ["body", "nome"], msg: "Já existe uma tag com esse nome.", type: "value_error" }],
    });
    const user = userEvent.setup();
    renderWithProviders(<TagFormDialog open tag={null} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "duplicada");
    await user.click(screen.getByRole("button", { name: "Criar tag" }));

    // `findByText` bate tanto no erro do campo quanto no toast que o
    // `ToastProvider` também dispara para o mesmo erro (`role="status"`) -
    // o erro do campo é o `role="alert"` de `FormError` (ver `ui/FormError.tsx`).
    expect(await screen.findByRole("alert")).toHaveTextContent("Já existe uma tag com esse nome.");
  });
});
