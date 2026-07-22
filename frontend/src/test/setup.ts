/**
 * Setup global do Vitest (`vite.config.ts`, `test.setupFiles`) — roda uma
 * vez antes de toda a suíte. Só registra os matchers de
 * `@testing-library/jest-dom` (`toBeInTheDocument`, `toHaveTextContent`
 * etc.) e limpa o DOM entre testes; nenhuma outra configuração global de
 * propósito (ver docs/analise-arquitetural-testes-frontend.md — sem
 * globals do Vitest, cada teste importa o que precisa explicitamente).
 */
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

/** jsdom não implementa `window.matchMedia` — vários componentes de UI
 * (`useIsMobileViewport`/`RichPicker`/`ColorPicker`/`IconPicker`, tema
 * escuro/claro) dependem dele. Mock mínimo (sempre "não corresponde"),
 * suficiente pra esses componentes não quebrarem ao montar em teste; não
 * simula nenhum breakpoint real de verdade (nenhum teste desta etapa
 * depende de comportamento responsivo). */
/** jsdom também não implementa `Element.scrollIntoView` — `ui/Form.tsx`
 * chama isso ao focar o primeiro campo com erro após submit inválido. */
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}

if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
