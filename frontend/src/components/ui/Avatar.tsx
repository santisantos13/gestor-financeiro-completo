export interface AvatarProps {
  nome: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<AvatarProps["size"]>, string> = {
  sm: "h-6 w-6 text-micro",
  md: "h-8 w-8 text-caption",
  lg: "h-11 w-11 text-body",
};

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/);
  const primeira = partes[0]?.[0] ?? "";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}

/** Círculo com iniciais — não há upload de foto no backend hoje, então
 * sempre iniciais. design-system.md, seção 14. */
export function Avatar({ nome, size = "md", className = "" }: AvatarProps) {
  return (
    <div
      className={`flex items-center justify-center rounded-full bg-surface-3 font-medium text-text-secondary ${SIZE_CLASSES[size]} ${className}`}
      title={nome}
      aria-hidden="true"
    >
      {iniciais(nome)}
    </div>
  );
}
