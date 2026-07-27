import { createContext, useCallback, useEffect, useState, type ReactNode } from "react";
import {
  gravarPreferencias,
  lerPreferenciasSalvas,
  PREFERENCIAS_PADRAO,
  type PreferenciasNotificacao,
} from "../lib/notificacaoPreferencias";
import type { TipoAlerta } from "../types/alerta";

export interface NotificacaoContextValue {
  preferencias: PreferenciasNotificacao;
  /** Habilita/desabilita um `tipo` inteiro no contador do sino — nunca
   * pausa/exclui nenhum `Alerta` de verdade (ver docstring de
   * `lib/notificacaoPreferencias.ts`). */
  setPreferencia: (tipo: TipoAlerta, habilitado: boolean) => void;
}

export const NotificacaoContext = createContext<NotificacaoContextValue | null>(null);

/**
 * Preferências de Notificações (Configurações → Notificações) — irmão de
 * `AccentContext`/`ThemeContext`: `localStorage` + reatividade instantânea
 * via Context (sem `window.location.reload()`, o `Header` já re-renderiza
 * com o novo valor assim que o usuário troca uma opção).
 */
export function NotificacaoProvider({ children }: { children: ReactNode }) {
  const [preferencias, setPreferenciasState] = useState<PreferenciasNotificacao>(lerPreferenciasSalvas);

  useEffect(() => {
    gravarPreferencias(preferencias);
  }, [preferencias]);

  const setPreferencia = useCallback((tipo: TipoAlerta, habilitado: boolean) => {
    setPreferenciasState((atual) => ({ ...atual, [tipo]: habilitado }));
  }, []);

  return (
    <NotificacaoContext.Provider value={{ preferencias: preferencias ?? PREFERENCIAS_PADRAO, setPreferencia }}>
      {children}
    </NotificacaoContext.Provider>
  );
}
