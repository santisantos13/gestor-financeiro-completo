import { Fragment } from "react";

/**
 * Destaca o primeiro trecho de `texto` que casa com `query` (case-
 * insensitive) envolvendo-o num `<mark>` estilizado — usado por
 * `RichPicker`/`SearchSelect` para a busca ficar mais fácil de escanear
 * visualmente (docs/analise-arquitetural-refinamento-pickers-performance.md,
 * seção 4). Função pura de apresentação: nunca decide o que é ou não um
 * resultado válido (isso continua sendo o filtro já existente de cada
 * componente), só decora o texto que já passou no filtro.
 */
export function destacarTrecho(texto: string, query: string) {
  const termo = query.trim();
  if (!termo) return texto;

  const indice = texto.toLowerCase().indexOf(termo.toLowerCase());
  if (indice === -1) return texto;

  const antes = texto.slice(0, indice);
  const trecho = texto.slice(indice, indice + termo.length);
  const depois = texto.slice(indice + termo.length);

  return (
    <Fragment>
      {antes}
      <mark className="rounded-[2px] bg-accent-subtle text-accent">{trecho}</mark>
      {depois}
    </Fragment>
  );
}
