import { useState } from "react";
import { AlertTriangle, ArrowDownToLine, Plus, Trash2, Wallet } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { SectionTitle } from "../../components/ui/SectionTitle";
import { StatCard } from "../../components/ui/StatCard";
import { AnimatedNumber } from "../../components/ui/AnimatedNumber";
import { TrendIndicator } from "../../components/ui/TrendIndicator";
import { FinancialBadge } from "../../components/ui/FinancialBadge";
import { Badge } from "../../components/ui/Badge";
import { MetricCard } from "../../components/ui/MetricCard";
import { Skeleton } from "../../components/ui/Skeleton";
import { LoadingCard } from "../../components/ui/LoadingCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { Button } from "../../components/ui/Button";
import { InstitutionBadge } from "../../components/ui/InstitutionBadge";
import { ThemeToggle } from "../../components/ui/ThemeToggle";
import { TODAS_INSTITUICOES_CONHECIDAS } from "../../lib/institutions";

const TODOS_STATUS_FATURA = ["ABERTA", "FECHADA", "PARCIALMENTE_PAGA", "PAGA", "ATRASADA"] as const;
const TODOS_STATUS_CONTRATO = ["ATIVO", "QUITADO", "INADIMPLENTE"] as const;
const TODOS_STATUS_TRANSACAO = ["PENDENTE", "PAGO"] as const;

/**
 * Laboratório visual permanente — rota `/dev`, protegida mas fora do
 * `Sidebar` (docs/analise-arquitetural-dashboard.md, seção 12). Demonstra
 * cada componente novo de `components/ui/` (seção 9.1) com dado fixo local
 * (nunca uma chamada real à API — a página tem que funcionar sempre,
 * independente do estado real do banco), cobrindo loading/erro/vazio/
 * sucesso. Convenção: todo componente novo de qualquer etapa futura ganha
 * uma seção aqui no mesmo commit que o introduz. Etapa de Refinamento
 * Visual: adicionou as seções "Branding de instituições financeiras" e
 * "Aparência" abaixo — as microinterações de hover em si (Button/Card/
 * Sidebar/StatCard) não ganharam seção nova porque já são visíveis em
 * TODOS os componentes existentes nesta mesma página (é passar o mouse).
 */
