import { useEffect, useState } from "react";
import type { MetaRead } from "../types/meta";

function chaveCelebracao(metaId: number): string {
  return `meta-celebrada-${metaId}`;
}

/** ~1.6s — duração total da animação em `MetaCelebracao` (confete + selo),
 * mantida aqui porque é o hook quem decide quando desligar `celebrando`. */
const DURACAO_CELEBRACAO_MS = 1600;

/**
 * Decide SE uma Meta deve disparar a celebração — uma ÚNICA VEZ por Meta, na
 * primeira vez que o cliente observa `concluida_em` preenchido (Refinamento
 * de Metas, seção 4). `concluida_em` é fato de negócio persistido pelo
 * backend e nunca é desfeito (mesmo que o progresso caia depois); "já
 * mostrei a celebração para esta Meta neste navegador" é puro estado de
 * apresentação, guardado em `localStorage` — nunca no backend, nunca
 * reenviado como regra de negócio (ver
 * docs/analise-arquitetural-metas-refinamento.md, seção 4.2).
 *
 * Deliberadamente simples (sem sincronizar entre abas/dispositivos): se o
 * usuário limpar o `localStorage` ou abrir em outro navegador, a celebração
 * pode reaparecer — consequência aceita do design (é só um momento bonito,
 * nunca uma fonte de verdade), não um bug a esconder com mais estado.
 */
export function useCelebracaoMeta(meta: MetaRead): boolean {
  const [celebrando, setCelebrando] = useState(false);

  useEffect(() => {
    if (!meta.concluida_em) return;

    const chave = chaveCelebracao(meta.id);
    let jaCelebrada = true;
    try {
      jaCelebrada = localStorage.getItem(chave) != null;
      if (!jaCelebrada) localStorage.setItem(chave, "1");
    } catch {
      // localStorage indisponível (modo privado/restrito) — não celebra de
      // novo a cada render, mas também não quebra a tela por causa disso.
      return;
    }
    if (jaCelebrada) return;

    setCelebrando(true);
    const timer = setTimeout(() => setCelebrando(false), DURACAO_CELEBRACAO_MS);
    return () => clearTimeout(timer);
  }, [meta.id, meta.concluida_em]);

  return celebrando;
}
