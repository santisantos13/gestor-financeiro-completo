import { useState } from "react";
import { Menu, ListTree } from "lucide-react";
import { UserMenu } from "./UserMenu";
import { MobileNav } from "./MobileNav";
import { AtividadesRecentesDrawer } from "../domain/dashboard/AtividadesRecentesDrawer";

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
  const [menuAberto, setMenuAberto] = useState(false);
  const [atividadesAberto, setAtividadesAberto] = useState(false);

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
      <span className="hidden md:block" />

      <div className="flex items-center gap-1">
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
    </header>
  );
}
