import { useMemo } from "react";
import { ArrowDownCircle, ArrowUpCircle, CalendarClock, Flame, Scale } from "lucide-react";
import { Card } from "../../ui/Card";
import { formatDate } from "../../../utils/date";
import { formatMoney } from "../../../utils/format";
import type { CategoriaEventoCalendario } from "../../../types/enums";
import type { EventoCalendario } from "../../../types/centralFinanceira";

/** Categorias que representam dinheiro efetivamente SAINDO da conta (ou já
 * comprometido a sair) num dado mês — usadas por "Despesas previstas"
 * abaixo. Bug real corrigido em 2026-07-22: o cálculo original só olhava
 * `categoria === "DESPESA"`, deixando de fora Financiamento/Empréstimo
 * (categorias próprias desde 2026-07-21, ver `lib/calendarioCategorias.ts`)
 * inteiramente — quem tinha parcela de financiamento no mês via "Despesas
 * previstas" abaixo do valor real. FATURA_VENCIMENTO entra pelo mesmo
 * motivo (é o evento que representa a fatura do cartão saindo da conta —
 * `calendario_financeiro` nunca lista as compras individuais no cartão,
 * `apenas_conta=True`, só o evento de Fatura). FATURA_FECHAMENTO fica de
 * fora de propósito — é só informativo (fechamento do ciclo), o dinheiro
 * ainda não saiu; somar os dois quando caem no mesmo mês contaria a MESMA
 * fatura em dobro. */
const CATEGORIAS_DE_DESPESA: ReadonlySet<CategoriaEventoCalendario> = new Set([
  "DESPESA",
  "FINANCIAMENTO",
  "EMPRESTIMO",
  "FATURA_VENCIMENTO",
]);

export interface ResumoMesCalendarioProps {
  eventos: EventoCalendario[];
}

interface Indicador {
  icon: typeof ArrowUpCircle;
  label: string;
  valor: string;
  tone: string;
}

/**
 * Painel de resumo do mês — tudo derivado client-side dos MESMOS `eventos`
 * já carregados por `/central-financeira/calendario` (nenhuma chamada
 * nova). Ver docs/analise-arquitetural-transferencias-frontend.md.
 *
 * "Saldo previsto do mês" é deliberadamente rotulado "Fluxo do mês"
 * (receitas − despesas dos eventos do mês) — NÃO é o saldo bancário
 * projetado das contas (que dependeria de somar `saldo_atual` atual +
 * eventos futuros, uma conta bem mais complexa e fora do escopo desta
 * etapa). Rotular com precisão evita prometer uma informação que não é
 * essa.
 */
export function ResumoMesCalendario({ eventos }: ResumoMesCalendarioProps) {
  const hojeIso = useMemo(() => {
    const hoje = new Date();
    return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
  }, []);

  const dados = useMemo(() => {
    const receitas = eventos.filter((e) => e.categoria === "RECEITA");
    const despesas = eventos.filter((e) => CATEGORIAS_DE_DESPESA.has(e.categoria));
    const totalReceitas = receitas.reduce((soma, e) => soma + Number(e.valor), 0);
    const totalDespesas = despesas.reduce((soma, e) => soma + Number(e.valor), 0);

    const contagemPorDia = new Map<string, number>();
    for (const evento of eventos) {
      contagemPorDia.set(evento.data, (contagemPorDia.get(evento.data) ?? 0) + 1);
    }
    let diaMaisMovimentado: { data: string; total: number } | null = null;
    for (const [data, total] of contagemPorDia) {
      if (!diaMaisMovimentado || total > diaMaisMovimentado.total) diaMaisMovimentado = { data, total };
    }

    const proximoVencimento = eventos
      .filter((e) => e.categoria === "FATURA_VENCIMENTO" && e.data >= hojeIso)
      .sort((a, b) => a.data.localeCompare(b.data))[0];

    const proximaEntrada = receitas.filter((e) => e.data >= hojeIso).sort((a, b) => a.data.localeCompare(b.data))[0];

    return { totalReceitas, totalDespesas, diaMaisMovimentado, proximoVencimento, proximaEntrada };
  }, [eventos, hojeIso]);

  const fluxoMes = dados.totalReceitas - dados.totalDespesas;

  const indicadores: Indicador[] = [
    { icon: ArrowUpCircle, label: "Receitas previstas", valor: formatMoney(dados.totalReceitas), tone: "text-positive" },
    { icon: ArrowDownCircle, label: "Despesas previstas", valor: formatMoney(dados.totalDespesas), tone: "text-negative" },
    {
      icon: Scale,
      label: "Fluxo do mês",
      valor: `${fluxoMes >= 0 ? "+" : ""}${formatMoney(fluxoMes)}`,
      tone: fluxoMes >= 0 ? "text-positive" : "text-negative",
    },
  ];

  return (
    <Card className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {indicadores.map((indicador) => (
          <div key={indicador.label} className="flex items-center gap-2.5">
            <indicador.icon size={18} className={`shrink-0 ${indicador.tone}`} aria-hidden="true" />
            <div className="min-w-0">
              <p className="text-micro text-text-tertiary">{indicador.label}</p>
              <p className={`tabular font-semibold ${indicador.tone}`}>{indicador.valor}</p>
            </div>
          </div>
        ))}
      </div>

      {(dados.diaMaisMovimentado || dados.proximoVencimento || dados.proximaEntrada) && (
        <div className="grid grid-cols-1 gap-2 border-t border-border-subtle pt-3 text-sm sm:grid-cols-3">
          {dados.diaMaisMovimentado && dados.diaMaisMovimentado.total > 1 && (
            <div className="flex items-center gap-2 text-text-secondary">
              <Flame size={14} className="shrink-0 text-warning" aria-hidden="true" />
              <span>
                Dia mais movimentado: <strong className="text-text-primary">{formatDate(dados.diaMaisMovimentado.data)}</strong> ({dados.diaMaisMovimentado.total} eventos)
              </span>
            </div>
          )}
          {dados.proximoVencimento && (
            <div className="flex items-center gap-2 text-text-secondary">
              <CalendarClock size={14} className="shrink-0 text-warning" aria-hidden="true" />
              <span>
                Próximo vencimento: <strong className="text-text-primary">{formatDate(dados.proximoVencimento.data)}</strong>
              </span>
            </div>
          )}
          {dados.proximaEntrada && (
            <div className="flex items-center gap-2 text-text-secondary">
              <ArrowUpCircle size={14} className="shrink-0 text-positive" aria-hidden="true" />
              <span>
                Próxima entrada: <strong className="text-text-primary">{formatDate(dados.proximaEntrada.data)}</strong>
              </span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
