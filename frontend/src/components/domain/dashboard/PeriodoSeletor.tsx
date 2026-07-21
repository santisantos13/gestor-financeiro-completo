import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "../../ui/Button";
import { MesAnoSeletor } from "../calendario/MesAnoSeletor";

export interface PeriodoSeletorProps {
  ano: number;
  mes: number;
  onChange: (ano: number, mes: number) => void;
}

/** Navegação de mês anterior/próximo + `MesAnoSeletor` (popup de ano/mês) no
 * meio — `resumo`/`visao-mensal` só aceitam `ano`+`mes` únicos, sem
 * seletor de range (fora de escopo, docs/analise-arquitetural-dashboard.md,
 * seção 4). Mesma composição já usada em `CalendarioPage` (Etapa de
 * Refinamento UX/UI, item 6): o rótulo estático virou um botão que abre um
 * stepper de ano + grid dos 12 meses, permitindo pular direto para um mês
 * distante em vez de clicar dezenas de vezes nas setas — pedido do usuário
 * para reaproveitar esse padrão em toda navegação por data do app. Usado
 * tanto pelo Dashboard quanto por `TransacoesPage`, então ambos ganham o
 * mesmo popup automaticamente. */
export function PeriodoSeletor({ ano, mes, onChange }: PeriodoSeletorProps) {
  function anterior() {
    if (mes === 1) onChange(ano - 1, 12);
    else onChange(ano, mes - 1);
  }

  function proximo() {
    if (mes === 12) onChange(ano + 1, 1);
    else onChange(ano, mes + 1);
  }

  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="sm" onClick={anterior} aria-label="Mês anterior">
        <ChevronLeft size={16} aria-hidden="true" />
      </Button>
      <MesAnoSeletor ano={ano} mes={mes} onSelecionar={onChange} className="min-w-[8rem] justify-center" />
      <Button variant="ghost" size="sm" onClick={proximo} aria-label="Próximo mês">
        <ChevronRight size={16} aria-hidden="true" />
      </Button>
    </div>
  );
}
