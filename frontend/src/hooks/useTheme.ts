import { useContext } from "react";
import { ThemeContext, type Theme, type ThemeContextValue } from "../contexts/ThemeContext";

export type { Theme, ThemeContextValue };

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme precisa ser usado dentro de um ThemeProvider.");
  }
  return context;
}
