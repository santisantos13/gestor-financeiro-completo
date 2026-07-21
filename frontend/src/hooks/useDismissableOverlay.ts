import { useEffect, useRef, useState } from "react";

/**
 * Mecânica compartilhada de "fechar ao clicar fora / fechar com Esc" —
 * extraída durante a Etapa F10 (`docs/analise-arquitetural-overlays.md`,
 * seção 7) porque `IconField`, `ColorField` e `SearchSelect` cada um
 * reimplementava exatamente este mesmo `useEffect` de listeners. Qualquer
 * overlay tier 1 novo (`RichPicker`, e a versão enriquecida de
 * `SearchSelect`) usa este hook em vez de duplicar a lógica de novo.
 *
 * Não é um componente visual — só o estado de "está montado, então ouça
 * clique fora e Esc"; quem chama decide o que fazer com `onClose` (nesta
 * base, sempre "fechar o popover").
 */
export function useDismissableOverlay<T extends HTMLElement>(
  open: boolean,
  onClose: () => void,
  /** Refs adicionais cujo conteúdo NUNCA conta como "fora" — necessário
   * para painéis flutuantes portados para `document.body`
   * (`useFloatingPanel.ts`): o painel deixa de ser descendente DOM do
   * gatilho, então o clique dentro dele precisa ser explicitamente
   * excluído da checagem, senão todo clique no próprio painel fecharia o
   * overlay por engano. Refs são estáveis (mutáveis), por isso não entram
   * no array de dependências abaixo — mesmo raciocínio já aplicado a
   * `open`. */
  extraRefs: React.RefObject<HTMLElement>[] = [],
) {
  const rootRef = useRef<T>(null);

  useEffect(() => {
    if (!open) return;

    function onClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (extraRefs.some((ref) => ref.current?.contains(target))) return;
      onClose();
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return rootRef;
}

/** `true` abaixo do breakpoint `md` (768px) do Design System
 * (`docs/design-system.md`, seção 24) — usado por `RichPicker` para trocar
 * o popover ancorado por um shell de `Dialog` centralizado em telas
 * pequenas (`docs/analise-arquitetural-overlays.md`, seção 4.3). */
export function useIsMobileViewport(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches,
  );

  useEffect(() => {
    const mql = window.matchMedia("(max-width: 767px)");
    function onChange() {
      setIsMobile(mql.matches);
    }
    mql.addEventListener("change", onChange);
    onChange();
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return isMobile;
}
