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
 * Drawer de personalização do Dashboard (Sprint de Refinamento Premium,
 * item 15) — reordenar (drag-and-drop nativo, sem biblioteca) e
 * mostrar/ocultar os cards do Bento Grid. Mesmo componente de overlay
 * tier 2 (`Drawer`) já usado em Fatura/Financiamento; nada de novo em
 * termos de padrão visual.
 *
 * Drag-and-drop com a API nativa do HTML5 (`draggable`) — deliberado, para
 * não adicionar uma biblioteca de DnD só por causa de uma preferência
 * cosmética (ver decisão em
 * docs/analise-arquitetural-sprint-refinamento-premium.md, seção 15).
 */
export function DashboardCustomizeDrawer({ open, layout, onChange, onClose }: DashboardCustomizeDrawerProps) {
  const [arrastando, setArrastando] = useState<DashboardCardId | null>(null);
  const cardsPorId = new Map(CARDS_PERSONALIZAVEIS.map((c) => [c.id, c]));

  function onDragStart(id: DashboardCardId) {
    return (event: DragEvent<HTMLLIElement>) => {
      setArrastando(id);
      event.dataTransfer.effectAllowed = "move";
    };
  }

  function onDragOver(id: DashboardCardId) {
    return (event: DragEvent<HTMLLIElement>) => {
      event.preventDefault();
      if (!arrastando || arrastando === id) return;

      const indiceOrigem = layout.ordem.indexOf(arrastando);
      const indiceDestino = layout.ordem.indexOf(id);
      if (indiceOrigem === -1 || indiceDestino === -1) return;

      const novaOrdem = [...layout.ordem];
      novaOrdem.splice(indiceOrigem, 1);
      novaOrdem.splice(indiceDestino, 0, arrastando);
      onChange({ ...layout, ordem: novaOrdem });
    };
  }

  function onDragEnd() {
    setArrastando(null);
  }

  function alternarVisibilidade(id: DashboardCardId) {
    const oculto = layout.ocultos.includes(id);
    onChange({
      ...layout,
      ocultos: oculto ? layout.ocultos.filter((atual) => atual !== id) : [...layout.ocultos, id],
    });
  }

  function restaurarPadrao() {
    onChange(layoutPadrao());
  }

  return (
    <Drawer
      open={open}
      title="Personalizar Dashboard"
      description="Arraste para reordenar. Use o interruptor para mostrar ou ocultar um card."
      onClose={onClose}
      footer={
        <Button variant="ghost" size="sm" onClick={restaurarPadrao}>
          <RotateCcw size={14} aria-hidden="true" />
          Restaurar padrão
        </Button>
      }
    >
      <ul className="space-y-2">
        {layout.ordem.map((id) => {
          const card = cardsPorId.get(id);
          if (!card) return null;
          const oculto = layout.ocultos.includes(id);

          return (
            <li
              key={id}
              draggable
              onDragStart={onDragStart(id)}
              onDragOver={onDragOver(id)}
              onDragEnd={onDragEnd}
              className={`flex items-center gap-3 rounded-md border border-border-subtle bg-surface-2 p-3 transition-opacity ${
                arrastando === id ? "opacity-50" : ""
              } ${oculto ? "opacity-60" : ""}`}
            >
              <GripVertical
                size={16}
                className="shrink-0 cursor-grab text-text-tertiary active:cursor-grabbing"
                aria-hidden="true"
              />
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
