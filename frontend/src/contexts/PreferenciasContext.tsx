import { createContext, useCallback, useState, type ReactNode } from "react";
import {
  FORMATO_DATA_PADRAO,
  getFormatoData,
  setFormatoData as gravarFormatoData,
  type FormatoData,
} from "../lib/preferencesStore";

export interface PreferenciasContextValue {
  formatoData: FormatoData;
  /** Grava a preferência (store + localStorage) e recarrega a página - ver
   * docstring de `lib/preferencesStore.ts` sobre por que a mudança não é
   * instantaneamente reativa como o tema (`formatDate`/`formatDateTime` são
   * chamados como função pura por dezenas de componentes, não um hook). */
  setFormatoData: (formato: FormatoData) => void;
}

export const PreferenciasContext = createContext<PreferenciasContextValue | null>(null);

/**
 * Configurações → Preferências (moeda deliberadamente FORA - pedido
 * explícito do usuário para evitar um seletor de símbolo que pareça
 * converter valor de verdade sem converter nada, ver
 * docs/analise-arquitetural-configuracoes.md). Só "Formato de data" por
 * enquanto; Tema continua 100% em `ThemeContext` (não duplicado aqui).
 */
export function PreferenciasProvider({ children }: { children: ReactNode }) {
  const [formatoData, setFormatoDataState] = useState<FormatoData>(() => getFormatoData() ?? FORMATO_DATA_PADRAO);

  const setFormatoData = useCallback((formato: FormatoData) => {
    gravarFormatoData(formato);
    setFormatoDataState(formato);
    window.location.reload();
  }, []);

  return (
    <PreferenciasContext.Provider value={{ formatoData, setFormatoData }}>{children}</PreferenciasContext.Provider>
  );
}
