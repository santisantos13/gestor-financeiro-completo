/**
 * Fluxo crítico de autenticação (docs/analise-arquitetural-testes-frontend.md).
 * Mocka `authService` (não `fetch`/`httpClient`) - isola exatamente a camada
 * que `AuthContext` consome, sem precisar simular `Response` do FastAPI.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { renderWithProviders } from "../../test/renderWithProviders";
import { LoginPage } from "./LoginPage";
import { authService } from "../../services/authService";

vi.mock("../../services/authService", () => ({
  authService: {
    login: vi.fn(),
    // Resolvido por padrão (não `vi.fn()` puro): depois de um login bem
    // sucedido, `AuthContext` habilita `meQuery` automaticamente - sem
    // isso a query ficaria pendurada esperando uma Promise que nunca
    // resolve, gerando ruído/erro não tratado nos testes que logam com
    // sucesso.
    me: vi.fn().mockResolvedValue({
      id: 1,
      nome: "Sant",
      email: "sant@example.com",
      papel: "USER",
      ativo: true,
      criado_em: "2026-01-01T00:00:00",
    }),
    refresh: vi.fn(),
    registrar: vi.fn(),
    logout: vi.fn(),
    logoutTodas: vi.fn(),
  },
}));

/** `AuthContext` faz uma chamada de boot a `authService.refresh` só quando
 * existe um refresh token salvo em `localStorage` - em jsdom começa sempre
 * vazio, então nenhum mock de `refresh`/`me` é necessário para estes
 * cenários (o app já nasce "unauthenticated" e mostra a LoginPage). */
function renderLoginPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<p>Home (autenticado)</p>} />
      <Route path="/login" element={<LoginPage />} />
    </Routes>,
    { initialEntries: ["/login"] },
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.mocked(authService.login).mockReset();
  });

  it("mostra erro de validação quando os campos estão vazios, sem chamar login", async () => {
    const user = userEvent.setup();
    renderLoginPage();

    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Informe o email.")).toBeInTheDocument();
    expect(screen.getByText("Informe a senha.")).toBeInTheDocument();
    expect(authService.login).not.toHaveBeenCalled();
  });

  it("mostra erro de credencial inválida devolvido pela API", async () => {
    vi.mocked(authService.login).mockRejectedValueOnce({
      status: 401,
      detail: "Email ou senha incorretos.",
    });
    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "sant@example.com");
    await user.type(screen.getByLabelText("Senha"), "senha-errada");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email ou senha incorretos.");
  });

  it("navega para a Home ao logar com sucesso", async () => {
    vi.mocked(authService.login).mockResolvedValueOnce({
      access_token: "token-acesso",
      refresh_token: "token-refresh",
      token_type: "bearer",
      expira_em_segundos: 900,
    });
    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText("Email"), "sant@example.com");
    await user.type(screen.getByLabelText("Senha"), "senha-correta");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Home (autenticado)")).toBeInTheDocument();
    // Só o 1º argumento importa aqui - o React Query passa um 2º argumento
    // de contexto próprio (`{ client, meta, mutationKey }`) para toda
    // `mutationFn`, que não é parte do contrato de `authService.login`.
    expect(vi.mocked(authService.login).mock.calls[0][0]).toEqual({
      email: "sant@example.com",
      senha: "senha-correta",
    });
  });
});
