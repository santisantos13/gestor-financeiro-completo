import { forwardRef, type ButtonHTMLAttributes } from "react";
import { motion } from "motion/react";
import { DURATION, EASE, SPRING } from "../../lib/motion";
import { Spinner } from "./Spinner";

// `motion.button` tem seu próprio tipo para onDrag*/onAnimation* (assinatura
// de gesto do Framer Motion), incompatível com o handler nativo do DOM —
// omitidos aqui porque este componente nunca usa esses handlers nativos.
type NativeButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration"
>;

export interface ButtonProps extends NativeButtonProps {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  /** Substitui o label por um Spinner mantendo a largura do botão — nunca
   * um "pulo" de layout. design-system.md, seção 14. */
  loading?: boolean;
}

const VARIANT_CLASSES: Record<NonNullable<ButtonProps["variant"]>, string> = {
  // `hover:shadow-glow-accent` — glow discreto de acento (Etapa de
  // Refinamento Visual, motion-principles.md não define glow por não ser
  // motion de posição/opacidade, mas é a mesma filosofia de "confirmação
  // sutil de interação" das seções 1/2 daquele documento; só a variante
  // primária (a ação de maior destaque) ganha o glow.
  primary: "bg-accent text-text-onAccent hover:bg-accent-hover active:bg-accent-active hover:shadow-glow-accent",
  secondary:
    "bg-surface-2 text-text-primary border border-border hover:bg-surface-3 hover:border-border-strong active:bg-surface-3",
  ghost: "bg-transparent text-text-secondary hover:bg-surface-2 hover:text-text-primary",
  danger: "bg-negative text-text-onAccent hover:brightness-110 active:brightness-95",
};

const SIZE_CLASSES: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "h-7 px-3 text-sm gap-1.5",
  md: "h-9 px-4 text-body gap-2",
  lg: "h-11 px-5 text-body gap-2",
};

const SPINNER_SIZE: Record<NonNullable<ButtonProps["size"]>, "sm" | "md"> = {
  sm: "sm",
  md: "sm",
  lg: "md",
};

/**
 * Botão base do Design System — design-system.md, seção 14. `loading`
 * formaliza o `LoadingButton` citado na seção 15 (não é um componente
 * separado: a própria seção 15 aponta de volta para cá).
 *
 * Hover: elevação de 1px (`whileHover`, não CSS `translate` — um
 * `motion.button` já controla `transform` para o `whileTap`; misturar com
 * uma classe Tailwind de `translate` no mesmo elemento faria os dois
 * sistemas de transform brigarem pela mesma propriedade CSS. `whileHover`
 * e `whileTap` do Framer Motion compõem corretamente entre si, então a
 * elevação de hover e o "press" de clique nunca conflitam mesmo
 * acontecendo em sequência rápida). Cor/borda/glow continuam via classe
 * Tailwind (não conflitam com `transform`).
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, disabled, className = "", children, ...props },
  ref,
) {
  const isDisabled = disabled || loading;

  return (
    <motion.button
      ref={ref}
      disabled={isDisabled}
      whileHover={isDisabled ? undefined : { y: -1, transition: { duration: DURATION.fast, ease: EASE.out } }}
      whileTap={isDisabled ? undefined : { scale: 0.98, transition: { duration: DURATION.instant, ...SPRING.snappy } }}
      className={`relative inline-flex items-center justify-center rounded-sm font-medium transition-[background-color,border-color,box-shadow,color] duration-fast ease-out disabled:cursor-not-allowed disabled:opacity-50 ${SIZE_CLASSES[size]} ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    >
      <span className={loading ? "invisible" : "inline-flex items-center gap-2"}>{children}</span>
      {loading && (
        <span className="absolute inset-0 flex items-center justify-center">
          <Spinner size={SPINNER_SIZE[size]} tone={variant === "primary" || variant === "danger" ? "onAccent" : "accent"} />
        </span>
      )}
    </motion.button>
  );
});
