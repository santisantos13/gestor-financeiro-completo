import { useContext } from "react";
import { NotificacaoContext, type NotificacaoContextValue } from "../contexts/NotificacaoContext";

export function useNotificacao(): NotificacaoContextValue {
  const context = useContext(NotificacaoContext);
  if (!context) {
    throw new Error("useNotificacao precisa ser usado dentro de um NotificacaoProvider.");
  }
  return context;
}
