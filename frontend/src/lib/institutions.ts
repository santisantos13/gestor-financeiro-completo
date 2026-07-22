/**
 * Registry único de branding de instituições financeiras — Etapa de
 * Refinamento Visual (Branding + Microinterações). Resolve logo/nome/cor
 * predominante/fallback num único lugar; nenhum outro arquivo do projeto
 * deve ter um `switch`/`if` mapeando nome de instituição para cor ou ícone
 * — sempre passa por `resolveInstitution()` daqui.
 *
 * Não é regra de negócio: `instituicao` já existe como `string | null`
 * livre no backend (Conta/Cartão) — este arquivo só decora visualmente um
 * valor que o backend já entrega, nunca valida nem transforma o dado
 * salvo.
 *
 * Logos reais (2026-07-24, pedido explícito do usuário): 15 das 17
 * instituições ganharam `logoUrl` apontando para um SVG oficial real (ver
 * `src/assets/institutions/NOTICE.md` para proveniência completa - cada
 * arquivo vem do diretório público de participantes do Open Finance
 * Brasil, redistribuído via o pacote `logos-bancos-br`, uso nominativo).
 * Wise/PayPal continuam só com monograma (instituições internacionais,
 * fora do escopo desse dataset). `InstitutionBadge` usa `logoUrl` quando
 * presente, caindo no monograma sobre `cor` como fallback - exatamente a
 * extensão que este arquivo já previa desde a etapa de Branding original.
 *
 * Agibank/Stone/BRB/PagBank (2026-07-22, mesma fonte `logos-bancos-br`
 * atualizada): PNG em vez de SVG - as ferramentas de busca web disponíveis
 * nesta sessão só extraem TEXTO de página, nunca bytes binários/vetoriais
 * brutos (SVG incluído), então esses 4 arquivos não puderam ser baixados
 * como nos 15 acima. Capturados via navegador (Chrome), recortados e com
 * fundo removido (ver `NOTICE.md`) - raster, não vetor, mas o mesmo
 * tratamento (`object-contain` em `InstitutionBadge`) funciona igual para
 * os dois formatos. PagBank foi pedido separadamente pelo usuário (faltava
 * na lista original).
 */

import { corDeContraste } from "./color";
import logoBB from "../assets/institutions/bb.svg";
import logoSantander from "../assets/institutions/santander.svg";
import logoItau from "../assets/institutions/itau.svg";
import logoBradesco from "../assets/institutions/bradesco.svg";
import logoCaixa from "../assets/institutions/caixa.svg";
import logoInter from "../assets/institutions/inter.svg";
import logoC6 from "../assets/institutions/c6.svg";
import logoNeon from "../assets/institutions/neon.svg";
import logoPicpay from "../assets/institutions/picpay.svg";
import logoMercadoPago from "../assets/institutions/mercadopago.svg";
import logoXp from "../assets/institutions/xp.svg";
import logoBtg from "../assets/institutions/btg.svg";
import logoSicredi from "../assets/institutions/sicredi.svg";
import logoSicoob from "../assets/institutions/sicoob.svg";
import logoNubank from "../assets/institutions/nubank.svg";
import logoAgibank from "../assets/institutions/agibank.png";
import logoStone from "../assets/institutions/stone.png";
import logoBrb from "../assets/institutions/brb.png";
import logoPagbank from "../assets/institutions/pagbank.png";

export interface InstitutionInfo {
  id: string;
  nome: string;
  /** Substrings normalizadas (sem acento, minúsculas) usadas para casar
   * com o texto livre que o usuário digitou em `instituicao`. */
  aliases: string[];
  /** Cor de marca real (hex) — fato público, usada como fundo do
   * monograma e, quando fizer sentido, como acento decorativo pontual. */
  cor: string;
  /** Monograma de 1-2 caracteres exibido quando não há logo real. */
  iniciais: string;
  /** Logo oficial real (SVG importado como asset) — quando presente,
   * `InstitutionBadge` mostra a imagem em vez do monograma. `undefined`
   * para instituições sem logo redistribuível (Wise/PayPal). */
  logoUrl?: string;
}

