/**
 * Tailwind lê os tokens de docs/design-system.md (seções 6-12) e
 * docs/motion-principles.md (seção 4) a partir das variáveis CSS definidas
 * em src/index.css (:root) — nunca um valor hardcoded aqui que não exista
 * também como var(--...). Ver docs/design-system.md, seção 5.
 *
 * Onde uma chave do Tailwind é sobrescrita (ex. `sm` em fontSize, `md` em
 * boxShadow), é proposital: o token do design system substitui o valor
 * default do Tailwind em todo o projeto, não convive com ele.
 */
import defaultTheme from "tailwindcss/defaultTheme.js";

/**
 * Escala global da interface (Ajustes de UX/UI + Etapa F9) — mesmo
 * multiplicador de `--ui-scale` em `src/index.css` (1.2, documentado nos
 * dois lugares). Tipografia/radius escalam via variável CSS (index.css já
 * fazia isso, só os VALORES mudaram); espaçamento/altura/largura (que
 * usam a escala padrão do Tailwind, nunca conectada a uma CSS custom
 * property) escala aqui, sobrescrevendo `theme.spacing` inteiro a partir
 * da escala default real do Tailwind (`tailwindcss/defaultTheme`, nunca
 * copiada à mão — se o Tailwind mudar de versão, a escala usada aqui
 * acompanha automaticamente). `0px`/`1px` nunca escalam (zero continua
 * zero; a borda de 1px precisa continuar exatamente 1px, nunca um
 * "1.2px" fracionário estranho). Resultado: TODO componente que já usa
 * `p-*`/`gap-*`/`h-*`/`w-*`/`m-*`/etc. fica ~20% maior automaticamente,
 * sem editar um único componente — cumpre o pedido de "reorganizar os
 * tokens, não hardcodar em cada lugar". Não é uma CSS custom property
 * (não pode ser, com segurança, dentro de `theme.spacing` do Tailwind —
 * ver nota em index.css); é uma constante de build centralizada, o passo
 * intermediário documentado antes de uma preferência real de densidade
 * (Compacto/Padrão/Confortável) trocável em runtime.
 */
const UI_SCALE = 1.2;

function escalarEspacamento(valor) {
  if (valor === "0px" || valor === "1px") return valor;
  const remOriginal = parseFloat(valor);
  if (Number.isNaN(remOriginal)) return valor;
  const remEscalado = Math.round(remOriginal * UI_SCALE * 1000) / 1000;
  return `${remEscalado}rem`;
}

const spacingEscalado = Object.fromEntries(
  Object.entries(defaultTheme.spacing).map(([chave, valor]) => [chave, escalarEspacamento(valor)]),
);

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    // Fora de `extend` de propósito — substitui a escala inteira, não
    // convive com os valores default do Tailwind (mesmo raciocínio já
    // documentado acima para fontSize/borderRadius).
    spacing: spacingEscalado,
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: {
          1: "var(--color-surface-1)",
          2: "var(--color-surface-2)",
          3: "var(--color-surface-3)",
          4: "var(--color-surface-4)",
        },
        border: {
          subtle: "var(--color-border-subtle)",
          DEFAULT: "var(--color-border-default)",
          strong: "var(--color-border-strong)",
        },
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          tertiary: "var(--color-text-tertiary)",
          disabled: "var(--color-text-disabled)",
          onAccent: "var(--color-text-on-accent)",
          // Texto sobre fundo SÓLIDO de cada semântica — `StatusChip`
          // (revisão de UX de Cartões, "cores adaptativas"), mesmo
          // princípio de `onAccent`.
          onPositive: "var(--color-text-on-positive)",
          onNegative: "var(--color-text-on-negative)",
          onWarning: "var(--color-text-on-warning)",
          onInfo: "var(--color-text-on-info)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          hover: "var(--color-accent-hover)",
          active: "var(--color-accent-active)",
          subtle: "var(--color-accent-subtle)",
          ring: "var(--color-accent-ring)",
        },
        positive: {
          DEFAULT: "var(--color-positive)",
          subtle: "var(--color-positive-subtle)",
        },
        negative: {
          DEFAULT: "var(--color-negative)",
          subtle: "var(--color-negative-subtle)",
        },
        warning: {
          DEFAULT: "var(--color-warning)",
          subtle: "var(--color-warning-subtle)",
        },
        info: {
          DEFAULT: "var(--color-info)",
          subtle: "var(--color-info-subtle)",
        },
        chart: {
          1: "var(--color-chart-1)",
          2: "var(--color-chart-2)",
          3: "var(--color-chart-3)",
          4: "var(--color-chart-4)",
          5: "var(--color-chart-5)",
          6: "var(--color-chart-6)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      // Escala tipográfica — design-system.md, seção 7.1. `sm` sobrescreve
      // o default do Tailwind (nosso token de 13px, não o de 14px padrão).
      fontSize: {
        display: ["var(--text-display-size)", { lineHeight: "var(--text-display-leading)", letterSpacing: "var(--text-display-tracking)" }],
        h1: ["var(--text-h1-size)", { lineHeight: "var(--text-h1-leading)", letterSpacing: "var(--text-h1-tracking)" }],
        h2: ["var(--text-h2-size)", { lineHeight: "var(--text-h2-leading)" }],
        h3: ["var(--text-h3-size)", { lineHeight: "var(--text-h3-leading)" }],
        body: ["var(--text-body-size)", { lineHeight: "var(--text-body-leading)" }],
        sm: ["var(--text-sm-size)", { lineHeight: "var(--text-sm-leading)" }],
        caption: ["var(--text-caption-size)", { lineHeight: "var(--text-caption-leading)" }],
        micro: ["var(--text-micro-size)", { lineHeight: "var(--text-micro-leading)" }],
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        full: "var(--radius-full)",
      },
      boxShadow: {
        xs: "var(--shadow-xs)",
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
        // Glow discreto de acento (Etapa de Refinamento Visual) — hover de
        // alto destaque (botão primário, item de navegação ativo, StatCard).
        "glow-accent": "var(--shadow-glow-accent)",
      },
      backdropBlur: {
        sm: "var(--blur-sm)",
        md: "var(--blur-md)",
        lg: "var(--blur-lg)",
        xl: "var(--blur-xl)",
      },
      // Curvas e durações — fonte canônica em docs/motion-principles.md,
      // seção 4. `ease-out`/`ease-in`/`ease-in-out` sobrescrevem as curvas
      // genéricas do CSS: nenhum lugar do projeto deve usar a easing
      // default do navegador (motion-principles.md, seção 4.2).
      transitionTimingFunction: {
        out: "var(--ease-out)",
        in: "var(--ease-in)",
        "in-out": "var(--ease-in-out)",
      },
      transitionDuration: {
        instant: "var(--duration-instant)",
        fast: "var(--duration-fast)",
        base: "var(--duration-base)",
        moderate: "var(--duration-moderate)",
        slow: "var(--duration-slow)",
      },
    },
  },
  plugins: [],
};
