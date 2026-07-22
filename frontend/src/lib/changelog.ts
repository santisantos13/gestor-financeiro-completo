/**
 * Fonte única do que aparece em `/novidades` (docs/versionamento.md) —
 * lista mantida à mão, um item por versão publicada (mesma granularidade
 * do bump de `package.json`: uma entrada por bump de patch OU minor,
 * nunca uma entrada "genérica" cobrindo várias versões de uma vez).
 * Ordem: mais recente primeiro (a página não reordena).
 */
export interface ChangelogEntry {
  versao: string;
  data: string;
  titulo: string;
  itens: string[];
}

export const CHANGELOG: ChangelogEntry[] = [
  {
    versao: "0.4.2",
    data: "2026-07-22",
    titulo: "Mais 3 logos de instituição: Agibank, Stone e BRB",
    itens: [
      "Selo de instituição (Conta/Cartão) agora reconhece Agibank, Stone e Banco de Brasília (BRB) com o logo oficial, além dos 15 já existentes.",
    ],
  },
  {
    versao: "0.4.1",
    data: "2026-07-22",
    titulo: "Correções no Calendário financeiro",
    itens: [
      '"Despesas previstas" do resumo do mês não somava parcelas de Financiamento/Empréstimo (categorias próprias desde 21/07) - agora entram na soma, junto com o vencimento de fatura.',
      "Vencimento (e às vezes fechamento) de fatura podia sumir do calendário - acontecia ao navegar para um mês passado, ou quando o cartão já tinha vários ciclos futuros criados. Corrigido na raiz: a busca agora filtra direto pela data, sem depender de um número fixo de ciclos recentes.",
    ],
  },
  {
    versao: "0.4.0",
    data: "2026-07-22",
    titulo: "Primeira suíte de testes automatizados do frontend",
    itens: [
      "Nenhuma mudança visível para quem usa o app - trabalho interno de qualidade.",
      "Testes cobrindo os 3 fluxos críticos: login, envio de formulário (Tag) e a tabela (busca, ordenação, paginação).",
      "Vitest + Testing Library configurados sem risco para o build de produção (isolados de vite.config.ts/tsconfig.json de produção).",
    ],
  },
  {
    versao: "0.3.2",
    data: "2026-07-22",
    titulo: "Correção definitiva: site em produção travava com tela branca",
    itens: [
      'A correção anterior (0.3.1) não resolveu de verdade - o mesmo erro "__APP_VERSION__ is not defined" persistiu em produção mesmo após o novo deploy. Trocado por uma constante fixa de código-fonte (sem nenhuma injeção em tempo de build), eliminando de vez a dependência de como o ambiente de build resolve isso.',
    ],
  },
  {
    versao: "0.3.1",
    data: "2026-07-22",
    titulo: "Correção: site em produção travava com tela branca",
    itens: [
      'Selo de versão do Header quebrava toda a aplicação em produção (erro "__APP_VERSION__ is not defined"). Corrigida a forma como a versão é lida em tempo de build.',
    ],
  },
  {
    versao: "0.3.0",
    data: "2026-07-22",
    titulo: "Anexos de transação",
    itens: [
      'Nova ação "Anexos" em cada transação (ícone de clipe), abrindo um painel com a lista de anexos.',
      "Adicionar anexo por nome + caminho/link do arquivo (o app ainda não armazena o arquivo em si, só a referência).",
      "Remover anexo com confirmação.",
    ],
  },
  {
    versao: "0.2.2",
    data: "2026-07-22",
    titulo: "Selo de versão + página de novidades",
    itens: [
      'Selo "Alpha X.Y.Z" no Header, lido de package.json em tempo de build.',
      '"Últimas atualizações" abaixo do selo leva a esta página.',
    ],
  },
  {
    versao: "0.2.1",
    data: "2026-07-22",
    titulo: "Home: personalização corrigida e ampliada",
    itens: [
      'Dashboard renomeado para "Home" na navegação.',
      "Transações recentes: mostra as 3 mais recentes (antes eram 6).",
      "Personalizar Home: corrigido o arrastar para reordenar e o interruptor de mostrar/ocultar, que não funcionavam de forma confiável.",
      'Contas e Cartões, Transações Recentes e Evolução do saldo agora também podem ser reordenados/ocultados em "Personalizar" (antes eram fixos).',
    ],
  },
  {
    versao: "0.2.0",
    data: "2026-07-22",
    titulo: "Gráficos",
    itens: [
      "Nova página /gráficos: Evolução do saldo, Entradas x Saídas por mês, Gastos por categoria, Gastos por cartão e Distribuição do saldo por conta.",
      "Mini-card de Evolução do saldo na Home, com atalho para a página completa.",
    ],
  },
];