export function DevPage() {
  const [valorDemo, setValorDemo] = useState(1234.56);

  return (
    <div className="space-y-10 pb-16">
      <div>
        <h1 className="text-h1 font-semibold text-text-primary">/dev — laboratório visual</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Componentes de <code className="font-mono text-text-tertiary">components/ui/</code> criados na
          Etapa F3, com dado fixo (sem chamada à API). Ver docs/analise-arquitetural-dashboard.md, seção 12.
        </p>
      </div>

      <section>
        <SectionTitle>Aparência — tema claro/escuro</SectionTitle>
        <Card className="flex items-center justify-between">
          <div>
            <p className="text-sm text-text-primary">Alternância de tema</p>
            <p className="mt-0.5 text-caption text-text-tertiary">
              Mesmo <code className="font-mono">ThemeToggle</code> que aparece dentro do menu do usuário
              (clique no seu nome no canto superior direito). Persistido em{" "}
              <code className="font-mono">localStorage</code>, aplicado antes do React montar (sem flash).
            </p>
          </div>
          <ThemeToggle />
        </Card>
      </section>

      <section>
        <SectionTitle
          action={<Badge tone="accent">{TODAS_INSTITUICOES_CONHECIDAS.length} instituições</Badge>}
        >
          Branding de instituições financeiras
        </SectionTitle>
        <p className="mb-3 text-sm text-text-secondary">
          Registry único (<code className="font-mono text-text-tertiary">lib/institutions.ts</code>) que
          resolve nome/cor/logo/monograma/fallback para qualquer <code className="font-mono">instituicao</code>{" "}
          livre — usado por Conta (tabela e formulário) e pelos cards de Conta/Cartão do Dashboard. 15 das 17
          instituições têm logo oficial real (ver <code className="font-mono">assets/institutions/NOTICE.md</code>{" "}
          para proveniência); as demais (Wise/PayPal, internacionais) caem no monograma sobre a cor de marca.
        </p>
        <Card>
          <div className="flex flex-wrap gap-3">
            {TODAS_INSTITUICOES_CONHECIDAS.map((inst) => (
              <InstitutionBadge key={inst.id} nome={inst.nome} size="md" showName />
            ))}
          </div>
          <div className="mt-4 border-t border-border-subtle pt-4">
            <p className="mb-2 text-caption text-text-tertiary">Fallbacks</p>
            <div className="flex flex-wrap gap-3">
              <InstitutionBadge nome={null} size="md" showName />
              <InstitutionBadge nome="Cooperativa de Crédito Regional" size="md" showName />
            </div>
          </div>
        </Card>
      </section>

      <section>
        <SectionTitle>Botões — microinterações de hover</SectionTitle>
        <p className="mb-3 text-sm text-text-secondary">
          Passe o mouse: elevação de 1px em todas as variantes, glow discreto de acento na primária, borda
          reagindo na secundária. Clique para ver o <code className="font-mono">press</code> (
          <code className="font-mono">scale 0.98</code>, inalterado desta etapa).
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary">
            <Plus size={14} aria-hidden="true" /> Primário
          </Button>
          <Button variant="secondary">Secundário</Button>
          <Button variant="ghost">
            <ArrowDownToLine size={14} aria-hidden="true" /> Ghost
          </Button>
          <Button variant="danger">
            <Trash2 size={14} aria-hidden="true" /> Danger
          </Button>
          <Button variant="primary" loading>
            Carregando
          </Button>
          <Button variant="primary" disabled>
            Desabilitado
          </Button>
        </div>
      </section>

      <section>
        <SectionTitle>Card</SectionTitle>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card>
            <p className="text-sm text-text-secondary">Superfície base — passe o mouse para ver a elevação.</p>
          </Card>
          <Card>
            <p className="text-sm text-text-secondary">Segundo card, mesmo componente.</p>
          </Card>
          <Card>
            <p className="text-sm text-text-secondary">Terceiro card, mesmo componente.</p>
          </Card>
        </div>
      </section>

      <section>
        <SectionTitle>StatCard + AnimatedNumber + TrendIndicator</SectionTitle>
        <p className="mb-3 text-sm text-text-secondary">
          Entrada com fade + slide-up na montagem (recarregue a página para ver de novo); ícone reage com
          escala + rotação sutil no próprio hover.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <StatCard label="Sem variação" value={valorDemo} icon={<Wallet size={16} className="text-text-tertiary" aria-hidden="true" />} />
          <StatCard label="Variação positiva" value={valorDemo} trend={12.4} />
          <StatCard label="Variação negativa" value={valorDemo} trend={-8.1} />
          <StatCard label="Formato percentual" value="42.5" format="percent" />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setValorDemo((atual) => (atual === 1234.56 ? 9876.5 : 1234.56))}
          >
            Trocar valor (interpolação seção 6.2)
          </Button>
          <TrendIndicator percentual={12.4} />
          <TrendIndicator percentual={-8.1} />
        </div>
      </section>

      <section>
        <SectionTitle>FinancialBadge (por enum) e Badge (tones brutos)</SectionTitle>
        <div className="space-y-3">
          <div>
            <p className="mb-1.5 text-caption text-text-tertiary">StatusFatura</p>
            <div className="flex flex-wrap gap-2">
              {TODOS_STATUS_FATURA.map((status) => (
                <FinancialBadge key={status} status={status} />
              ))}
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-caption text-text-tertiary">StatusContratoCredito</p>
            <div className="flex flex-wrap gap-2">
              {TODOS_STATUS_CONTRATO.map((status) => (
                <FinancialBadge key={status} status={status} />
              ))}
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-caption text-text-tertiary">StatusTransacao</p>
            <div className="flex flex-wrap gap-2">
              {TODOS_STATUS_TRANSACAO.map((status) => (
                <FinancialBadge key={status} status={status} />
              ))}
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-caption text-text-tertiary">Badge — tones brutos</p>
            <div className="flex flex-wrap gap-2">
              <Badge tone="positive">positive</Badge>
              <Badge tone="negative">negative</Badge>
              <Badge tone="warning">warning</Badge>
              <Badge tone="neutral">neutral</Badge>
              <Badge tone="accent">accent</Badge>
            </div>
          </div>
        </div>
      </section>

      <section>
        <SectionTitle>MetricCard</SectionTitle>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard label="Contas ativas" value="3" />
          <MetricCard label="Cartões ativos" value="2" />
          <MetricCard label="Parcelas atrasadas" value="0" />
          <MetricCard label="Progresso médio de metas" value="64,2%" />
        </div>
      </section>

      <section>
        <SectionTitle action={<Badge tone="accent">com ação</Badge>}>SectionTitle (com e sem ação)</SectionTitle>
        <p className="text-sm text-text-secondary">
          Este título acima usa a prop <code className="font-mono">action</code>; a maioria dos cards do
          Dashboard usa a versão sem ação.
        </p>
      </section>

      <section>
        <SectionTitle>Skeleton</SectionTitle>
        <div className="flex flex-col gap-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
          <Skeleton className="h-4 w-full max-w-sm" />
        </div>
      </section>

      <section>
        <SectionTitle>LoadingCard</SectionTitle>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <LoadingCard lines={1} />
          <LoadingCard lines={3} />
          <LoadingCard lines={5} />
        </div>
      </section>

      <section>
        <SectionTitle>EmptyState</SectionTitle>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <EmptyState icon={Wallet} title="Sem dado" description="Sem ação — versão mínima." />
          </Card>
          <Card>
            <EmptyState
              icon={Wallet}
              title="Sem dado, com ação"
              description="Versão com botão de ação primária."
              action={<Button size="sm">Criar item</Button>}
            />
          </Card>
        </div>
      </section>

      <section>
        <SectionTitle>Erro + retry (decorativo)</SectionTitle>
        <Card>
          <ErrorMessage error={{ status: 500, detail: "Falha simulada só para esta página de demonstração." }} />
          <Button size="sm" variant="secondary" className="mt-3" onClick={() => {}}>
            Tentar novamente
          </Button>
        </Card>
      </section>

      <section>
        <SectionTitle action={<AlertTriangle size={16} className="text-warning" aria-hidden="true" />}>
          Nota
        </SectionTitle>
        <p className="text-sm text-text-secondary">
          Componentes de <code className="font-mono text-text-tertiary">components/domain/dashboard/</code>{" "}
          (ResumoFinanceiroSection, ContasCard, CartoesCard etc.) já são visíveis com dado real no Dashboard
          (<code className="font-mono text-text-tertiary">/</code>) e não são repetidos aqui — esta página
          cobre só as peças genéricas de <code className="font-mono text-text-tertiary">ui/</code>. A
          infraestrutura de tabelas (Etapa F4) tem laboratório próprio em{" "}
          <code className="font-mono text-text-tertiary">/dev/tables</code> (inclui a microinteração de
          hover/seleção de linha desta etapa), e a de formulários (Etapa F5) em{" "}
          <code className="font-mono text-text-tertiary">/dev/forms</code>. Pelo mesmo motivo,{" "}
          <code className="font-mono text-text-tertiary">components/domain/conta/</code> (Etapa F6 —
          colunas de tabela e o modal criar/visualizar/editar) não é duplicado aqui com dado falso: já é
          exercitado com dado real, contra o backend de verdade, em{" "}
          <code className="font-mono text-text-tertiary">/contas</code>. Pelo mesmo motivo,{" "}
          <code className="font-mono text-text-tertiary">components/domain/categoria/</code> (Etapa F7 —
          colunas de tabela, badge de cor/ícone e o modal criar/visualizar/editar) também é exercitado com
          dado real em <code className="font-mono text-text-tertiary">/categorias</code>, nunca duplicado
          aqui. Os dois campos novos e genéricos dessa etapa (
          <code className="font-mono text-text-tertiary">IconPicker</code>/
          <code className="font-mono text-text-tertiary">ColorPicker</code>, sem conhecimento de Categoria)
          têm seção própria em <code className="font-mono text-text-tertiary">/dev/forms</code>. A
          microinteração da{" "}
          <code className="font-mono text-text-tertiary">Sidebar</code> (ícone reagindo ao hover, glow no
          item ativo) só é visível na navegação real do app (ela fica fora de <code className="font-mono">/dev</code>
          , seção 12 de docs/analise-arquitetural-dashboard.md) — passe o mouse nos itens à esquerda.
        </p>
      </section>
    </div>
  );
}
