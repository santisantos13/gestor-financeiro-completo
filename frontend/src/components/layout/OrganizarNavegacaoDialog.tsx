import { useEffect, useMemo, useState } from "react";
import { Reorder, useDragControls } from "motion/react";
import { ChevronDown, ChevronUp, GripVertical, Lock } from "lucide-react";
import { FormDialog } from "../ui/FormDialog";
import { Button } from "../ui/Button";
import { CancelButton } from "../ui/CancelButton";
import { SPRING } from "../../lib/motion";
import { useNavOrder } from "../../hooks/useNavOrder";
import { NAV_ITEMS, type NavItem } from "./navItems";

const ITEM_DASHBOARD = NAV_ITEMS.find((item) => item.to === "/")!;
const ORDEM_PADRAO = NAV_ITEMS.filter((item) => item.to !== "/").map((item) => item.to);

export interface OrganizarNavegacaoDialogProps {
  open: boolean;
  onClose: () => void;
}

function arraysIguais(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((valor, indice) => valor === b[indice]);
}

/**
 * Modal de "Organizar navegação" — aberto a partir de `UserMenu.tsx`
 * (bloco "Aparência", abaixo do `ThemeToggle`). Casca 100% `FormDialog`
 * (design-system.md, seção 22: foco preso, "só um modal por vez", scroll
 * do body bloqueado, fluxo de "descartar alterações?" via `isDirty`) — só
 * o conteúdo (lista reordenável) é próprio desta etapa. Racional completo
 * de cada decisão abaixo em
 * docs/analise-arquitetural-organizacao-sidebar.md.
 *
 * `isDirty` aqui não vem de React Hook Form — vem da comparação entre a
 * ordem em edição e a ordem persistida no momento em que o modal abriu.
 * `FormDialog` não precisa saber disso: só recebe o booleano, exatamente
 * como o próprio componente já documenta ("decoupled de propósito").
 */
