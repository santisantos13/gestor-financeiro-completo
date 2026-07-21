import { useState, type ComponentType } from "react";
import { CreditCard, Settings2 } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useIndicadoresGeraisQuery } from "../../hooks/useCentralFinanceiraQueries";
import { Skeleton } from "../../components/ui/Skeleton";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { Button } from "../../components/ui/Button";
import { DashboardOnboarding } from "../../components/domain/dashboard/DashboardOnboarding";
import { ProximoPassoCard } from "../../components/domain/dashboard/ProximoPassoCard";
import { PeriodoSeletor } from "../../components/domain/dashboard/PeriodoSeletor";
import { ResumoFinanceiroSection } from "../../components/domain/dashboard/ResumoFinanceiroSection";
import { IndicadoresStrip } from "../../components/domain/dashboard/IndicadoresStrip";
import { ContasCartoesCard } from "../../components/domain/dashboard/ContasCartoesCard";
import { TransacoesRecentesCard } from "../../components/domain/dashboard/TransacoesRecentesCard";
import { FaturasCard } from "../../components/domain/dashboard/FaturasCard";
import { FinanciamentosCard } from "../../components/domain/dashboard/FinanciamentosCard";
import { EmprestimosCard } from "../../components/domain/dashboard/EmprestimosCard";
import { MetasCard } from "../../components/domain/dashboard/MetasCard";
import { HojeCard } from "../../components/domain/dashboard/HojeCard";
import { DashboardCustomizeDrawer } from "../../components/domain/dashboard/DashboardCustomizeDrawer";
import { carregarLayoutDashboard, salvarLayoutDashboard, type DashboardCardId, type LayoutDashboard } from "../../lib/dashboardLayout";

/** Mapa id → componente dos cards personalizáveis (Sprint de Refinamento
 * Premium, item 15) - único lugar que precisa mudar ao adicionar um card
 * novo à personalização (junto de `lib/dashboardLayout.ts`). */
const COMPONENTE_POR_CARD: Record<DashboardCardId, ComponentType> = {
  faturas: FaturasCard,
  financiamentos: FinanciamentosCard,
  emprestimos: EmprestimosCard,
  metas: MetasCard,
};

/**
 * Orquestra o layout do Dashboard (Bento Grid, docs/analise-arquitetural-dashboard.md
 * seção 8) e compõe os widgets — nunca chama `httpClient`/serviços
 * diretamente, nunca guarda estado de loading/erro/dado de nenhuma seção
 * (seção 16.1, diretriz aprovada explicitamente: "crescer sem
 * refatoração"). Toda busca mora nos hooks de
 * `hooks/useCentralFinanceiraQueries.ts`; cada seção abaixo é um componente
 * independente e reutilizável — adicionar uma seção nova no futuro é criar
 * um componente + hook novo, sem tocar nos existentes.
 */
export function DashboardPage() {
  const { usuario } = useAuth();
  const hoje = new Date();
  const [periodo, setPeriodo] = useState({ ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 });
  const [layout, setLayout] = useState<LayoutDashboard>(carregarLayoutDashboard);
  const [personalizando, setPersonalizando] = useState(false);

  function atualizarLayout(novoLayout: LayoutDashboard) {
    setLayout(novoLayout);
    salvarLayoutDashboard(novoLayout);
  }

  // Gate de onboarding (seção 7.1): decide entre a tela cheia de onboarding
  // e o Bento Grid normal. Mesma queryKey de `IndicadoresStrip` — o React
  // Query deduplica automaticamente, sem requisição extra.
  const { data: indicadores, isLoading: carregandoIndicadores } = useIndicadoresGeraisQuery();

  if (carregandoIndicadores) {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-40" />
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <LoadingCard key={index} lines={1} />
          ))}
        </div>
      </div>
    );
  }

  if (indicadores && indicadores.contas_ativas === 0) {
    return <DashboardOnboarding />;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 font-semibold text-text-primary">Olá, {usuario?.nome}.</h1>
          <p className="mt-1 text-sm text-text-secondary">Aqui está o resumo das suas finanças.</p>
        </div>
        <div className="flex items-center gap-2">
          <PeriodoSeletor
            ano={periodo.ano}
            mes={periodo.mes}
            onChange={(ano, mes) => setPeriodo({ ano, mes })}
          />
          <Button variant="ghost" size="sm" onClick={() => setPersonalizando(true)} aria-label="Personalizar Dashboard">
            <Settings2 size={16} aria-hidden="true" />
            Personalizar
          </Button>
        </div>
      </header>

      <ResumoFinanceiroSection ano={periodo.ano} mes={periodo.mes} />

      {indicadores && indicadores.contas_ativas > 0 && indicadores.cartoes_ativos === 0 && (
        <ProximoPassoCard
          icon={CreditCard}
          titulo="Cadastre seu primeiro cartão"
          descricao="Acompanhe limite, faturas e vencimentos em um só lugar."
          rota="/cartoes"
        />
      )}

      <IndicadoresStrip />

      {/* Card "Hoje" (Sprint de Refinamento Premium, item 13): posicionado
          logo após os indicadores, antes do Bento Grid dos cards de domínio,
          para dar destaque visual ao que precisa de atenção HOJE — some
          sozinho quando não há eventos (ver `HojeCard.tsx`). */}
      <HojeCard />

      {/* Linha fixa de destaque (Refinamento Visual, decisão 7-8): "Contas e
          Cartões" + "Transações Recentes" ficam no mesmo nível de destaque
          do print de referência do usuário — fora da personalização do
          Bento Grid abaixo. */}
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
        <ContasCartoesCard />
        <TransacoesRecentesCard />
      </div>

      {/* `items-start`: sem isso, o CSS Grid padrão estica cada card para a
          altura da linha inteira (a do vizinho mais alto) — com conteúdo de
          densidade tão variável entre estes cards (uma lista de 1 linha
          por item em Faturas vs. 3 linhas + barra de progresso em Metas),
          o resultado era cards curtos "esticados" com um vazio enorme
          embaixo. Cada card agora só ocupa a própria altura natural
          (Etapa de Refinamento UX/UI, itens 1-2: hierarquia visual e
          densidade). */}
      <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-2 lg:grid-cols-3">
        {layout.ordem
          .filter((id) => !layout.ocultos.includes(id))
          .map((id) => {
            const Componente = COMPONENTE_POR_CARD[id];
            return <Componente key={id} />;
          })}
      </div>

      <DashboardCustomizeDrawer
        open={personalizando}
        layout={layout}
        onChange={atualizarLayout}
        onClose={() => setPersonalizando(false)}
      />
    </div>
  );
}