const INSTITUICOES: InstitutionInfo[] = [
  { id: "nubank", nome: "Nubank", aliases: ["nubank", "nu pagamentos", "nu financeira"], cor: "#820AD1", iniciais: "Nu", logoUrl: logoNubank },
  { id: "inter", nome: "Banco Inter", aliases: ["banco inter", "inter"], cor: "#FF7A00", iniciais: "In", logoUrl: logoInter },
  { id: "santander", nome: "Santander", aliases: ["santander"], cor: "#EC0000", iniciais: "Sa", logoUrl: logoSantander },
  { id: "itau", nome: "Itaú", aliases: ["itau", "itaú"], cor: "#EC7000", iniciais: "It", logoUrl: logoItau },
  { id: "bradesco", nome: "Bradesco", aliases: ["bradesco"], cor: "#CC092F", iniciais: "Br", logoUrl: logoBradesco },
  { id: "caixa", nome: "Caixa Econômica Federal", aliases: ["caixa economica", "caixa econômica", "caixa"], cor: "#0070AE", iniciais: "Cx", logoUrl: logoCaixa },
  { id: "bb", nome: "Banco do Brasil", aliases: ["banco do brasil"], cor: "#FADB00", iniciais: "BB", logoUrl: logoBB },
  { id: "c6", nome: "C6 Bank", aliases: ["c6 bank", "c6"], cor: "#242424", iniciais: "C6", logoUrl: logoC6 },
  { id: "neon", nome: "Neon", aliases: ["neon"], cor: "#00E28A", iniciais: "Ne", logoUrl: logoNeon },
  { id: "picpay", nome: "PicPay", aliases: ["picpay"], cor: "#21C25E", iniciais: "Pi", logoUrl: logoPicpay },
  { id: "mercadopago", nome: "Mercado Pago", aliases: ["mercado pago", "mercadopago"], cor: "#00B1EA", iniciais: "Mp", logoUrl: logoMercadoPago },
  { id: "wise", nome: "Wise", aliases: ["wise", "transferwise"], cor: "#9FE870", iniciais: "Wi" },
  { id: "paypal", nome: "PayPal", aliases: ["paypal"], cor: "#003087", iniciais: "Pp" },
  { id: "xp", nome: "XP Investimentos", aliases: ["xp investimentos", "xp inc", "xp "], cor: "#1C1C1C", iniciais: "XP", logoUrl: logoXp },
  { id: "btg", nome: "BTG Pactual", aliases: ["btg pactual", "btg"], cor: "#003DA5", iniciais: "BT", logoUrl: logoBtg },
  { id: "sicredi", nome: "Sicredi", aliases: ["sicredi"], cor: "#7AB51D", iniciais: "Si", logoUrl: logoSicredi },
  { id: "sicoob", nome: "Sicoob", aliases: ["sicoob"], cor: "#00A65E", iniciais: "Sc", logoUrl: logoSicoob },
  { id: "agibank", nome: "Agibank", aliases: ["agibank", "agi bank"], cor: "#0062FB", iniciais: "Ag", logoUrl: logoAgibank },
  { id: "stone", nome: "Stone", aliases: ["stone"], cor: "#00D700", iniciais: "St", logoUrl: logoStone },
  { id: "brb", nome: "Banco de Brasília (BRB)", aliases: ["banco de brasilia", "banco de brasília", "brb"], cor: "#0D76E1", iniciais: "BR", logoUrl: logoBrb },
  { id: "pagbank", nome: "PagBank", aliases: ["pagbank", "pagseguro", "pag bank", "pag seguro"], cor: "#63C4C6", iniciais: "Pb", logoUrl: logoPagbank },
];

/** Fallback quando `instituicao` é `null`/vazia — nenhuma cor de marca,
 * tratado à parte em `InstitutionBadge` (ícone neutro `Landmark`, sem
 * monograma). Fallback quando `instituicao` tem texto mas não bate com
 * nenhum alias conhecido — usa o texto do próprio usuário como "nome",
 * cor neutra do Design System (nunca uma cor inventada). */
const COR_NEUTRA = "#3F3F46";

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function extrairIniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

/**
 * Resolve nome/cor/iniciais para um valor livre de `instituicao`. `null`/
 * string vazia devolve `null` (sem instituição informada — quem chama
 * decide o ícone neutro). Uma instituição desconhecida devolve um
 * `InstitutionInfo` sintético com o texto do próprio usuário e cor neutra
 * — nunca lança erro, nunca reprova o dado (o backend já aceita qualquer
 * string livre em `instituicao`, este resolver só decora).
 */
export function resolveInstitution(instituicao: string | null | undefined): InstitutionInfo | null {
  const texto = instituicao?.trim();
  if (!texto) return null;

  const normalizado = normalizar(texto);
  const conhecida = INSTITUICOES.find((inst) => inst.aliases.some((alias) => normalizado.includes(alias)));
  if (conhecida) return conhecida;

  return {
    id: `desconhecida:${normalizado}`,
    nome: texto,
    aliases: [],
    cor: COR_NEUTRA,
    iniciais: extrairIniciais(texto),
  };
}

/** Reexportado por compatibilidade — a função em si foi extraída para
 * `lib/color.ts` na Etapa F7 (Categoria), que precisava da mesma lógica
 * sem depender de nada específico de instituição. Necessária aqui porque a
 * paleta de marca real inclui cores muito claras (ex. Banco do Brasil
 * `#FADB00`) e muito escuras (ex. C6 `#242424`), então um texto de cor
 * fixa ficaria ilegível em metade dos casos. */
export { corDeContraste };

/** Lista completa — usada só pela galeria de demonstração em `/dev`, nunca
 * por código de produto (que sempre resolve uma instituição específica via
 * `resolveInstitution`). */
export const TODAS_INSTITUICOES_CONHECIDAS: readonly InstitutionInfo[] = INSTITUICOES;
