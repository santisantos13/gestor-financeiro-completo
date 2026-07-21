import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/layout/Sidebar";
import { Header } from "../components/layout/Header";
import { CommandPalette } from "../components/layout/CommandPalette";
import { useSincronizarRecorrentesAoAbrir } from "../hooks/useContaRecorrenteQueries";

/**
 * Casca de rota autenticada. Compõe `Sidebar` + `Header`
 * (`components/layout/`) construídos na Etapa F2 — na F1 este arquivo
 * ainda tinha o cabeçalho embutido e nenhuma navegação lateral.
 *
 * `CommandPalette` (Sprint de Refinamento Premium, item 16) montado aqui
 * uma única vez — disponível (`Ctrl+K`/`Cmd+K`) em qualquer rota
 * autenticada, sem precisar remontar a cada navegação.
 *
 * `useSincronizarRecorrentesAoAbrir` (expansão de Contas Recorrentes,
 * 2026-07-20): uma chamada por sessão a `POST /contas-recorrentes/sincronizar`
 * — as ocorrências vencidas de todos os templates ativos viram Transacao
 * assim que o usuário abre o app ("geração automática" sem scheduler).
 */
export function AppLayout() {
  useSincronizarRecorrentesAoAbrir();
  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
