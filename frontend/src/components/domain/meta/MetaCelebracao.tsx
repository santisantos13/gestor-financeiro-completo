import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { PartyPopper } from "lucide-react";
import { DURATION, EASE, SPRING } from "../../../lib/motion";

const CORES_CONFETTI = ["var(--color-accent)", "var(--color-positive)", "var(--color-info)", "var(--color-warning)"];

interface Particula {
  id: number;
  xFinal: number;
  yFinal: number;
  rotacaoFinal: number;
  atraso: number;
  cor: string;
}

function gerarParticulas(quantidade: number): Particula[] {
  return Array.from({ length: quantidade }, (_, i) => ({
    id: i,
    xFinal: (Math.random() - 0.5) * 220,
    yFinal: 70 + Math.random() * 60,
    rotacaoFinal: (Math.random() - 0.5) * 340,
    atraso: Math.random() * 0.12,
    cor: CORES_CONFETTI[i % CORES_CONFETTI.length],
  }));
}

export interface MetaCelebracaoProps {
  ativa: boolean;
}

/**
 * Celebração de conclusão de Meta — pedido explícito do usuário (Refinamento
 * de Metas, seção 4). É uma EXCEÇÃO deliberada e documentada ao princípio de
 * "confiança silenciosa" de docs/design-system.md, concedida pelo próprio
 * usuário só para este momento específico (ver
 * docs/analise-arquitetural-metas-refinamento.md, seção 4.1).
 *
 * Deliberadamente contida, conforme pedido ("não quero algo exagerado"):
 * ~14 partículas pequenas, cores só dos tokens semânticos já existentes
 * (accent/positive/info/warning — nenhuma cor nova), ~1.1s de queda e
 * ~1.6s de duração total, sem som (o pedido do usuário marcava som como
 * "opcional"; o projeto não tem nenhum asset de áudio, e adicionar um só
 * para isto contradiria "elegante e coerente com o restante do sistema").
 *
 * `ativa` é decidido inteiramente por quem usa este componente
 * (`useCelebracaoMeta`, que controla o "só uma vez" via `localStorage`) —
 * este componente só sabe COMO celebrar, nunca SE deve.
 */
export function MetaCelebracao({ ativa }: MetaCelebracaoProps) {
  const [particulas] = useState(() => gerarParticulas(14));

  return (
    <AnimatePresence>
      {ativa && (
        <motion.div
          className="pointer-events-none absolute inset-0 z-10 overflow-hidden rounded-lg"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: DURATION.slow, ease: EASE.in } }}
        >
          {particulas.map((p) => (
            <motion.span
              key={p.id}
              className="absolute left-1/2 top-1/4 h-1.5 w-1.5 rounded-sm"
              style={{ backgroundColor: p.cor }}
              initial={{ opacity: 1, x: 0, y: 0, rotate: 0 }}
              animate={{
                opacity: 0,
                x: p.xFinal,
                y: p.yFinal,
                rotate: p.rotacaoFinal,
                transition: { duration: 0.9, delay: p.atraso, ease: EASE.out },
              }}
            />
          ))}

          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1, transition: { delay: 0.05, ...SPRING.gentle } }}
            exit={{ opacity: 0, scale: 0.96, transition: { duration: DURATION.fast, ease: EASE.in } }}
          >
            <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1.5 shadow-md">
              <PartyPopper size={14} className="shrink-0 text-accent" aria-hidden="true" />
              <span className="text-caption font-medium text-text-primary">Meta concluída — parabéns!</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
