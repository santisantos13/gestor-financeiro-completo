import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { Search } from "lucide-react";
import { modalBackdrop, modalPanel } from "../../lib/motion";
import { destacarTrecho } from "../../utils/highlight";
import { buscarComandos } from "../../lib/commandPalette";

/**
 * Command Palette (Sprint de Refinamento Premium, item 16,
 * `docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 16) —
 * `Ctrl+K`/`Cmd+K` abre um modal de busca+navegação, disponível em
 * qualquer rota autenticada (montado uma única vez em `AppLayout`).
 * Reaproveita `modalBackdrop`/`modalPanel` (mesmo padrão visual de
 * `FormDialog`) e `destacarTrecho` (mesmo destaque de busca de
 * `RichPicker`/`SearchSelect`) — nenhum padrão visual novo.
 */
export function CommandPalette() {
  const navigate = useNavigate();
  const [aberto, setAberto] = useState(false);
  const [query, setQuery] = useState("");
  const [indiceSelecionado, setIndiceSelecionado] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listaRef = useRef<HTMLUListElement>(null);

  const resultados = useMemo(() => buscarComandos(query), [query]);

  function fechar() {
    setAberto(false);
    setQuery("");
    setIndiceSelecionado(0);
  }

  function navegarPara(rota: string) {
    fechar();
    navigate(rota);
  }

  // Atalho global: ignora quando o foco já está num campo de texto (não
  // interfere na digitação em nenhum outro formulário da tela) - exceto
  // quando o próprio atalho é Ctrl/Cmd+K, que sempre deve funcionar.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const combinacaoAtalho = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
      if (combinacaoAtalho) {
        event.preventDefault();
        setAberto((atual) => !atual);
        return;
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (aberto) inputRef.current?.focus();
  }, [aberto]);

  useEffect(() => {
    setIndiceSelecionado(0);
  }, [query]);

  useEffect(() => {
    const item = listaRef.current?.children[indiceSelecionado] as HTMLElement | undefined;
    item?.scrollIntoView({ block: "nearest" });
  }, [indiceSelecionado]);

  function onKeyDownModal(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault();
      fechar();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setIndiceSelecionado((atual) => Math.min(atual + 1, resultados.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setIndiceSelecionado((atual) => Math.max(atual - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const selecionado = resultados[indiceSelecionado];
      if (selecionado) navegarPara(selecionado.rota);
    }
  }

  return createPortal(
    <AnimatePresence>
      {aberto && (
        <motion.div
          {...modalBackdrop}
          className="fixed inset-0 z-[var(--z-tier2)] flex items-start justify-center bg-bg/60 pt-[15vh] backdrop-blur-lg"
          onClick={fechar}
        >
          <motion.div
            {...modalPanel}
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={onKeyDownModal}
            className="w-full max-w-lg overflow-hidden rounded-md border border-border bg-surface-4 shadow-xl"
          >
            <div className="flex items-center gap-2.5 border-b border-border-subtle px-4 py-3">
              <Search size={16} className="shrink-0 text-text-tertiary" aria-hidden="true" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Para onde você quer ir?"
                className="w-full bg-transparent text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none"
                aria-label="Buscar"
              />
              <kbd className="shrink-0 rounded-sm border border-border-subtle px-1.5 py-0.5 text-micro text-text-tertiary">
                Esc
              </kbd>
            </div>

            <ul ref={listaRef} className="max-h-80 overflow-y-auto p-2">
              {resultados.length === 0 && (
                <li className="px-3 py-6 text-center text-sm text-text-tertiary">Nenhum resultado.</li>
              )}
              {resultados.map((resultado, index) => (
                <li key={resultado.id}>
                  <button
                    type="button"
                    onClick={() => navegarPara(resultado.rota)}
                    onMouseEnter={() => setIndiceSelecionado(index)}
                    className={`flex w-full items-center gap-2.5 rounded-sm px-3 py-2 text-left text-sm transition-colors duration-fast ease-out ${
                      index === indiceSelecionado ? "bg-surface-3 text-text-primary" : "text-text-secondary"
                    }`}
                  >
                    <resultado.icon size={16} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                    {destacarTrecho(resultado.label, query)}
                  </button>
                </li>
              ))}
            </ul>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
