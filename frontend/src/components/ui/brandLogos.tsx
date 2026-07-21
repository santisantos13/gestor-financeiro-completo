import type { SVGProps } from "react";

/**
 * Logos reais de bandeira (Visa/Mastercard) — pedido explícito do usuário
 * (2026-07-24), com as imagens de referência anexadas na própria conversa.
 * Recriações simplificadas em SVG (não os arquivos originais), fiéis às
 * cores oficiais de marca já usadas em `lib/bandeiras.ts` (`#EB001B` e
 * `#1A1F71`).
 *
 * Mesmo raciocínio já registrado em `CartaoVisual.tsx` sobre usar a cor de
 * marca real de cada instituição: projeto de uso pessoal, nunca publicado -
 * reproduzir marcas amplamente reconhecidas de forma descritiva (indicar a
 * bandeira de um cartão) não é o mesmo problema de direito autoral que
 * reproduzir uma obra original.
 *
 * Só Visa/Mastercard ganham logo real - as outras 5 bandeiras continuam
 * com o monograma sobre cor de marca (`BandeiraBadge`/`CardBrandPicker`),
 * que já cumpria bem o papel e não teve referência visual pedida aqui.
 */

/** Marca "duas bolas" da Mastercard (versão flat pós-rebranding de 2016) -
 * círculo vermelho + círculo dourado com sobreposição translúcida, gerando
 * o laranja característico sem precisar calcular a interseção exata em
 * path (suficiente para um ícone pequeno, sem pretensão de reprodução
 * vetorial oficial pixel-a-pixel). */
export function MastercardLogo({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 32 20" role="img" aria-label="Mastercard" className={className} {...props}>
      <circle cx="12" cy="10" r="9" fill="#EB001B" />
      <circle cx="20" cy="10" r="9" fill="#F79E1B" fillOpacity={0.85} />
    </svg>
  );
}

/** Wordmark "VISA" em itálico/negrito, branco - Visa (como a maioria das
 * bandeiras/instituições publica oficialmente) tem uma variante "reversa"
 * clara para uso sobre fundo escuro/colorido; usamos essa aqui porque o
 * selo deste app não tem mais fundo sólido atrás (só uma borda sutil, ver
 * `BandeiraBadge`) - a versão em `#1A1F71` (azul-marinho de marca) ficava
 * ilegível sobre o tema escuro do app sem uma caixa branca atrás. */
export function VisaLogo({ className, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 48 20" role="img" aria-label="Visa" className={className} {...props}>
      <text
        x="24"
        y="15"
        textAnchor="middle"
        fontFamily="Arial, Helvetica, sans-serif"
        fontStyle="italic"
        fontWeight={800}
        fontSize="16"
        letterSpacing="-0.5"
        fill="#FFFFFF"
      >
        VISA
      </text>
    </svg>
  );
}
