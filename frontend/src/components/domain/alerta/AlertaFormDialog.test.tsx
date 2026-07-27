/**
 * Fluxo de criação de Alerta (`docs/analise-arquitetural-testes-frontend.md`)
 * — cobre o caminho mais representativo (LIMITE_CARTAO, o único tipo com
 * um picker de entidade + um campo de condição numérico), mais a
 * imutabilidade de `tipo`/`entidade_id` em modo edição. Mocka
 * `alertaService` (a camada que `useCriarAlerta`/`useAtualizarAlerta`
 * chamam) e os 4 services de listagem que alimentam o picker de entidade
 * (`cartaoService`/`contaService`/`metaService`/`contaRecorrenteService`) —
 * nunca `httpClient`.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { AlertaFormDialog } from "./AlertaFormDialog";
import { alertaService } from "../../../services/alertaService";
import { cartaoService } from "../../../services/cartaoService";
import { contaService } from "../../../services/contaService";
import { metaService } from "../../../services/metaService";
import { contaRecorrenteService } from "../../../services/contaRecorrenteService";

vi.mock("../../../services/alertaService", () => ({
  alertaService: {
    listar: vi.fn().mockResolvedValue([]),
    obter: vi.fn(),
    criar: vi.fn(),
    atualizar: vi.fn(),
    excluir: vi.fn(),
  },
}));
vi.mock("../../../services/cartaoService", () => ({
  cartaoService: {
    listar: vi.fn().mockResolvedValue([
      {
        id: 7,
        nome: "Nubank",
        conta_pagamento_id: 1,
        instituicao: "Nubank",
        bandeira: "MASTERCARD",
        ultimos_quatro_digitos: "1234",
        limite: "1000.00",
        limite_disponivel: "1000.00",
        dia_fechamento: 5,
        dia_vencimento: 12,
        ativo: true,
        saldo_inicial_utilizado: "0.00",
      },
    ]),
  },
}));
vi.mock("../../../services/contaService", () => ({
  contaService: {
    listar: vi.fn().mockResolvedValue([]),
  },
}));
vi.mock("../../../services/metaService", () => ({
  metaService: {
    listar: vi.fn().mockResolvedValue([]),
  },
}));
vi.mock("../../../services/contaRecorrenteService", () => ({
  contaRecorrenteService: {
    listar: vi.fn().mockResolvedValue([]),
  },
}));

describe("AlertaFormDialog", () => {
  beforeEach(() => {
    vi.mocked(alertaService.criar).mockReset();
    vi.mocked(alertaService.atualizar).mockReset();
  });

  it("cria um alerta de LIMITE_CARTAO com sucesso e fecha o diálogo", async () => {
    vi.mocked(alertaService.criar).mockResolvedValueOnce({
      id: 1,
      tipo: "LIMITE_CARTAO",
      entidade_id: 7,
      condicao: { limite_percentual: 90 },
      ativo: true,
      ultima_disparada_em: null,
      criado_em: "2026-07-26T10:00:00",
      disparado: false,
      mensagem: null,
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<AlertaFormDialog open alerta={null} onClose={onClose} />);

    // O tipo padrão já é LIMITE_CARTAO - só falta escolher o cartão e o
    // percentual.
    await user.click(await screen.findByRole("combobox", { name: "Cartão" }));
    await user.click(await screen.findByRole("option", { name: "Nubank" }));
    await user.type(screen.getByLabelText("Avisar ao atingir (% do limite)"), "9000");

    await user.click(screen.getByRole("button", { name: "Criar alerta" }));

    await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(vi.mocked(alertaService.criar).mock.calls[0][0]).toEqual({
      tipo: "LIMITE_CARTAO",
      entidade_id: 7,
      condicao: { limite_percentual: 90 },
    });
  });

  it("mostra erro de validação e não chama a API quando nenhum cartão é selecionado", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AlertaFormDialog open alerta={null} onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "Criar alerta" }));

    expect(await screen.findByText("Selecione o item que este alerta vai monitorar.")).toBeInTheDocument();
    expect(alertaService.criar).not.toHaveBeenCalled();
  });

  it("em modo edição, tipo e item monitorado ficam desabilitados - só a condição é editável", async () => {
    vi.mocked(alertaService.atualizar).mockResolvedValueOnce({
      id: 1,
      tipo: "LIMITE_CARTAO",
      entidade_id: 7,
      condicao: { limite_percentual: 80 },
      ativo: true,
      ultima_disparada_em: null,
      criado_em: "2026-07-26T10:00:00",
      disparado: false,
      mensagem: null,
    });
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <AlertaFormDialog
        open
        alerta={{
          id: 1,
          tipo: "LIMITE_CARTAO",
          entidade_id: 7,
          condicao: { limite_percentual: 90 },
          ativo: true,
          ultima_disparada_em: null,
          criado_em: "2026-07-26T10:00:00",
          disparado: false,
          mensagem: null,
        }}
        onClose={onClose}
      />,
    );

    expect(await screen.findByRole("combobox", { name: "Tipo de alerta" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Cartão" })).toBeDisabled();

    const campoPercentual = screen.getByLabelText("Avisar ao atingir (% do limite)") as HTMLInputElement;
    await user.clear(campoPercentual);
    await user.type(campoPercentual, "8000");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(vi.mocked(alertaService.atualizar).mock.calls[0]).toEqual([1, { condicao: { limite_percentual: 80 } }]);
  });
});
