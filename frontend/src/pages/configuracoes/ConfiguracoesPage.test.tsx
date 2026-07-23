/**
 * Fluxo de Configurações → Perfil (docs/analise-arquitetural-testes-frontend.md,
 * mesmo padrão de LoginPage.test.tsx). Diferente de LoginPage, aqui o app
 * precisa nascer JÁ AUTENTICADO - por isso o refresh token é semeado em
 * `localStorage` antes de renderizar e `authService.refresh`/`me` são
 * mockados para resolver com sucesso (mesmo boot que `AuthContext` faz de
 * verdade quando a página é recarregada com uma sessão válida).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/renderWithProviders";
import { ConfiguracoesPage } from "./ConfiguracoesPage";
import { authService } from "../../services/authService";
import { REFRESH_TOKEN_STORAGE_KEY } from "../../api/tokenStore";

vi.mock("../../services/authService", () => ({
  authService: {
    login: vi.fn(),
    me: vi.fn(),
    refresh: vi.fn(),
    registrar: vi.fn(),
    logout: vi.fn(),
    logoutTodas: vi.fn(),
    atualizarPerfil: vi.fn(),
    trocarSenha: vi.fn(),
  },
}));

const USUARIO_INICIAL = {
  id: 1,
  nome: "Sant",
  email: "sant@example.com",
  papel: "USER" as const,
  ativo: true,
  criado_em: "2026-01-01T00:00:00",
};

function renderConfiguracoes() {
  return renderWithProviders(<ConfiguracoesPage />, { initialEntries: ["/configuracoes"] });
}

describe("ConfiguracoesPage", () => {
  beforeEach(() => {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, "refresh-token-valido");
    vi.mocked(authService.refresh).mockResolvedValue({
      access_token: "access-token",
      refresh_token: "refresh-token-valido",
      token_type: "bearer",
      expira_em_segundos: 900,
    });
    vi.mocked(authService.me).mockResolvedValue(USUARIO_INICIAL);
    vi.mocked(authService.atualizarPerfil).mockReset();
    vi.mocked(authService.trocarSenha).mockReset();
  });

  it("pré-preenche nome e email do usuário autenticado", async () => {
    renderConfiguracoes();

    expect(await screen.findByDisplayValue("Sant")).toBe(screen.getByLabelText("Nome"));
    expect(screen.getByLabelText("Email")).toHaveValue("sant@example.com");
  });

  it("salva alterações de perfil com sucesso", async () => {
    vi.mocked(authService.atualizarPerfil).mockResolvedValueOnce({
      ...USUARIO_INICIAL,
      nome: "Santiago",
    });
    const user = userEvent.setup();
    renderConfiguracoes();

    // espera o preenchimento assíncrono (useEffect após `usuario` resolver) -
    // o campo já existe no DOM desde o primeiro render (vazio), então só
    // `findByLabelText` não é suficiente: ele resolveria antes do reset()
    // acontecer, e uma interação do teste correria com o próprio reset().
    await screen.findByDisplayValue("Sant");
    await user.clear(screen.getByLabelText("Nome"));
    await user.type(screen.getByLabelText("Nome"), "Santiago");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByText("Perfil atualizado.")).toBeInTheDocument();
    expect(vi.mocked(authService.atualizarPerfil).mock.calls[0][0]).toEqual({
      nome: "Santiago",
      email: "sant@example.com",
    });
  });

  it("mapeia erro 409 de e-mail duplicado para o campo email", async () => {
    vi.mocked(authService.atualizarPerfil).mockRejectedValueOnce({
      status: 409,
      detail: "Já existe um usuário cadastrado com este e-mail.",
    });
    const user = userEvent.setup();
    renderConfiguracoes();

    // espera o preenchimento assíncrono (useEffect após `usuario` resolver) -
    // o campo já existe no DOM desde o primeiro render (vazio), então só
    // `findByLabelText` não é suficiente: ele resolveria antes do reset()
    // acontecer, e uma interação do teste correria com o próprio reset().
    await screen.findByDisplayValue("Sant");
    await user.clear(screen.getByLabelText("Email"));
    await user.type(screen.getByLabelText("Email"), "outro@example.com");
    await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Já existe um usuário cadastrado com este e-mail.");
  });

  it("rejeita troca de senha quando a confirmação não coincide, sem chamar a API", async () => {
    const user = userEvent.setup();
    renderConfiguracoes();

    // espera o preenchimento assíncrono (useEffect após `usuario` resolver) -
    // o campo já existe no DOM desde o primeiro render (vazio), então só
    // `findByLabelText` não é suficiente: ele resolveria antes do reset()
    // acontecer, e uma interação do teste correria com o próprio reset().
    await screen.findByDisplayValue("Sant");
    await user.type(screen.getByLabelText("Senha atual"), "senhaAtual123");
    await user.type(screen.getByLabelText("Senha nova"), "senhaNova123");
    await user.type(screen.getByLabelText("Confirmar senha nova"), "outraSenha456");
    await user.click(screen.getByRole("button", { name: "Alterar senha" }));

    expect(await screen.findByText("As senhas não coincidem.")).toBeInTheDocument();
    expect(authService.trocarSenha).not.toHaveBeenCalled();
  });

  it("troca a senha com sucesso e limpa os campos", async () => {
    vi.mocked(authService.trocarSenha).mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderConfiguracoes();

    // espera o preenchimento assíncrono (useEffect após `usuario` resolver) -
    // o campo já existe no DOM desde o primeiro render (vazio), então só
    // `findByLabelText` não é suficiente: ele resolveria antes do reset()
    // acontecer, e uma interação do teste correria com o próprio reset().
    await screen.findByDisplayValue("Sant");
    await user.type(screen.getByLabelText("Senha atual"), "senhaAtual123");
    await user.type(screen.getByLabelText("Senha nova"), "senhaNova123");
    await user.type(screen.getByLabelText("Confirmar senha nova"), "senhaNova123");
    await user.click(screen.getByRole("button", { name: "Alterar senha" }));

    expect(await screen.findByText("Senha alterada.")).toBeInTheDocument();
    expect(vi.mocked(authService.trocarSenha).mock.calls[0][0]).toEqual({
      senha_atual: "senhaAtual123",
      senha_nova: "senhaNova123",
    });
    expect(screen.getByLabelText("Senha atual")).toHaveValue("");
  });

  it("mapeia erro 401 de senha atual incorreta para o campo senha_atual", async () => {
    vi.mocked(authService.trocarSenha).mockRejectedValueOnce({
      status: 401,
      detail: "Senha atual incorreta.",
    });
    const user = userEvent.setup();
    renderConfiguracoes();

    // espera o preenchimento assíncrono (useEffect após `usuario` resolver) -
    // o campo já existe no DOM desde o primeiro render (vazio), então só
    // `findByLabelText` não é suficiente: ele resolveria antes do reset()
    // acontecer, e uma interação do teste correria com o próprio reset().
    await screen.findByDisplayValue("Sant");
    await user.type(screen.getByLabelText("Senha atual"), "senhaErrada1");
    await user.type(screen.getByLabelText("Senha nova"), "senhaNova123");
    await user.type(screen.getByLabelText("Confirmar senha nova"), "senhaNova123");
    await user.click(screen.getByRole("button", { name: "Alterar senha" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Senha atual incorreta.");
  });
});
