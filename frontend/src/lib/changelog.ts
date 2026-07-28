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
    versao: "0.13.0",
    data: "2026-07-28",
    titulo: "Parcelamentos: excluir só esta parcela (sem cancelar a compra inteira)",
    itens: [
      'Ao excluir uma parcela de uma compra parcelada (Transações ou dentro do Cartão), agora é possível escolher entre "Só esta parcela" (remove só aquela linha, mantendo as demais) e "Compra inteira" (cancela todas as parcelas ainda destravadas, comportamento de sempre).',
      "Nenhuma parcela já paga/travada (fatura fechada) pode ser excluída por nenhuma das duas opções - continua protegida como antes.",
    ],
  },
  {
    versao: "0.12.1",
    data: "2026-07-26",
    titulo: "Correção de lentidão em produção",
    itens: [
      'O endpoint "/health" passou a checar o banco de verdade - necessário para um ping externo periódico (configurado fora do app) evitar tanto o "sono" do servidor gratuito quanto a pausa do banco gratuito por inatividade.',
    ],
  },
  {
    versao: "0.12.0",
    data: "2026-07-26",
    titulo: "Gráficos: total do mês com variação, drill-down, comparação e mais",
    itens: [
      'A seção "Gastos do mês" (categoria/cartão/conta) ganhou um total com a variação vs mês anterior, um único seletor de mês compartilhado e um atalho "Baixar relatório".',
      "Clicar numa categoria ou conta leva direto para as transações filtradas daquele item; clicar num cartão leva para a página de detalhe dele.",
      'Novo toggle "Comparar com mês anterior" mostra lado a lado o gasto deste mês e do mês passado.',
      "Categorias/contas/cartões em excesso agora agrupam os menores num item \"Outros\", mantendo os gráficos legíveis.",
    ],
  },
  {
    versao: "0.11.0",
    data: "2026-07-26",
    titulo: "Relatórios: exportar resumo do mês em CSV/PDF",
    itens: [
      'Nova página "Relatórios": mostra o mesmo resumo de um mês que a página de Gráficos exibe (entradas, saídas, saldo e gastos por categoria/cartão/conta) e permite baixar esse resumo em CSV (para abrir em planilha) ou PDF (para ler/imprimir).',
      "Nenhum cálculo novo - o arquivo baixado sempre reflete exatamente os mesmos números já exibidos em tela antes do download.",
    ],
  },
  {
    versao: "0.10.0",
    data: "2026-07-26",
    titulo: "Configurações: Notificações",
    itens: [
      'Nova seção "Notificações" em Configurações: escolha quais tipos de alerta (limite de cartão, vencimento de fatura, vencimento de conta recorrente, meta atingida, saldo baixo) contam para o número no sino do cabeçalho.',
      "Silenciar um tipo aqui não apaga nem pausa nenhum alerta - ele continua aparecendo normalmente na lista do sino, só para de gerar o aviso no contador.",
    ],
  },
  {
    versao: "0.9.0",
    data: "2026-07-26",
    titulo: "Alertas: sino de notificações, lista e criação",
    itens: [
      'Novo sino no cabeçalho (ícone de alerta) mostra quantos avisos configurados estão disparados agora - limite de cartão perto de estourar, fatura/conta recorrente perto de vencer, meta atingida, saldo baixo.',
      'Clicar no sino abre a lista completa: pausar/reativar, editar ou excluir cada alerta.',
      'Botão "Novo alerta" na lista permite criar um alerta do zero - escolha o tipo, o item monitorado (cartão/conta/meta/conta recorrente) e a condição (ex.: "avisar ao atingir 90% do limite").',
    ],
  },
  {
    versao: "0.8.0",
    data: "2026-07-26",
    titulo: "Alertas: base pronta nos bastidores (ainda sem tela)",
    itens: [
      "Nenhuma mudança visível ainda - trabalho interno. O backend de Alertas (avisos de limite de cartão perto de estourar, fatura/conta recorrente perto de vencer, meta atingida, saldo baixo) foi finalizado e testado.",
      'Próxima entrega traz a tela (sino de notificações + lista) que finalmente usa isso.',
    ],
  },
  {
    versao: "0.7.0",
    data: "2026-07-26",
    titulo: "Configurações: cor de destaque personalizável",
    itens: [
      'Nova opção em Configurações → Preferências: escolha entre 5 cores de destaque (Azul, Verde, Rosa, Lilás, Âmbar) - troca instantânea, sem recarregar a página. Funciona igual nos temas claro e escuro.',
      "Notificações continua pendente (depende do backend de Alertas, ainda não pronto).",
    ],
  },
  {
    versao: "0.6.0",
    data: "2026-07-25",
    titulo: "Gráficos: novo gráfico \"Gastos por conta\"",
    itens: [
      'Nova página /gráficos ganha um 6º gráfico: "Gastos por conta", em círculo (como "Gastos por categoria"), mostrando quanto foi gasto direto de cada conta no mês - irmão de "Gastos por cartão", nunca mistura os dois (compra de cartão não conta aqui).',
      "O total do período agora também aparece escrito no miolo do círculo, não só na lista ao lado.",
    ],
  },
  {
    versao: "0.5.3",
    data: "2026-07-25",
    titulo: "Transações: \"Despesas/Receitas do período\" agora batem com a tabela",
    itens: [
      'O total no topo de Transações incluía compras de cartão, mas a tabela logo abaixo nunca as mostra (regra de 20/07) - os números pareciam não bater. Agora "Receitas/Despesas/Saldo do período" desta tela contam só o que aparece na tabela (lançamentos de Conta e pagamentos de fatura). O Dashboard continua mostrando o gasto real do mês, cartão incluído - só mudou aqui.',
    ],
  },
  {
    versao: "0.5.2",
    data: "2026-07-25",
    titulo: "Transações: aviso quando uma compra cancelada deixa parcela para trás",
    itens: [
      'Excluir uma compra parcelada no cartão sempre preservou a(s) parcela(s) que já estavam numa fatura fechada (o total daquele mês não muda de propósito) - mas não havia nenhum aviso disso. Agora "Compras desta fatura" (dentro do cartão) mostra uma etiqueta "Compra cancelada" nessas parcelas, explicando por que elas continuam contando no total do período.',
    ],
  },
  {
    versao: "0.5.1",
    data: "2026-07-23",
    titulo: "Configurações: preferências de formato de data e tema",
    itens: [
      "Nova seção \"Preferências\" em Configurações: escolha o formato de data (DD/MM/AAAA, AAAA-MM-DD ou MM/DD/AAAA) e o tema (claro/escuro, já existente, agora também aqui).",
      "Moeda ficou de fora - trocar só o símbolo (R$/US$/€) sem converter os valores poderia confundir sobre quanto dinheiro você realmente tem.",
    ],
  },
  {
    versao: "0.5.0",
    data: "2026-07-23",
    titulo: "Configurações: editar perfil e trocar senha",
    itens: [
      'Nova página "Configurações" (menu do usuário → Configurações): altere seu nome/e-mail e troque sua senha.',
      "Primeira fatia do módulo de Configurações - preferências, notificações e temas chegam em entregas seguintes.",
    ],
  },
  {
    versao: "0.4.3",
    data: "2026-07-22",
    titulo: "Mais um logo de instituição: PagBank",
    itens: [
      "Selo de instituição (Conta/Cartão) agora reconhece PagBank/PagSeguro com o logo oficial - estava faltando na lista anterior.",
    ],
  },
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
