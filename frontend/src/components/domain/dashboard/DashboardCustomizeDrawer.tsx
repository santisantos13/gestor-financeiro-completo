import { useState, type DragEvent } from "react";
import { GripVertical, RotateCcw } from "lucide-react";
import { Drawer } from "../../ui/Drawer";
import { Switch } from "../../ui/Switch";
import { Button } from "../../ui/Button";
import {
  CARDS_PERSONALIZAVEIS,
  layoutPadrao,
  type DashboardCardId,
  type LayoutDashboard,
} from "../../../lib/dashboardLayout";

export interface DashboardCustomizeDrawerProps {
  open: boolean;
  layout: LayoutDashboard;
  onChange: (layout: LayoutDashboard) => void;
  onClose: () => void;
}

/**
 * Drawer de personalização do Home (Sprint de Refinamento Premium, item
 * 15) — reordenar (drag-and-drop nativo, sem biblioteca) e mostrar/ocultar
 * os cards do Bento Grid. Mesmo componente de overlay tier 2 (`Drawer`) já
 * usado em Fatura/Financiamento; nada de novo em termos de padrão visual.
 *
 * Correção de 2026-07-22 (bug relatado pelo usuário, "arrastar não
 * funciona" + "ocultar não some"): a versão anterior colocava
 * `draggable` na `<li>` INTEIRA, que também continha o `Switch` — como o
 * `Switch` é um `<button>` interativo dentro de um ancestral `draggable`,
 * qualquer micro-movimento do mouse ao clicar nele podia ser interpretado
 * pelo navegador como início de um arraste da linha toda, "engolindo" o
 * clique antes que o `onCheckedChange` disparasse (a mesma causa explica
 * os dois sintomas). Além disso, o reordenamento era commitado ao
 * componente pai (com escrita em localStorage) a CADA evento
 * `dragover` — dezenas por segundo durante um arraste — criando uma
 * corrida entre o estado antigo capturado no closure e o novo já
 * recalculado, o que fazia a ordem "pular" de forma imprevisível.
 *
 * Fix: `draggable` migrou para a alcinha (`GripVertical`) — só ela inicia
 * o arraste, o resto da linha (inclusive o `Switch`) nunca é sequestrado.
 * A reordenação em si passou a ser calculada em estado LOCAL
 * (`ordemArraste`) durante o `dragover`, só sendo commitada ao pai (via
 * `onChange`, uma vez) no `drop`/`dragend` — sem escritas repetidas em
 * localStorage no meio do gesto.
 */
export function DashboardCustomizeDrawer({ open, layout, onChange, onClose }: DashboardCustomizeDrawerProps) {
  const [arrastando, setArrastando] = useState<DashboardCardId | null>(null);
  const [ordemArraste, setOrdemArraste] = useState<DashboardCardId[] | null>(null);
  const cardsPorId = new Map(CARDS_PERSONALIZAVEIS.map((c) => [c.id, c]));

  const ordemExibida = ordemArraste ?? layout.ordem;

  function onDragStart(id: DashboardCardId) {
    return (event: DragEvent<HTMLSpanElement>) => {
      setArrastando(id);
      setOrdemArraste(layout.ordem);
      event.dataTransfer.effectAllowed = "move";
    };
  }

  function onDragOverItem(id: DashboardCardId) {
    return (event: DragEvent<HTMLLIElement>) => {
      event.preventDefault();
      if (!arrastando || arrastando === id || !ordemArraste) return;

      const indiceOrigem = ordemArraste.indexOf(arrastando);
      const indiceDestino = ordemArraste.indexOf(id);
      if (indiceOrigem === -1 || indiceDestino === -1 || indiceOrigem === indiceDestino) return;

      const novaOrdem = [...ordemArraste];
      novaOrdem.splice(indiceOrigem, 1);
      novaOrdem.splice(indiceDestino, 0, arrastando);
      setOrdemArraste(novaOrdem);
    };
  }

  function confirmarArraste() {
    if (ordemArraste) onChange({ ...layout, ordem: ordemArraste });
    setArrastando(null);
    setOrdemArraste(null);
  }

  function onDrop(event: DragEvent<HTMLLIElement>) {
    event.preventDefault();
    confirmarArraste();
  }

  function alternarVisibilidade(id: DashboardCardId) {
    const oculto = layout.ocultos.includes(id);
    onChange({
      ...layout,
      ocultos: oculto ? layout.ocultos.filter((atual) => atual !== id) : [...layout.ocultos, id],
    });
  }

  function restaurarPadrao() {
    setOrdemArraste(null);
    setArrastando(null);
    onChange(layoutPadrao());
  }

  return (
    <Drawer
      open={open}
      title="Personalizar Home"
      description="Arraste pela alcinha para reordenar. Use o interruptor para mostrar ou ocultar um card."
      onClose={onClose}
      footer={
        <Button variant="ghost" size="sm" onClick={restaurarPadrao}>
          <RotateCcw size={14} aria-hidden="true" />
          Restaurar padrão
        </Button>
      }
    >
      <ul className="space-y-2">
        {ordemExibida.map((id) => {
          const card = cardsPorId.get(id);
          if (!card) return null;
          const oculto = layout.ocultos.includes(id);

          return (
            <li
              key={id}
              onDragOver={onDragOverItem(id)}
              onDrop={onDrop}
              className={`flex items-center gap-3 rounded-md border border-border-subtle bg-surface-2 p-3 transition-opacity ${
                arrastando === id ? "opacity-50" : ""
              } ${oculto ? "opacity-60" : ""}`}
            >
              <span
                draggable
                onDragStart={onDragStart(id)}
                onDragEnd={confirmarArraste}
                role="button"
                tabIndex={-1}
                aria-label={`Arrastar para reordenar ${card.label}`}
                className="shrink-0 cursor-grab text-text-tertiary active:cursor-grabbing"
              >
                <GripVertical size={16} aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1 text-sm font-medium text-text-primary">{card.label}</span>
              <Switch
                checked={!oculto}
                onCheckedChange={() => alternarVisibilidade(id)}
                aria-label={`Mostrar card ${card.label}`}
              />
            </li>
          );
        })}
      </ul>
    </Drawer>
  );
}
