import { type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** Estrutura fixa (ícone + título + descrição + ação opcional) — nunca um
 * texto solto "nenhum resultado". design-system.md, seção 20.1. */
export function EmptyState({ icon: Icon, title, description, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center gap-2 py-8 text-center ${className}`}>
      <Icon size={28} className="text-text-tertiary" aria-hidden="true" strokeWidth={1.5} />
      <p className="text-h3 font-semibold text-text-primary">{title}</p>
      {description && <p className="max-w-xs text-sm text-text-secondary">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
