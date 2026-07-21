import { Outlet } from "react-router-dom";
import { motion } from "motion/react";
import { DURATION, EASE } from "../lib/motion";

/** Casca de rota pública (login/registro) - card centralizado, sem
 * navegação. Ver docs/analise-arquitetural-frontend.md, seção 3. Visual
 * formalizado na Etapa F2 (design-system.md). */
export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.slow, ease: EASE.out }}
        className="w-full max-w-sm rounded-lg border border-border bg-surface-1 p-8 shadow-md"
      >
        <h1 className="mb-6 text-center text-h2 font-semibold text-text-primary">
          Finanças Pessoais
        </h1>
        <Outlet />
      </motion.div>
    </div>
  );
}
