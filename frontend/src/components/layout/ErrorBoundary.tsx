import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "../ui/Button";

export interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Rede de segurança de topo — Estabilização de Overlays, 2ª rodada. O
 * projeto nunca teve nenhum `ErrorBoundary`: qualquer exceção não tratada
 * em QUALQUER render (o loop infinito de `useFloatingPanel` corrigido
 * nesta mesma etapa é um exemplo real que já aconteceu) derrubava a árvore
 * React inteira sem nenhuma chance de recuperação — a pessoa via a tela
 * inteira em branco/preta, sem nenhuma mensagem, precisando adivinhar que
 * era preciso recarregar a página.
 *
 * Só React Error Boundaries (`componentDidCatch`/`getDerivedStateFromError`
 * — mecanismo de classe, não existe equivalente em hooks) capturam esse
 * tipo de erro de render; um `try/catch` comum não pega nada aqui. Este
 * componente não previne bugs (a causa raiz de cada um continua precisando
 * ser corrigida como sempre), só garante que um bug futuro qualquer nunca
 * mais quebre a aplicação inteira sem explicação — sempre uma tela com
 * mensagem + ação de recarregar, nunca um branco silencioso.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Erro não tratado capturado pelo ErrorBoundary:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex min-h-screen items-center justify-center bg-bg p-6">
        <div className="flex max-w-sm flex-col items-center gap-3 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-negative-subtle">
            <AlertTriangle size={22} className="text-negative" aria-hidden="true" />
          </span>
          <h1 className="text-h3 font-semibold text-text-primary">Algo deu errado</h1>
          <p className="text-sm text-text-secondary">
            Encontramos um erro inesperado nesta tela. Recarregar a página normalmente resolve — nenhum dado
            é perdido, tudo continua salvo no servidor.
          </p>
          <Button size="sm" onClick={() => window.location.reload()}>
            <RotateCcw size={14} aria-hidden="true" />
            Recarregar página
          </Button>
        </div>
      </div>
    );
  }
}
