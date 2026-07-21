import { useContext } from "react";
import { NavOrderContext, type NavOrderContextValue } from "../contexts/NavOrderContext";

export type { NavOrderContextValue };

export function useNavOrder(): NavOrderContextValue {
  const context = useContext(NavOrderContext);
  if (!context) {
    throw new Error("useNavOrder precisa ser usado dentro de um NavOrderProvider.");
  }
  return context;
}
