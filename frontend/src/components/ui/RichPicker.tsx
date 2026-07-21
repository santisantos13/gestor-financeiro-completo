import { useDeferredValue, useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, Search } from "lucide-react";
import { DURATION, EASE, modalBackdrop } from "../../lib/motion";
import { useFloatingPanel } from "../../hooks/useFloatingPanel";
import { useIsMobileViewport } from "../../hooks/useDismissableOverlay";
import { destacarTrecho } from "../../utils/highlight";

export interface RichPickerItem<T> {
  value: T;
  label: string;
  /** O que renderizar no grid/lista — ícone, swatch de cor, monograma de
   * instituição, o que fizer sentido para o registry consumido. O
   * `RichPicker` não sabe o que é isso, só posiciona. */
  render: ReactNode;
  /** Grupo opcional (ex. "Moradia", "Vermelho"). Quando presente em pelo
   * menos um item, o picker organiza em seções com cabeçalho. */
  group?: string;
  /** Termos extras de busca além do label (ex. aliases de instituição). */
  keywords?: string[];
}

export interface RichPickerProps<T> {
  value: T | null;
  onChange: (value: T) => void;
  items: RichPickerItem<T>[];
  /** grid para ícone/cor (swatch puro), list para instituição/bandeira
   * (monograma + nome legível). */
  layout: "grid" | "list";
  placeholder: string;
  searchPlaceholder?: string;
  /** Abaixo deste número de itens, a busca nem aparece. Default: 10. */
  searchThreshold?: number;
  /** Preview maior no topo do painel (ex. swatch grande + hex). */
  renderPreview?: (item: RichPickerItem<T> | null) => ReactNode;
  /** Nó extra fixado no fim da lista de itens (ex. opção "Outra" do
   * `BankPicker`, que revela um campo de texto livre). */
  footerExtra?: ReactNode;
  disabled?: boolean;
  hasError?: boolean;
  id?: string;
  name?: string;
  onBlur?: () => void;
  "aria-label"?: string;
  className?: string;
}

const GRID_COLUMNS = 10;
const PANEL_WIDTH = { grid: 560, list: 400 } as const;

/**
 * Popover tier 1 rico — `docs/analise-arquitetural-overlays.md`, seção 4.3,
 * e `docs/analise-arquitetural-rich-pickers.md`, seção 2. Componente base
 * genérico, sem nenhum conhecimento de ícone/cor/instituição/bandeira
 * específico — cada registry entra via `items`.
 *
 * Refinamento (`docs/analise-arquitetural-refinamento-pickers-performance.md`,
 * seções 2-3): o painel agora é sempre portado para `document.body` com
 * `position: fixed` calculado a partir do gatilho (`useFloatingPanel`) —
 * escapa do clipping de qualquer `overflow-y-auto` ancestral (o corpo de um
 * `FormDialog`, por exemplo), o que antes forçava um painel pequeno com
 * scroll próprio dentro do scroll do modal. Grid de 6 para 10 colunas,
 * células maiores, altura útil de até `min(70vh, 480px)` em vez de um
 * limite fixo pequeno — cabe muito mais opções por tela, sem virar um
 * "dropdown gigante" (a largura continua contida, só a altura/densidade
 * aumentam de verdade).
 */
