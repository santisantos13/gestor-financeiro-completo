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
