/**
 * Fluxo de listagem/pausar/excluir de Alerta — complementa
 * `AlertaFormDialog.test.tsx` (que cobre criar/editar). Mocka
 * `alertaService` e os 4 services de listagem usados para resolver o nome
 * da entidade (`nomeDaEntidade`, ver docstring de `AlertasDrawer.tsx`).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { AlertasDrawer } from "./AlertasDrawer";
import { alertaService } from "../../../services/alertaService";
import type { AlertaRead } from "../../../types/alerta";

vi.mock("../../../services/cartaoService", () => ({
  cartaoService: { listar: vi.fn().mockResolvedValue([]) },
}));
vi.mock("../../../services/contaService", () => ({
  contaService: {
    listar: vi.fn().mockResolvedValue([
      { id: 3, nome: "Conta Corrente", tipo: "CORRENTE", saldo_inicial: "0.00", saldo_atual: "50.00", instituicao: null, ativo: true },
    ]),
  },
}));
vi.mock("../../../services/metaService", () => ({
  metaService: { listar: vi.fn().mockResolvedValue([]) },
}));
vi.mock("../../../services/contaRecorrenteService", () => ({
  contaRecorrenteService: { listar: vi.fn().mockResolvedValue([]) },
}));
vi.mock("../../../services/alertaService", () => ({
  alertaService: {
    listar: vi.fn(),
    obter: vi.fn(),
    criar: vi.fn(),
    atualizar: vi.fn(),
    excluir: vi.fn(),
  },
}));

const ALERTA_SALDO_BAIXO: AlertaRead = {
  id: 9,
  tipo: "SALDO_BAIXO",
  entidade_id: 3,
  condicao: { valor_minimo: 100 },
  ativo: true,
  ultima_disparada_em: "2026-07-26T09:00:00",
  criado_em: "2026-07-01T09:00:00",
  disparado: true,
  mensagem: 'Conta "Conta Corrente" está com saldo baixo: R$ 50.00 (mínimo configurado: R$ 100.00).',
};

describe("AlertasDrawer", () => {
  beforeEach(() => {
    vi.mocked(alertaService.listar).mockReset();
    // Default persistente para o refetch que a invalidação de cache dispara
    // após pausar/excluir - `mockResolvedValueOnce` abaixo, em cada teste,
    // só cobre a carga INICIAL da lista.
    vi.mocked(alertaService.listar).mockResolvedValue([]);
    vi.mocked(alertaService.atualizar).mockReset();
    vi.mocked(alertaService.excluir).mockReset();
  });

  it("mostra a mensagem já pronta do backend para um alerta disparado", async () => {
    vi.mocked(alertaService.listar).mockResolvedValueOnce([ALERTA_SALDO_BAIXO]);
    renderWithProviders(<AlertasDrawer open onClose={vi.fn()} />);

    expect(await screen.findByText(/está com saldo baixo/)).toBeInTheDocument();
  });

  it("pausa um alerta ativo via PATCH { ativo: false }", async () => {
    vi.mocked(alertaService.listar).mockResolvedValueOnce([ALERTA_SALDO_BAIXO]);
    vi.mocked(alertaService.atualizar).mockResolvedValueOnce({ ...ALERTA_SALDO_BAIXO, ativo: false, disparado: null, mensagem: null });
    const user = userEvent.setup();
    renderWithProviders(<AlertasDrawer open onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Pausar alerta" }));

    await vi.waitFor(() => expect(alertaService.atualizar).toHaveBeenCalledWith(9, { ativo: false }));
  });

  it("exclui um alerta após confirmação", async () => {
    vi.mocked(alertaService.listar).mockResolvedValueOnce([ALERTA_SALDO_BAIXO]);
    vi.mocked(alertaService.excluir).mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderWithProviders(<AlertasDrawer open onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Excluir alerta" }));
    await user.click(await screen.findByRole("button", { name: "Excluir" }));

    await vi.waitFor(() => expect(alertaService.excluir).toHaveBeenCalledWith(9));
  });
});
