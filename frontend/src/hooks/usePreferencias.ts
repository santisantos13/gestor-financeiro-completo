import { useContext } from "react";
import { PreferenciasContext, type PreferenciasContextValue } from "../contexts/PreferenciasContext";

export function usePreferencias(): PreferenciasContextValue {
  const context = useContext(PreferenciasContext);
  if (!context) {
    throw new Error("usePreferencias precisa ser usado dentro de um PreferenciasProvider.");
  }
  return context;
}
