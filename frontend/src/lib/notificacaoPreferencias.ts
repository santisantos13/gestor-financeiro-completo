/**
 * Preferências de Notificações (Configurações → Notificações) — um
 * interruptor por `TipoAlerta` que decide se aquele TIPO conta para o
 * contador do sino no `Header`. Puramente uma preferência de EXIBIÇÃO
 * local (`localStorage`, mesmo padrão de `lib/accentThemes.ts`), nunca
 * enviada ao backend: silenciar "Vencimento de fatura" aqui não pausa
 * nenhum `Alerta` de verdade (isso já existe, é o `ativo` de cada regra,
 * ver `AlertasDrawer`) — só filtra o que gera aquele "ping" no sino, para
 * quem quer ver TODOS os alertas na lista mas não quer ser interrompido
 * por uma categoria específica.
 *
 * `AlertasDrawer` continua mostrando TODOS os alertas (silenciados ou não)
 * — silenciar não é o mesmo que pausar/excluir a regra.
 */
import type { TipoAlerta } from "../types/alerta";

export type PreferenciasNotificacao = Record<TipoAlerta, boolean>;

const TODOS_OS_TIPOS: TipoAlerta[] = [
  "LIMITE_CARTAO",
  "VENCIMENTO_FATURA",
  "VENCIMENTO_CONTA_RECORRENTE",
  "META_ATINGIDA",
  "SALDO_BAIXO",
];

/** Padrão: tudo habilitado - silenciar é uma escolha explícita do usuário,
 * nunca o estado inicial. */
export const PREFERENCIAS_PADRAO: PreferenciasNotificacao = {
  LIMITE_CARTAO: true,
  VENCIMENTO_FATURA: true,
  VENCIMENTO_CONTA_RECORRENTE: true,
  META_ATINGIDA: true,
  SALDO_BAIXO: true,
};

const STORAGE_KEY = "financas:notificacoes";

function ehRegistroValido(valor: unknown): valor is Partial<PreferenciasNotificacao> {
  return typeof valor === "object" && valor !== null;
}

export function lerPreferenciasSalvas(): PreferenciasNotificacao {
  if (typeof window === "undefined") return PREFERENCIAS_PADRAO;
  try {
    const bruto = window.localStorage.getItem(STORAGE_KEY);
    if (!bruto) return PREFERENCIAS_PADRAO;
    const salvo: unknown = JSON.parse(bruto);
    if (!ehRegistroValido(salvo)) return PREFERENCIAS_PADRAO;
    // Faz merge com o padrão (nunca confia 100% no valor salvo) - um `tipo`
    // novo adicionado depois desta preferência já existir salva no
    // navegador do usuário nasce habilitado, nunca `undefined`.
    const resultado = { ...PREFERENCIAS_PADRAO };
    for (const tipo of TODOS_OS_TIPOS) {
      if (typeof salvo[tipo] === "boolean") resultado[tipo] = salvo[tipo] as boolean;
    }
    return resultado;
  } catch {
    return PREFERENCIAS_PADRAO;
  }
}

export function gravarPreferencias(preferencias: PreferenciasNotificacao): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferencias));
  } catch {
    // localStorage indisponível - a preferência ainda vale para esta sessão
    // (mesma degradação silenciosa de accentThemes.ts/ThemeContext).
  }
}
