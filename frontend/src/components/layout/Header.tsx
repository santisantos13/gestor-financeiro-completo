import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Menu, ListTree, Bell } from "lucide-react";
import { UserMenu } from "./UserMenu";
import { MobileNav } from "./MobileNav";
import { AtividadesRecentesDrawer } from "../domain/dashboard/AtividadesRecentesDrawer";
import { AlertasDrawer } from "../domain/alerta/AlertasDrawer";
import { useAlertas } from "../../hooks/useAlertaQueries";
import { APP_VERSION } from "../../version";

/**
 * Cabecalho fixo. backdrop-blur + fundo semi-transparente e o uso
 * sancionado de glass em "header com scroll por baixo" - design-system.md,
 * secao 12. Substitui o header embutido em AppLayout na F1. Avatar/nome/
 * logout viviam soltos aqui ate a Etapa de Refinamento Visual - agora
 * moram dentro de UserMenu (clicar no nome abre o menu, que tambem tem
 * o toggle de tema e e a ancora para futuras opcoes de personalizacao).
 *
 * Botao de menu (abaixo de md, Etapa de Refinamento de UI): abre
 * MobileNav - antes deste botao nao havia NENHUMA forma de navegar
 * entre paginas no celular (Sidebar e hidden ate md). Ver
 * docs/revisao-tecnica-refinamento-ui.md.
 */
export function Header() {
  const navigate = useNavigate();
  const [menuAberto, setMenuAberto] = useState(false);
  const [atividadesAberto, setAtividadesAberto] = useState(false);
  const [alertasAberto, setAlertasAberto] = useState(false);
  // `useAlertas()` já é usado de novo dentro de `AlertasDrawer` (mesmo
  // cache do React Query, sem requisição extra) - aqui só para o
  // contador do sino, que precisa existir mesmo com o Drawer fechado.
  const { data: alertas } = useAlertas(false);
  const quantidadeDisparados = (alertas ?? []).filter((a) => a.disparado).length;

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center justify-between border-b border-border-subtle bg-bg/80 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex items-center gap-2 md:hidden">
        <button
          type="button"
          onClick={() => setMenuAberto(true)}
          aria-label="Abrir navegacao"
          aria-haspopup="dialog"
          aria-expanded={menuAberto}
          className="-ml-1.5 rounded-sm p-1.5 text-text-secondary transition-colors duration-fast ease-out hover:bg-surface-2 hover:text-text-primary"
        >
          <Menu size={20} aria-hidden="true" />
        </button>
        <span className="text-h3 font-semibold text-text-primary">Financas Pessoais</span>
      </div>
      {/* Selo de versão + link de changelog (docs/versionamento.md) —
          "Alpha X.Y.Z" a partir de `APP_VERSION` (`version.ts`), mantida
          manualmente em sincronia com `package.json` (ver docstring de
          `version.ts` para o porquê: duas tentativas de injetar isso via
          `vite.config.ts` funcionavam aqui mas quebravam em produção no
          Render). Convenção de bump: Z (patch) a cada ajuste/correção
          pequena, Y (minor, reseta Z para 0) a cada CRUD novo ou
          funcionalidade grande. Prefixo "Alpha" enquanto o projeto não
          tiver um primeiro release estável. "Últimas atualizações" leva a
          `/novidades` (`lib/changelog.ts`), pedido explícito do usuário
          para ver um resumo do que mudou sem precisar perguntar. */}
      <div className="hidden flex-col items-center gap-0.5 md:flex">
        <span className="select-none rounded-full border border-border-subtle px-2 py-0.5 text-caption text-text-tertiary">
          Alpha {APP_VERSION}
        </span>
        <button
          type="button"
          onClick={() => navigate("/novidades")}
          className="text-micro font-medium text-text-tertiary underline-offset-2 transition-colors duration-fast ease-out hover:text-accent hover:underline"
        >
          Últimas atualizações
        </button>
      </div>

      <div className="flex items-center gap-1">
        {/* Alertas (frontend do CRUD de Alerta, item t139) - contador mostra
            quantos alertas ATIVOS estão disparados agora (avaliação em
            tempo real, nunca um histórico - ver docs/analise-arquitetural-alertas.md). */}
        <button
          type="button"
          onClick={() => setAlertasAberto(true)}
          aria-label={`Ver alertas${quantidadeDisparados > 0 ? ` (${quantidadeDisparados} disparado(s))` : ""}`}
          aria-haspopup="dialog"
          aria-expanded={alertasAberto}
          className="relative rounded-sm p-1.5 text-text-secondary transition-colors duration-fast ease-out hover:bg-surface-2 hover:text-text-primary"
        >
          <Bell size={18} aria-hidden="true" />
          {quantidadeDisparados > 0 && (
            <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-negative px-1 text-[10px] font-semibold leading-none text-text-onAccent">
              {quantidadeDisparados > 9 ? "9+" : quantidadeDisparados}
            </span>
          )}
        </button>
        {/* Central de Atividades (Sprint de Refinamento Premium, item 17) */}
        <button
          type="button"
          onClick={() => setAtividadesAberto(true)}
          aria-label="Ver atividades recentes"
          aria-haspopup="dialog"
          aria-expanded={atividadesAberto}
          className="rounded-sm p-1.5 text-text-secondary transition-colors duration-fast ease-out hover:bg-surface-2 hover:text-text-primary"
        >
          <ListTree size={18} aria-hidden="true" />
        </button>
        <UserMenu />
      </div>

      <MobileNav open={menuAberto} onClose={() => setMenuAberto(false)} />
      <AtividadesRecentesDrawer open={atividadesAberto} onClose={() => setAtividadesAberto(false)} />
      <AlertasDrawer open={alertasAberto} onClose={() => setAlertasAberto(false)} />
    </header>
  );
}