export function RichPicker<T extends string>({
  value,
  onChange,
  items,
  layout,
  placeholder,
  searchPlaceholder = "Buscar...",
  searchThreshold = 10,
  renderPreview,
  footerExtra,
  disabled = false,
  hasError = false,
  id,
  name,
  onBlur,
  className = "",
  ...aria
}: RichPickerProps<T>) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const deferredQuery = useDeferredValue(query);
  const searchRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();
  const isMobile = useIsMobileViewport();

  function close() {
    setOpen(false);
    onBlur?.();
  }

  const { anchorRef, panelRef, rect } = useFloatingPanel<HTMLDivElement>(open, close, {
    panelWidth: () => PANEL_WIDTH[layout],
    estimatedHeight: 420,
  });

  const mostraBusca = items.length >= searchThreshold;

  const filtrados = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) || item.keywords?.some((k) => k.toLowerCase().includes(q)),
    );
  }, [items, deferredQuery]);

  const grupos = useMemo(() => {
    const temGrupo = filtrados.some((item) => item.group);
    if (!temGrupo) return [{ nome: null as string | null, itens: filtrados }];
    const ordem: string[] = [];
    const mapa = new Map<string, RichPickerItem<T>[]>();
    for (const item of filtrados) {
      const chave = item.group ?? "";
      if (!mapa.has(chave)) {
        ordem.push(chave);
        mapa.set(chave, []);
      }
      mapa.get(chave)!.push(item);
    }
    return ordem.map((chave) => ({ nome: chave || null, itens: mapa.get(chave)! }));
  }, [filtrados]);

  const flat = useMemo(() => grupos.flatMap((g) => g.itens), [grupos]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(Math.max(0, flat.findIndex((item) => item.value === value)));
    if (mostraBusca) {
      const t = setTimeout(() => searchRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    setActiveIndex((i) => Math.min(i, Math.max(0, flat.length - 1)));
  }, [flat.length]);

  const selecionado = items.find((item) => item.value === value) ?? null;

  function selecionar(item: RichPickerItem<T>) {
    onChange(item.value);
    close();
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (flat.length === 0) return;
    const passo = layout === "grid" ? GRID_COLUMNS : 1;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => Math.min(flat.length - 1, i + passo));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(0, i - passo));
    } else if (layout === "grid" && event.key === "ArrowRight") {
      event.preventDefault();
      setActiveIndex((i) => Math.min(flat.length - 1, i + 1));
    } else if (layout === "grid" && event.key === "ArrowLeft") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (flat[activeIndex]) selecionar(flat[activeIndex]);
    }
  }

  const painel = (
    <motion.div
      ref={panelRef}
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } }}
      exit={{ opacity: 0, y: -4, transition: { duration: DURATION.fast, ease: EASE.in } }}
      role="listbox"
      aria-label={aria["aria-label"] ?? placeholder}
      id={listboxId}
      onKeyDown={onKeyDown}
      style={
        isMobile || !rect
          ? undefined
          : { position: "fixed", top: rect.top, left: rect.left, width: rect.width }
      }
      className={
        isMobile
          ? "flex max-h-[70vh] w-full flex-col overflow-hidden rounded-xl border border-border bg-surface-4 shadow-xl"
          : "z-[var(--z-tier1)] flex max-h-[min(70vh,480px)] flex-col overflow-hidden rounded-md border border-border bg-surface-3 shadow-md"
      }
    >
      {renderPreview && (
        <div className="shrink-0 border-b border-border-subtle p-3">{renderPreview(selecionado)}</div>
      )}

      {mostraBusca && (
        <div className="relative shrink-0 border-b border-border-subtle p-1.5">
          <Search
            size={14}
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-text-tertiary"
            aria-hidden="true"
          />
          <input
            ref={searchRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={searchPlaceholder}
            className="h-8 w-full rounded-sm bg-transparent pl-6 pr-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none"
          />
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {flat.length === 0 && <p className="px-2 py-1.5 text-sm text-text-tertiary">Nenhum resultado</p>}

        {grupos.map(
          (grupo, grupoIndex) =>
            grupo.itens.length > 0 && (
              <div key={grupo.nome ?? `sem-grupo-${grupoIndex}`} className="mb-3 last:mb-0">
                {grupo.nome && (
                  <p className="mb-1.5 px-1 text-caption uppercase tracking-wide text-text-tertiary">{grupo.nome}</p>
                )}
                {layout === "grid" ? (
                  <div className="grid grid-cols-10 gap-1.5">
                    {grupo.itens.map((item) => {
                      const flatIndex = flat.indexOf(item);
                      return (
                        <button
                          key={String(item.value)}
                          type="button"
                          role="option"
                          aria-selected={item.value === value}
                          title={item.label}
                          onMouseEnter={() => setActiveIndex(flatIndex)}
                          onClick={() => selecionar(item)}
                          className={`flex h-11 w-11 items-center justify-center rounded-sm transition-all duration-fast ease-out hover:scale-110 ${
                            item.value === value
                              ? "bg-accent-subtle text-accent"
                              : flatIndex === activeIndex
                                ? "bg-surface-4 text-text-primary ring-2 ring-accent/40"
                                : "text-text-secondary hover:bg-surface-4"
                          }`}
                        >
                          {item.render}
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col gap-0.5">
                    {grupo.itens.map((item) => {
                      const flatIndex = flat.indexOf(item);
                      return (
                        <button
                          key={String(item.value)}
                          type="button"
                          role="option"
                          aria-selected={item.value === value}
                          onMouseEnter={() => setActiveIndex(flatIndex)}
                          onClick={() => selecionar(item)}
                          className={`flex items-center gap-2.5 rounded-sm px-2 py-2 text-left text-sm transition-colors duration-fast ease-out ${
                            item.value === value
                              ? "bg-accent-subtle text-accent"
                              : flatIndex === activeIndex
                                ? "bg-surface-4 text-text-primary ring-2 ring-inset ring-accent/40"
                                : "text-text-primary hover:bg-surface-4"
                          }`}
                        >
                          <span className="shrink-0">{item.render}</span>
                          <span className="truncate">{destacarTrecho(item.label, deferredQuery)}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ),
        )}

        {footerExtra}
      </div>
    </motion.div>
  );

  return (
    <div ref={anchorRef} className={`relative ${className}`}>
      <button
        type="button"
        id={id}
        name={name}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => setOpen((v) => !v)}
        className={`flex h-9 w-full items-center justify-between rounded-sm border bg-surface-2 px-3 text-body transition-colors duration-fast ease-out disabled:cursor-not-allowed disabled:bg-surface-1 disabled:text-text-disabled ${
          hasError ? "border-negative" : "border-border focus-visible:border-accent"
        }`}
      >
        {selecionado ? (
          <span className="flex min-w-0 items-center gap-2 text-text-primary">
            <span className="shrink-0">{selecionado.render}</span>
            <span className="truncate">{selecionado.label}</span>
          </span>
        ) : (
          <span className="truncate text-text-tertiary">{placeholder}</span>
        )}
        <ChevronDown
          size={16}
          className={`shrink-0 text-text-tertiary transition-transform duration-fast ease-out ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {createPortal(
        <AnimatePresence>
          {open &&
            (isMobile ? (
              // Wrapper só de POSICIONAMENTO (centraliza em telas pequenas) —
              // nunca um backdrop próprio. RichPicker é Tier 1
              // (docs/analise-arquitetural-overlays.md, seção 2: "Tier 1
              // nunca tem backdrop"), e é usado 100% das vezes de dentro de
              // um FormDialog já aberto (Tier 2, seu próprio backdrop já
              // escurece a tela). Antes desta correção, este wrapper
              // aplicava um SEGUNDO `bg-bg/60 backdrop-blur-lg` idêntico ao
              // do FormDialog por cima do primeiro — dois véus de 60%
              // opacidade + blur empilhados compõem para ~84% de opacidade,
              // e cobrem até o próprio conteúdo do FormDialog (que fica
              // atrás desta camada), lido pelo usuário como "a tela fica
              // toda preta e trava" — a causa raiz do bug relatado ao abrir
              // o ColorPicker/IconPicker de Categoria em viewport estreito.
              // `{...modalBackdrop}` (só a animação de opacidade) é mantido
              // para que o `AnimatePresence` continue tratando este
              // `motion.div` como o item rastreado, permitindo a animação de
              // saída do `painel` (motion.div-filho) funcionar normalmente.
              <motion.div
                {...modalBackdrop}
                className="fixed inset-0 z-[var(--z-tier1)] flex items-center justify-center p-4"
                onClick={close}
              >
                <div onClick={(event) => event.stopPropagation()} className="w-full max-w-sm">
                  {painel}
                </div>
              </motion.div>
            ) : (
              painel
            ))}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
