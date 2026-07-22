import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { formatDate } from "../../utils/date";
import { CHANGELOG } from "../../lib/changelog";

/**
 * `/novidades` — página de changelog do app, acessada pelo link "Últimas
 * atualizações" abaixo do selo de versão no Header (docs/versionamento.md).
 * Fora de `NAV_ITEMS`/Sidebar de propósito (mesmo tratamento das rotas
 * `/dev/*`): é uma página de apoio, não navegação principal do produto.
 * Conteúdo vem de `lib/changelog.ts`, mantido à mão a cada bump de versão
 * — nenhum dado vindo de backend aqui.
 */
export function NovidadesPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-h1 font-semibold text-text-primary">Últimas atualizações</h1>
        <p className="mt-1 text-sm text-text-secondary">O que mudou no app, versão por versão.</p>
      </header>

      <div className="space-y-4">
        {CHANGELOG.map((entrada) => (
          <Card key={entrada.versao}>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="accent">v{entrada.versao}</Badge>
              <h2 className="text-h3 font-semibold text-text-primary">{entrada.titulo}</h2>
              <span className="ml-auto text-caption text-text-tertiary">{formatDate(entrada.data)}</span>
            </div>
            <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-text-secondary">
              {entrada.itens.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  );
}
