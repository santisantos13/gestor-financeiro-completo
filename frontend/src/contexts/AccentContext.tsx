import { createContext, useCallback, useEffect, useState, type ReactNode } from "react";
import { ACCENT_PADRAO, gravarAccent, lerAccentSalvo, type AccentId } from "../lib/accentThemes";

export interface AccentContextValue {
  accent: AccentId;
  setAccent: (accent: AccentId) => void;
}

export const AccentContext = createContext<AccentContextValue | null>(null);

/**
 * Cor de destaque personalizável (Configurações → Temas personalizáveis) —
 * irmão direto de `ThemeContext`, mesmo mecanismo (`localStorage` +
 * atributo no `<html>`, aqui `data-accent` em vez de `data-theme`). Reage
 * instantaneamente (sem `window.location.reload()`, diferente de
 * `PreferenciasContext.setFormatoData`): trocar `--color-accent` via CSS
 * já repinta tudo que usa a variável, não exige que nenhum componente
 * releia um valor congelado em memória (diferente do formato de data, que
 * é lido como string já formatada por dezenas de chamadas de
 * `formatDate`/`formatDateTime`).
 */
export function AccentProvider({ children }: { children: ReactNode }) {
  const [accent, setAccentState] = useState<AccentId>(lerAccentSalvo);

  useEffect(() => {
    document.documentElement.setAttribute("data-accent", accent);
    gravarAccent(accent);
  }, [accent]);

  const setAccent = useCallback((novoAccent: AccentId) => {
    setAccentState(novoAccent);
  }, []);

  return (
    <AccentContext.Provider value={{ accent: accent ?? ACCENT_PADRAO, setAccent }}>{children}</AccentContext.Provider>
  );
}
