/**
 * Constantes de motion reutilizáveis em todo o projeto — espelham os
 * tokens canônicos de `docs/motion-principles.md` (seção 4). `motion`
 * (Framer Motion) não lê variáveis CSS em `transition={{ ... }}` (precisa
 * de número), então os valores de duração/curva/spring são duplicados
 * aqui como constantes TypeScript; `src/index.css` tem a versão CSS dos
 * mesmos valores para uso em transições Tailwind/CSS puras. Se um valor
 * mudar, muda nos dois lugares — nenhum outro arquivo deve declarar um
 * spring/duration/curva novo sem passar por `docs/motion-principles.md`
 * primeiro (seção 11 do documento).
 */

// ---- 4.1 Durações (em segundos, unidade que `motion` espera) ----
export const DURATION = {
  instant: 0.1,
  fast: 0.15,
  base: 0.2,
  moderate: 0.3,
  slow: 0.45,
} as const;

// ---- 4.2 Curvas ----
export const EASE = {
  out: [0.16, 1, 0.3, 1],
  in: [0.7, 0, 0.84, 0],
  inOut: [0.65, 0, 0.35, 1],
} as const;

// ---- 4.3 Springs ----
export const SPRING = {
  snappy: { type: "spring", stiffness: 500, damping: 30 },
  smooth: { type: "spring", stiffness: 300, damping: 30 },
  gentle: { type: "spring", stiffness: 200, damping: 26 },
} as const;

// ---- 5.1 Padrão de entrada/saída genérico (mount/unmount) ----
// Deslocamento pequeno (4-8px) na direção de onde o elemento "vem" —
// motion-principles.md, seção 5.1. `offset` é sobrescrito por chamada
// quando a direção importa (ex. dropdown vem de cima do gatilho).
export function fadeIn(offset: number = 6) {
  return {
    initial: { opacity: 0, y: offset },
    animate: { opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } },
    exit: { opacity: 0, y: offset * 0.6, transition: { duration: DURATION.fast, ease: EASE.in } },
  };
}

// ---- 5.8 / 15 Modal (FormDialog/DeleteDialog) ----
export const modalBackdrop = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: DURATION.moderate, ease: EASE.out } },
  exit: { opacity: 0, transition: { duration: DURATION.fast, ease: EASE.in } },
};

export const modalPanel = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: SPRING.smooth },
  exit: { opacity: 0, scale: 0.97, transition: { duration: DURATION.fast, ease: EASE.in } },
};

// ---- Drawer (docs/analise-arquitetural-overlays.md, seção 4.5) ----
// Mesmo backdrop do modal (só a superfície muda de centralizada para
// ancorada à borda) — reaproveita `modalBackdrop`, nenhum timing novo.
export const drawerBackdrop = modalBackdrop;

export const drawerPanel = {
  initial: { opacity: 0, x: "100%" },
  animate: { opacity: 1, x: 0, transition: SPRING.smooth },
  // Saída ~70% da duração de entrada, --ease-in (motion-principles.md, 5.1).
  exit: { opacity: 0, x: "100%", transition: { duration: DURATION.moderate * 0.7, ease: EASE.in } },
};

// ---- 5.7 Toast ----
export const toastVariants = {
  initial: { opacity: 0, y: 16, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1, transition: SPRING.smooth },
  exit: { opacity: 0, scale: 0.98, transition: { duration: DURATION.fast, ease: EASE.in } },
};
