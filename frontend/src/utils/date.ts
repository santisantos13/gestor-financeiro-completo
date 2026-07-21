/**
 * Formatação/aritmética de data para exibição — ver
 * docs/analise-arquitetural-dashboard.md, seção 7.4. `proximaOcorrenciaDoDia`
 * é aritmética de calendário pura (não financeira): converte um dia-do-mês
 * já autoritativo (`Cartao.dia_fechamento`/`dia_vencimento`) na próxima data
 * de calendário em que ele ocorre, só para exibição.
 */

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** `iso` no formato `AAAA-MM-DD` (como o backend serializa `date`). Evita
 * `new Date(iso)` puro porque isso interpreta a string como UTC meia-noite,
 * podendo exibir o dia errado dependendo do fuso do navegador — construímos
 * a data a partir dos componentes explicitamente. */
export function formatDate(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  if (!ano || !mes || !dia) return iso;
  return dateFormatter.format(new Date(ano, mes - 1, dia));
}

const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** `iso` é um datetime completo (com hora), diferente de `formatDate` acima
 * (só `AAAA-MM-DD`) — usado pela Central de Atividades
 * (Sprint de Refinamento Premium, item 17), onde `data_hora` sempre inclui
 * hora (mesmo quando o backend normalizou uma Meta concluída para meia-noite). */
export function formatDateTime(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  return dateTimeFormatter.format(data);
}

const NOMES_MES = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
] as const;

export function nomeMes(mes: number): string {
  return NOMES_MES[mes - 1] ?? "";
}

function ultimoDiaDoMes(ano: number, mes: number): number {
  return new Date(ano, mes + 1, 0).getDate();
}

function startOfDay(data: Date): Date {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate());
}

/** Dado um dia-do-mês (1-31), devolve a próxima data de calendário (hoje
 * incluso) em que esse dia ocorre — usa o mês corrente se o dia ainda não
 * passou, senão o próximo mês. Dias que não existem no mês (ex. 31 em
 * fevereiro) são presos (clamped) ao último dia real do mês. */
export function proximaOcorrenciaDoDia(dia: number, referencia: Date = new Date()): Date {
  const ano = referencia.getFullYear();
  const mes = referencia.getMonth();
  const diaClamp = Math.min(dia, ultimoDiaDoMes(ano, mes));
  const candidato = new Date(ano, mes, diaClamp);

  if (candidato >= startOfDay(referencia)) {
    return candidato;
  }

  const proximoMes = mes + 1;
  const diaProximoClamp = Math.min(dia, ultimoDiaDoMes(ano, proximoMes));
  return new Date(ano, proximoMes, diaProximoClamp);
}

/** Dias entre hoje e uma data futura (arredondado, nunca negativo). Usado
 * para "fecha em X dias" / "vence em X dias" no `CartoesCard`. */
export function diasAte(data: Date, referencia: Date = new Date()): number {
  const diffMs = startOfDay(data).getTime() - startOfDay(referencia).getTime();
  return Math.max(0, Math.round(diffMs / 86_400_000));
}

function paraIso(ano: number, mes: number, dia: number): string {
  return `${String(ano).padStart(4, "0")}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
}

/** Primeiro e último dia (ISO `AAAA-MM-DD`) de um mês — usado por
 * `TransacoesPage` para converter `PeriodoSeletor` (`ano`+`mes`) nos
 * parâmetros `data_inicio`/`data_fim` que `GET /transacoes` de fato aceita
 * (docs/analise-arquitetural-transacao-frontend.md, seção 2). `mes` é
 * 1-indexado (janeiro = 1), mesma convenção de `nomeMes`/`PeriodoSeletor`. */
export function intervaloDoMes(ano: number, mes: number): { inicio: string; fim: string } {
  return {
    inicio: paraIso(ano, mes, 1),
    fim: paraIso(ano, mes, ultimoDiaDoMes(ano, mes - 1)),
  };
}

export interface DiaGradeCalendario {
  iso: string;
  diaDoMes: number;
  noMesAtual: boolean;
  hoje: boolean;
}

/** Monta a grade completa (semanas de 7 dias, começando no domingo) do
 * Calendário Financeiro — inclui os dias de "sobra" do mês anterior/
 * seguinte para completar a primeira/última semana (`noMesAtual: false`),
 * mesmo padrão visual de Google Calendar/Notion Calendar (dias fora do mês
 * aparecem esmaecidos, nunca escondidos — evita uma grade com buracos).
 * `mes` é 1-indexado, mesma convenção de `nomeMes`/`intervaloDoMes`. */
export function construirGradeMensal(ano: number, mes: number, hoje: Date = new Date()): DiaGradeCalendario[] {
  const primeiroDiaMes = new Date(ano, mes - 1, 1);
  const ultimoDiaMes = new Date(ano, mes, 0);
  const inicioGrade = new Date(primeiroDiaMes);
  inicioGrade.setDate(inicioGrade.getDate() - primeiroDiaMes.getDay());
  const fimGrade = new Date(ultimoDiaMes);
  fimGrade.setDate(fimGrade.getDate() + (6 - ultimoDiaMes.getDay()));

  const hojeInicio = startOfDay(hoje);
  const dias: DiaGradeCalendario[] = [];
  const cursor = new Date(inicioGrade);
  while (cursor <= fimGrade) {
    dias.push({
      iso: paraIso(cursor.getFullYear(), cursor.getMonth() + 1, cursor.getDate()),
      diaDoMes: cursor.getDate(),
      noMesAtual: cursor.getMonth() === mes - 1,
      hoje: startOfDay(cursor).getTime() === hojeInicio.getTime(),
    });
    cursor.setDate(cursor.getDate() + 1);
  }
  return dias;
}

/** Diferença COM sinal em dias entre hoje e uma data ISO (`AAAA-MM-DD`) —
 * positivo = no futuro, negativo = no passado. Diferente de `diasAte`
 * (que sempre clampa em 0), usado onde o "atraso" é o próprio dado a
 * comunicar (`ProximaFaturaCard`/`CartaoResumoCard`, revisão de UX de
 * Cartões — uma fatura `ATRASADA` precisa dizer "há quantos dias", não
 * "vence em 0 dias"). Mesma construção por componentes de `formatDate`
 * (evita o fuso horário interpretar a string como UTC meia-noite). */
export function diferencaEmDias(iso: string, referencia: Date = new Date()): number {
  const [ano, mes, dia] = iso.split("-").map(Number);
  const data = new Date(ano, mes - 1, dia);
  const diffMs = startOfDay(data).getTime() - startOfDay(referencia).getTime();
  return Math.round(diffMs / 86_400_000);
}
