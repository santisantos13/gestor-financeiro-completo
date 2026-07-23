/**
 * Ponte não-React para o formato de data preferido — mesmo raciocínio de
 * `api/tokenStore.ts`: `utils/date.ts` é usado por DEZENAS de componentes
 * como função utilitária pura (não um hook), fora de qualquer árvore React,
 * então não pode `useContext`. `PreferenciasContext` é o ÚNICO escritor
 * (ver docs/analise-arquitetural-configuracoes.md, seção sobre
 * Preferências); tudo mais só lê via `getFormatoData()`.
 *
 * Diferente do tema (que reaplica instantaneamente via `data-theme` no
 * `<html>`), mudar o formato de data exigiria que TODO componente que chama
 * `formatDate`/`formatDateTime` reagisse a uma mudança de contexto — um
 * refactor bem maior que o escopo desta etapa. Solução deliberadamente mais
 * simples: `PreferenciasContext.setFormatoData` grava aqui + localStorage e
 * recarrega a página (`window.location.reload()`), garantindo que toda
 * chamada futura de `formatDate` (já remontada do zero) usa o valor novo -
 * sem precisar de reatividade fina espalhada pelo app.
 */
export type FormatoData = "DD/MM/AAAA" | "AAAA-MM-DD" | "MM/DD/AAAA";

export const FORMATO_DATA_PADRAO: FormatoData = "DD/MM/AAAA";
const STORAGE_KEY = "financas:formato_data";

function ehFormatoValido(valor: string | null): valor is FormatoData {
  return valor === "DD/MM/AAAA" || valor === "AAAA-MM-DD" || valor === "MM/DD/AAAA";
}

function lerFormatoSalvo(): FormatoData {
  if (typeof window === "undefined") return FORMATO_DATA_PADRAO;
  try {
    const salvo = window.localStorage.getItem(STORAGE_KEY);
    return ehFormatoValido(salvo) ? salvo : FORMATO_DATA_PADRAO;
  } catch {
    return FORMATO_DATA_PADRAO;
  }
}

let formatoDataAtual: FormatoData = lerFormatoSalvo();

export function getFormatoData(): FormatoData {
  return formatoDataAtual;
}

/** Só `PreferenciasContext` deveria chamar isso - qualquer outro lugar quer
 * `getFormatoData()` (leitura) ou o `setFormatoData` exposto por
 * `usePreferencias()` (que já cuida de persistir e recarregar). */
export function setFormatoData(formato: FormatoData): void {
  formatoDataAtual = formato;
  try {
    window.localStorage.setItem(STORAGE_KEY, formato);
  } catch {
    // localStorage indisponível - a preferência ainda vale para esta sessão.
  }
}
