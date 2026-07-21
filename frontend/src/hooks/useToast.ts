import { useContext } from "react";
import { ToastContext } from "../contexts/ToastContext";

export interface ToastHelpers {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

export function useToast(): ToastHelpers {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast precisa ser usado dentro de um ToastProvider.");
  }
  return {
    success: (message: string) => context.showToast("success", message),
    error: (message: string) => context.showToast("error", message),
    info: (message: string) => context.showToast("info", message),
  };
}
