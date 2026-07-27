/**
 * Vocabulário de exibição de Alerta — centralizado aqui para
 * `AlertasDrawer`/`AlertaFormDialog` nunca divergirem sobre rótulo/ícone/
 * texto de regra de um mesmo `tipo`.
 *
 * `ENTIDADE_DO_TIPO_ALERTA` espelha `AlertaService._ENTIDADE_DO_TIPO`
 * (backend) só para decidir ÍCONE (via `ICONE_POR_ORIGEM`, já existente) —
 * nunca enviado ao backend (`entidade_tipo` não existe em nenhum schema,
 * ver docstring de `types/alerta.ts`).
 */
import type { LucideIcon } from "lucide-react";
import { ICONE_POR_ORIGEM } from "./origemNavegacao";
import { formatMoney, formatPercent } from "../utils/format";
import type { AlertaCondicao, TipoAlerta } from "../types/alerta";
import type { TipoEntidadeReferenciavel } from "../types/enums";

export const TIPO_ALERTA_LABEL: Record<TipoAlerta, string> = {
  LIMITE_CARTAO: "Limite do cartão",
  VENCIMENTO_FATURA: "Vencimento de fatura",
  VENCIMENTO_CONTA_RECORRENTE: "Vencimento de conta recorrente",
  META_ATINGIDA: "Meta atingida",
  SALDO_BAIXO: "Saldo baixo",
};

const ENTIDADE_DO_TIPO_ALERTA: Record<TipoAlerta, TipoEntidadeReferenciavel> = {
  LIMITE_CARTAO: "CARTAO",
  VENCIMENTO_FATURA: "CARTAO",
  VENCIMENTO_CONTA_RECORRENTE: "CONTA_RECORRENTE",
  META_ATINGIDA: "META",
  SALDO_BAIXO: "CONTA",
};

export function iconePorTipoAlerta(tipo: TipoAlerta): LucideIcon {
  return ICONE_POR_ORIGEM[ENTIDADE_DO_TIPO_ALERTA[tipo]];
}

const DIAS_ANTES_PADRAO = 3;

/** Descreve a REGRA em si (nunca o resultado da avaliação — isso é
 * `alerta.mensagem`, calculado pelo backend). Usada tanto na lista (para
 * alertas ainda não disparados/pausados, que não têm `mensagem`) quanto no
 * formulário (preview antes de salvar). */
export function descreverCondicaoAlerta(tipo: TipoAlerta, condicao: AlertaCondicao): string {
  switch (tipo) {
    case "LIMITE_CARTAO": {
      const percentual = condicao && "limite_percentual" in condicao ? condicao.limite_percentual : null;
      return percentual != null ? `Avisa ao atingir ${formatPercent(percentual)} do limite.` : "Avisa ao atingir o limite configurado.";
    }
    case "VENCIMENTO_FATURA": {
      const dias = condicao && "dias_antes" in condicao ? condicao.dias_antes : DIAS_ANTES_PADRAO;
      return `Avisa ${dias} dia(s) antes do vencimento da fatura.`;
    }
    case "VENCIMENTO_CONTA_RECORRENTE": {
      const dias = condicao && "dias_antes" in condicao ? condicao.dias_antes : DIAS_ANTES_PADRAO;
      return `Avisa ${dias} dia(s) antes do vencimento.`;
    }
    case "META_ATINGIDA":
      return "Avisa quando a meta for concluída.";
    case "SALDO_BAIXO": {
      const valorMinimo = condicao && "valor_minimo" in condicao ? condicao.valor_minimo : null;
      return valorMinimo != null ? `Avisa quando o saldo ficar abaixo de ${formatMoney(valorMinimo)}.` : "Avisa quando o saldo ficar baixo.";
    }
    default:
      return "";
  }
}
