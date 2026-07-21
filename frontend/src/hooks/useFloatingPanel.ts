import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { useDismissableOverlay } from "./useDismissableOverlay";

export interface FloatingPanelRect {
  top: number;
  left: number;
  width: number;
}

export interface UseFloatingPanelOptions {
  /** Decide a largura do painel a partir da largura do próprio gatilho —
   * default: mesma largura do gatilho (comportamento de sempre de
   * `Select`/`SearchSelect`/`MultiSelectField`). `RichPicker` passa uma
   * largura fixa maior (painel de grid/lista bem mais largo que o campo
   * que o abre — `ColorPicker` é o caso mais extremo, gatilho de 112px
   * abrindo um painel de centenas de pixels). */
  panelWidth?: (anchorWidth: number) => number;
  /** Altura estimada do painel, usada só para decidir se abre para baixo
   * (padrão) ou para cima quando não há espaço suficiente abaixo do
   * gatilho — não precisa ser exata, é só heurística de "cabe ou não
   * cabe". Default 320. */
  estimatedHeight?: number;
  /** `"start"` (padrão) alinha a borda ESQUERDA do painel com a borda
   * esquerda do gatilho — comportamento de sempre. `"end"` alinha a borda
   * DIREITA do painel com a borda direita do gatilho (ex. `ColumnVisibility`,
   * cujo botão costuma ficar no canto direito de uma `Toolbar` — o painel
   * precisa crescer para a esquerda, não para fora da tela). */
  align?: "start" | "end";
}

/**
 * Hook compartilhado de posicionamento — paga a dívida técnica registrada
 * em `docs/analise-arquitetural-overlays.md`, seção 7 (cada popover do
 * projeto reimplementava sua própria mecânica de abrir/fechar/posicionar).
 * Consolidado na etapa de Refinamento de Pickers/Performance
 * (`docs/analise-arquitetural-refinamento-pickers-performance.md`, seção
 * 2): resolve o problema real de "scroll dentro de scroll" — um painel
 * `position: absolute` preso dentro do corpo rolável de um `FormDialog`
 * (`overflow-y-auto`) fica clipado pelo ancestral, forçando um painel
 * pequeno com sua própria barra de rolagem interna.
 *
 * A correção NÃO promove o popover a um overlay tier 2 (Dialog/Drawer) —
 * isso violaria a regra de "nunca dois overlays tier 2 ao mesmo tempo"
 * toda vez que o picker abrisse de dentro de um `FormDialog` já aberto
 * (`docs/analise-arquitetural-overlays.md`, seção 2). A causa raiz é
 * puramente geométrica (clipping de `overflow`), então a correção também
 * é: `position: fixed` com coordenadas calculadas via
 * `getBoundingClientRect()` do gatilho, IGUAL à técnica que `RichPicker` já
 * usava só no fallback mobile (`createPortal` para `document.body`) —
 * agora estendida para o desktop também, unificando os dois caminhos.
 * Portar para `document.body` (em vez de só trocar `absolute` por `fixed`
 * no mesmo lugar da árvore) é necessário porque o `FormDialog` anima
 * `scale` no próprio painel (`lib/motion.ts`, `modalPanel`) — um `scale`
 * aplicado via `transform` cria um "containing block" novo para qualquer
 * descendente `position: fixed`, o que faria as coordenadas de
 * `getBoundingClientRect()` (sempre relativas ao viewport) ficarem erradas
 * se o painel continuasse sendo filho DOM do modal. Portado para
 * `document.body`, o cálculo é sempre relativo ao viewport de verdade,
 * sem essa ambiguidade.
 *
 * Continua Tier 1 (`docs/analise-arquitetural-overlays.md`, seção 2): sem
 * backdrop, sem focus trap próprio — fecha com `Esc`/clique fora
 * (`useDismissableOverlay`, com o painel portado passado como `extraRef`
 * para não contar como "fora" de si mesmo).
 *
 * CAUSA RAIZ REAL do bug "tela trava/fica em branco ao abrir Cor/Ícone"
 * (Estabilização de Overlays, 2ª rodada) — não era o backdrop duplicado
 * corrigido antes (esse era um bug real, só que secundário e só em
 * viewport móvel). `options` é sempre um objeto literal novo a cada
 * render de quem chama (`RichPicker`/`ColumnVisibility`/`DateInput` passam
 * `{ panelWidth: () => ... }` inline, nenhum consumidor memoiza com
 * `useCallback`) — `options.panelWidth` mudava de identidade a cada
 * render, o que recriava `recompute` (estava nas deps do `useCallback`),
 * o que fazia o `useLayoutEffect` abaixo rodar de novo mesmo com `open`
 * inalterado, chamando `setRect` com um objeto novo, causando OUTRO
 * render — um loop infinito de render que crasha o React (sem
 * ErrorBoundary no projeto, o app inteiro desmonta e a tela fica em
 * branco). Corrigido guardando `options` numa ref (sempre a mais
 * recente) e tornando `recompute` estável para sempre (`useCallback` com
 * deps vazias) — `recompute` só é recriado quando o COMPONENTE inteiro é
 * desmontado, nunca por causa de um `options` novo a cada render.
 */
export function useFloatingPanel<TAnchor extends HTMLElement, TPanel extends HTMLElement = HTMLDivElement>(
  open: boolean,
  onClose: () => void,
  options: UseFloatingPanelOptions = {},
) {
  const panelRef = useRef<TPanel>(null);
  const anchorRef = useDismissableOverlay<TAnchor>(open, onClose, [panelRef]);
  const [rect, setRect] = useState<FloatingPanelRect | null>(null);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const recompute = useCallback(() => {
    const el = anchorRef.current;
    if (!el) return;
    const { panelWidth, estimatedHeight = 320, align } = optionsRef.current;
    const anchorRect = el.getBoundingClientRect();
    const larguraDesejada = panelWidth ? panelWidth(anchorRect.width) : anchorRect.width;
    const width = Math.min(larguraDesejada, window.innerWidth - 16);

    let left = align === "end" ? anchorRect.right - width : anchorRect.left;
    if (left + width > window.innerWidth - 8) left = window.innerWidth - width - 8;
    left = Math.max(8, left);

    const espacoAbaixo = window.innerHeight - anchorRect.bottom;
    const top =
      espacoAbaixo < estimatedHeight && anchorRect.top > estimatedHeight
        ? Math.max(8, anchorRect.top - estimatedHeight - 4)
        : anchorRect.bottom + 4;

    setRect({ top, left, width });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      setRect(null);
      return;
    }
    recompute();
    // `scroll` com `capture: true` — reposiciona mesmo quando o elemento
    // que rolou é um ancestral qualquer (ex. o corpo do `FormDialog`), não
    // só a janela inteira.
    window.addEventListener("scroll", recompute, true);
    window.addEventListener("resize", recompute);
    return () => {
      window.removeEventListener("scroll", recompute, true);
      window.removeEventListener("resize", recompute);
    };
  }, [open, recompute]);

  return { anchorRef, panelRef, rect };
}
