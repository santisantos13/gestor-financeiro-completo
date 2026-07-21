import { createContext, useCallback, useEffect, useState, type ReactNode } from "react";

export type Theme = "dark" | "light";

const STORAGE_KEY = "financas:tema";

export interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

function lerTemaSalvo(): Theme {
  if (typeof window === "undefined") return "dark";
  try {
    const salvo = window.localStorage.getItem(STORAGE_KEY);
    return salvo === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

/**
 * Tema claro/escuro — Etapa de Refinamento Visual. `docs/design-system.md`
 * (seção 0) já deixou a aplicação dark-only "sem fechar a porta" a um tema
 * claro no futuro (tokens como variável CSS desde o início); este
 * `ThemeProvider` é essa porta sendo aberta, a pedido explícito do
 * usuário. Padrão dark permanece o default (mesma decisão original) para
 * quem nunca escolheu nada.
 *
 * Persistência em `localStorage` (chave `financas:tema`) + um script
 * síncrono em `index.html` que já aplica o `data-theme` salvo antes do
 * React montar (evita flash do tema errado). Este Provider é só quem
 * mantém o estado React reativo depois disso e escreve `data-theme` de
 * volta no `<html>` a cada mudança.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(lerTemaSalvo);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // localStorage indisponível (modo privado restrito etc.) — o tema
      // ainda funciona nesta sessão, só não persiste entre visitas.
    }
  }, [theme]);

  const setTheme = useCallback((novoTema: Theme) => setThemeState(novoTema), []);

  const toggleTheme = useCallback(() => {
    setThemeState((atual) => (atual === "dark" ? "light" : "dark"));
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>{children}</ThemeContext.Provider>
  );
}
