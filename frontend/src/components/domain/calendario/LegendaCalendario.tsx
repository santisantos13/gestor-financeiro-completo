import { COR_DOT_POR_CATEGORIA, LABEL_CATEGORIA_EVENTO, ORDEM_LEGENDA_CALENDARIO } from "../../../lib/calendarioCategorias";

/** Legenda fixa dos dots do `CalendarioMensal` — sempre visível (o usuário
 * não deveria precisar adivinhar o que uma cor significa). Ver
 * docs/analise-arquitetural-transferencias-frontend.md. */
export function LegendaCalendario() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {ORDEM_LEGENDA_CALENDARIO.map((categoria) => (
        <span key={categoria} className="flex items-center gap-1.5 text-micro text-text-tertiary">
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${COR_DOT_POR_CATEGORIA[categoria]}`} aria-hidden="true" />
          {LABEL_CATEGORIA_EVENTO[categoria]}
        </span>
      ))}
    </div>
  );
}