export function OrganizarNavegacaoDialog({ open, onClose }: OrganizarNavegacaoDialogProps) {
  const { itensOrdenados, salvarOrdem } = useNavOrder();
  const [ordemEmEdicao, setOrdemEmEdicao] = useState<string[]>(() => itensOrdenados.map((item) => item.to));

  // Reinicia a lista em edição sempre que o modal abre, a partir da ordem
  // persistida naquele instante — nunca reaproveita um rascunho de uma
  // sessão anterior que foi fechada sem salvar.
  useEffect(() => {
    if (open) {
      setOrdemEmEdicao(itensOrdenados.map((item) => item.to));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const itensPorTo = useMemo(() => new Map(itensOrdenados.map((item) => [item.to, item])), [itensOrdenados]);
  const ordemOriginal = useMemo(() => itensOrdenados.map((item) => item.to), [itensOrdenados]);
  const isDirty = !arraysIguais(ordemEmEdicao, ordemOriginal);

  function mover(to: string, direcao: -1 | 1) {
    setOrdemEmEdicao((atual) => {
      const indice = atual.indexOf(to);
      const novoIndice = indice + direcao;
      if (novoIndice < 0 || novoIndice >= atual.length) return atual;
      const copia = [...atual];
      [copia[indice], copia[novoIndice]] = [copia[novoIndice], copia[indice]];
      return copia;
    });
  }

  function handleRestaurarPadrao() {
    setOrdemEmEdicao(ORDEM_PADRAO);
  }

  function handleSalvar(requestClose: () => void) {
    salvarOrdem(ordemEmEdicao);
    requestClose();
  }

  return (
    <FormDialog
      open={open}
      title="Organizar navegação"
      description="Arraste os itens (ou use as setas) para mudar a ordem do menu. O Dashboard permanece fixo."
      isDirty={isDirty}
      onClose={onClose}
      footer={(requestClose) => (
        <div className="flex items-center justify-between gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={handleRestaurarPadrao}>
            Restaurar padrão
          </Button>
          <div className="flex gap-2">
            <CancelButton size="sm" onClick={requestClose} />
            <Button type="button" variant="primary" size="sm" onClick={() => handleSalvar(requestClose)}>
              Salvar
            </Button>
          </div>
        </div>
      )}
    >
      {/* Card fixo do Dashboard — deliberadamente FORA do Reorder.Group
          (não é um Reorder.Item com drag desabilitado, o que ainda pareceria
          "quase arrastável"). Visual distinto (opacidade reduzida, ícone de
          cadeado, legenda) comunica a regra sem o usuário precisar tentar
          arrastar para descobrir que não funciona. */}
      <div className="flex items-center gap-3 rounded-md border border-border-subtle bg-surface-2 px-3 py-2.5 opacity-70">
        <Lock size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
        <ITEM_DASHBOARD.icon size={18} className="shrink-0 text-text-tertiary" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-text-secondary">
          {ITEM_DASHBOARD.label}
        </span>
        <span className="shrink-0 text-caption text-text-tertiary">Sempre primeiro</span>
      </div>

      <Reorder.Group
        as="ul"
        axis="y"
        values={ordemEmEdicao}
        onReorder={setOrdemEmEdicao}
        className="mt-2 flex flex-col gap-2"
      >
        {ordemEmEdicao.map((to, indice) => {
          const item = itensPorTo.get(to);
          if (!item) return null;
          return (
            <ReorderableNavItem
              key={to}
              item={item}
              isFirst={indice === 0}
              isLast={indice === ordemEmEdicao.length - 1}
              onMoveUp={() => mover(to, -1)}
              onMoveDown={() => mover(to, 1)}
            />
          );
        })}
      </Reorder.Group>
    </FormDialog>
  );
}

interface ReorderableNavItemProps {
  item: NavItem;
  isFirst: boolean;
  isLast: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

/**
 * Uma linha da lista reordenável. Componente próprio (não inline dentro do
 * `.map` do pai) porque `useDragControls` é um hook — precisa viver no topo
 * de um componente com identidade estável por item, nunca dentro de um
 * callback de `.map` do componente pai.
 *
 * `dragListener={false}` + `dragControls` própria, disparada só pelo
 * `onPointerDown` da alça (`GripVertical`): o card inteiro NÃO inicia
 * drag a partir de qualquer ponto — clicar nos botões de mover ou em
 * qualquer área do card não deve começar um arrasto por acidente.
 *
 * Botões `ChevronUp`/`ChevronDown` são a alternativa por teclado/toque
 * assistido — `Reorder` do `motion` não tem suporte nativo a teclado
 * (é puramente baseado em gesto de ponteiro), então esta é a única forma
 * de reordenar sem arrastar. Sempre visíveis (nunca só em hover, o que
 * excluiria teclado/leitor de tela) e com `aria-label` que inclui o nome
 * do item.
 */
function ReorderableNavItem({ item, isFirst, isLast, onMoveUp, onMoveDown }: ReorderableNavItemProps) {
  const dragControls = useDragControls();

  return (
    <Reorder.Item
      value={item.to}
      as="li"
      dragListener={false}
      dragControls={dragControls}
      transition={SPRING.smooth}
      className="flex items-center gap-3 rounded-md border border-border bg-surface-3 px-3 py-2.5 shadow-sm"
    >
      <button
        type="button"
        onPointerDown={(event) => dragControls.start(event)}
        aria-label={`Arrastar para reordenar ${item.label}`}
        className="flex h-10 w-10 shrink-0 touch-none cursor-grab items-center justify-center rounded-sm text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary active:cursor-grabbing"
      >
        <GripVertical size={16} aria-hidden="true" />
      </button>

      <item.icon size={18} className="shrink-0 text-text-secondary" aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate text-sm font-medium text-text-primary">{item.label}</span>

      <div className="flex shrink-0 gap-0.5">
        <button
          type="button"
          onClick={onMoveUp}
          disabled={isFirst}
          aria-label={`Mover ${item.label} para cima`}
          className="flex h-10 w-10 items-center justify-center rounded-sm text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronUp size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onMoveDown}
          disabled={isLast}
          aria-label={`Mover ${item.label} para baixo`}
          className="flex h-10 w-10 items-center justify-center rounded-sm text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-4 hover:text-text-primary disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronDown size={16} aria-hidden="true" />
        </button>
      </div>
    </Reorder.Item>
  );
}
