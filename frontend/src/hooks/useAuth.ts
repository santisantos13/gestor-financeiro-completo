import { useContext } from "react";
import { AuthContext, type AuthContextValue } from "../contexts/AuthContext";

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth precisa ser usado dentro de um AuthProvider.");
  }
  return context;
}
