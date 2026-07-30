import { useEffect, useRef, useState } from "react";
import { useIsFetching } from "@tanstack/react-query";
import { Spinner } from "../ui/Spinner";

/** Quanto tempo de fetch contínuo até avisar sobre cold start (ver
 * docstring abaixo) — curto o bastante para aparecer antes do usuário
 * desistir, longo o bastante para nunca piscar numa carga normal (rede
 * boa: a Home inteira busca ~10 endpoints em paralelo e normalmente
 * termina bem antes disso). */
const ATRASO_MS = 6_000;

/**
 * Aviso de "servidor acordando" — investigação de 2026-07-30 (usuário
 * reportou Home/Calendário "carregando infinito"): não era bug de código,
 * era o cold start já documentado em docs/analise-arquitetural-deploy-
 * prealfa.md (Render free tier dorme após 15 min sem tráfego) combinado
 * com o Skeleton (design-system.md, 20.3) sendo escuro sobre fundo escuro
 * — visualmente indistinguível de uma tela travada quando a espera passa
 * de alguns segundos. Confirmado via Chrome DevTools que todas as
 * requisições completam (200) eventualmente, só que em série conforme o
 * pool de conexão do Postgres gerenciado (Supabase free tier) esquenta.
 *
 * `useIsFetching()` conta quantas queries do React Query estão em voo
 * agora (soma de toda a árvore, não só da página atual) — se ficar > 0 por
 * mais de `ATRASO_MS` seguidos, mostra esta faixa. Nunca aparece numa
 * carga normal (curta); em cold start, aparece e explica o que está
 * acontecendo em vez de deixar a tela parecer quebrada.
 */
export function ColdStartBanner() {
  const isFetching = useIsFetching();
  const [mostrar, setMostrar] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isFetching > 0) {
      if (timeoutRef.current === null) {
        timeoutRef.current = setTimeout(() => setMostrar(true), ATRASO_MS);
      }
    } else {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      setMostrar(false);
    }
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isFetching]);

  if (!mostrar) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 border-b border-border-subtle bg-surface-2 px-4 py-2 text-caption text-text-secondary"
    >
      <Spinner size="sm" tone="tertiary" />
      Conectando ao servidor — pode levar até 1 minuto após um tempo sem uso (plano gratuito).
    </div>
  );
}
