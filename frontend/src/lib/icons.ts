/**
 * Registry único de ícones de Categoria — Etapa F7. `Categoria.icone` é uma
 * string livre no backend (até 40 caracteres, sem nenhuma convenção
 * imposta — `app/schemas/categoria.py`), então a convenção é definida
 * inteiramente aqui: o valor salvo é sempre o `id` de um destes ícones
 * curados, nunca um nome de componente ou um SVG arbitrário. Mesmo
 * princípio de `lib/institutions.ts` — um registry único, nenhum
 * switch/case espalhado pelo projeto resolvendo ícone por conta própria.
 * `IconPicker` (formulário) e `CategoryBadge` (exibição) são os dois
 * únicos consumidores.
 *
 * `grupo` — Etapa F10 (Rich Pickers): antes existia só como comentário
 * separando visualmente as faixas abaixo; formalizado como campo real
 * para o `IconPicker` conseguir agrupar de verdade no popover, sem mudar
 * nenhum `id`/`label`/`Icon` existente (o valor salvo no backend não
 * muda).
 */
import {
  Baby,
  Banknote,
  Bath,
  Bike,
  Book,
  Briefcase,
  Bus,
  Cake,
  Camera,
  Car,
  Cat,
  Coffee,
  Coins,
  CreditCard,
  Dog,
  Droplet,
  Dumbbell,
  Factory,
  Film,
  Flame,
  Fuel,
  Gamepad2,
  Gem,
  Gift,
  GraduationCap,
  HandCoins,
  HandHeart,
  Handshake,
  Headphones,
  HeartPulse,
  Home,
  Key,
  Landmark,
  Laptop,
  Lightbulb,
  Mountain,
  Music,
  Package,
  Palette,
  ParkingCircle,
  PartyPopper,
  PawPrint,
  Pill,
  PiggyBank,
  Plane,
  Popcorn,
  Receipt,
  Recycle,
  Scale,
  Scissors,
  Shirt,
  Ship,
  ShoppingBag,
  ShoppingCart,
  Smartphone,
  Sparkles,
  Star,
  Stethoscope,
  Tag,
  Ticket,
  Train,
  TreePine,
  TrendingUp,
  Trophy,
  Truck,
  Umbrella,
  Users,
  UtensilsCrossed,
  Watch,
  Wallet,
  Wifi,
  Wrench,
  Zap,
  DollarSign,
  Building2,
  type LucideIcon,
} from "lucide-react";

export interface IconInfo {
  id: string;
  label: string;
  Icon: LucideIcon;
  grupo: string;
}

const ICONE_NEUTRO: IconInfo = { id: "tag", label: "Outros", Icon: Tag, grupo: "Outros" };

const ICONES: IconInfo[] = [
  { id: "home", label: "Moradia", Icon: Home, grupo: "Moradia" },
  { id: "building-2", label: "Imóveis", Icon: Building2, grupo: "Moradia" },
  { id: "key", label: "Aluguel", Icon: Key, grupo: "Moradia" },
  { id: "lightbulb", label: "Consultoria", Icon: Lightbulb, grupo: "Moradia" },
  { id: "droplet", label: "Água", Icon: Droplet, grupo: "Moradia" },
  { id: "flame", label: "Gás", Icon: Flame, grupo: "Moradia" },
  { id: "wifi", label: "Internet", Icon: Wifi, grupo: "Moradia" },
  { id: "wrench", label: "Manutenção", Icon: Wrench, grupo: "Moradia" },
  { id: "car", label: "Transporte", Icon: Car, grupo: "Transporte" },
  { id: "bus", label: "Transporte público", Icon: Bus, grupo: "Transporte" },
  { id: "fuel", label: "Combustível", Icon: Fuel, grupo: "Transporte" },
  { id: "bike", label: "Bicicleta", Icon: Bike, grupo: "Transporte" },
  { id: "train", label: "Metrô/Trem", Icon: Train, grupo: "Transporte" },
  { id: "ship", label: "Barco", Icon: Ship, grupo: "Transporte" },
  { id: "parking-circle", label: "Estacionamento", Icon: ParkingCircle, grupo: "Transporte" },
  { id: "truck", label: "Mudança", Icon: Truck, grupo: "Transporte" },
  { id: "utensils-crossed", label: "Alimentação", Icon: UtensilsCrossed, grupo: "Alimentação" },
  { id: "coffee", label: "Café", Icon: Coffee, grupo: "Alimentação" },
  { id: "shopping-cart", label: "Compras", Icon: ShoppingCart, grupo: "Compras" },
  { id: "shopping-bag", label: "Sacola de compras", Icon: ShoppingBag, grupo: "Compras" },
  { id: "shirt", label: "Roupas", Icon: Shirt, grupo: "Compras" },
  { id: "watch", label: "Acessórios", Icon: Watch, grupo: "Compras" },
  { id: "gem", label: "Joias e luxo", Icon: Gem, grupo: "Compras" },
  { id: "package", label: "Encomendas", Icon: Package, grupo: "Compras" },
  { id: "heart-pulse", label: "Saúde", Icon: HeartPulse, grupo: "Saúde" },
  { id: "stethoscope", label: "Consultas médicas", Icon: Stethoscope, grupo: "Saúde" },
  { id: "pill", label: "Remédios", Icon: Pill, grupo: "Saúde" },
  { id: "dumbbell", label: "Academia", Icon: Dumbbell, grupo: "Saúde" },
  { id: "bath", label: "Cuidados pessoais", Icon: Bath, grupo: "Saúde" },
  { id: "scissors", label: "Salão de beleza", Icon: Scissors, grupo: "Saúde" },
  { id: "graduation-cap", label: "Educação", Icon: GraduationCap, grupo: "Educação" },
  { id: "book", label: "Livros", Icon: Book, grupo: "Educação" },
  { id: "plane", label: "Viagem", Icon: Plane, grupo: "Lazer e cultura" },
  { id: "mountain", label: "Trilha e aventura", Icon: Mountain, grupo: "Lazer e cultura" },
  { id: "tree-pine", label: "Natureza", Icon: TreePine, grupo: "Lazer e cultura" },
  { id: "film", label: "Cinema", Icon: Film, grupo: "Lazer e cultura" },
  { id: "popcorn", label: "Entretenimento", Icon: Popcorn, grupo: "Lazer e cultura" },
  { id: "ticket", label: "Ingressos", Icon: Ticket, grupo: "Lazer e cultura" },
  { id: "music", label: "Música", Icon: Music, grupo: "Lazer e cultura" },
  { id: "headphones", label: "Áudio e streaming", Icon: Headphones, grupo: "Lazer e cultura" },
  { id: "gamepad-2", label: "Jogos", Icon: Gamepad2, grupo: "Lazer e cultura" },
  { id: "camera", label: "Fotografia", Icon: Camera, grupo: "Lazer e cultura" },
  { id: "palette", label: "Arte", Icon: Palette, grupo: "Lazer e cultura" },
  { id: "sparkles", label: "Lazer", Icon: Sparkles, grupo: "Lazer e cultura" },
  { id: "party-popper", label: "Festas", Icon: PartyPopper, grupo: "Lazer e cultura" },
  { id: "cake", label: "Aniversário", Icon: Cake, grupo: "Lazer e cultura" },
  { id: "trophy", label: "Prêmios", Icon: Trophy, grupo: "Lazer e cultura" },
  { id: "star", label: "Favoritos", Icon: Star, grupo: "Lazer e cultura" },
  { id: "gift", label: "Presentes", Icon: Gift, grupo: "Lazer e cultura" },
  { id: "baby", label: "Filhos", Icon: Baby, grupo: "Família e relacionamentos" },
  { id: "users", label: "Família", Icon: Users, grupo: "Família e relacionamentos" },
  { id: "paw-print", label: "Pet", Icon: PawPrint, grupo: "Família e relacionamentos" },
  { id: "dog", label: "Cachorro", Icon: Dog, grupo: "Família e relacionamentos" },
  { id: "cat", label: "Gato", Icon: Cat, grupo: "Família e relacionamentos" },
  { id: "hand-heart", label: "Doações", Icon: HandHeart, grupo: "Família e relacionamentos" },
  { id: "handshake", label: "Acordos e parcerias", Icon: Handshake, grupo: "Família e relacionamentos" },
  { id: "smartphone", label: "Celular", Icon: Smartphone, grupo: "Tecnologia" },
  { id: "laptop", label: "Tecnologia", Icon: Laptop, grupo: "Tecnologia" },
  { id: "zap", label: "Contas e energia", Icon: Zap, grupo: "Trabalho e finanças" },
  { id: "briefcase", label: "Trabalho", Icon: Briefcase, grupo: "Trabalho e finanças" },
  { id: "factory", label: "Indústria", Icon: Factory, grupo: "Trabalho e finanças" },
  { id: "dollar-sign", label: "Renda", Icon: DollarSign, grupo: "Trabalho e finanças" },
  { id: "trending-up", label: "Investimentos", Icon: TrendingUp, grupo: "Trabalho e finanças" },
  { id: "piggy-bank", label: "Poupança", Icon: PiggyBank, grupo: "Trabalho e finanças" },
  { id: "wallet", label: "Carteira", Icon: Wallet, grupo: "Trabalho e finanças" },
  { id: "banknote", label: "Dinheiro", Icon: Banknote, grupo: "Trabalho e finanças" },
  { id: "coins", label: "Moedas", Icon: Coins, grupo: "Trabalho e finanças" },
  { id: "hand-coins", label: "Empréstimo", Icon: HandCoins, grupo: "Trabalho e finanças" },
  { id: "landmark", label: "Banco", Icon: Landmark, grupo: "Trabalho e finanças" },
  { id: "credit-card", label: "Cartão", Icon: CreditCard, grupo: "Trabalho e finanças" },
  { id: "receipt", label: "Assinaturas", Icon: Receipt, grupo: "Trabalho e finanças" },
  { id: "umbrella", label: "Seguro", Icon: Umbrella, grupo: "Trabalho e finanças" },
  { id: "scale", label: "Jurídico", Icon: Scale, grupo: "Trabalho e finanças" },
  { id: "recycle", label: "Reciclagem", Icon: Recycle, grupo: "Trabalho e finanças" },
  ICONE_NEUTRO,
];

export function resolveIconInfo(id: string | null | undefined): IconInfo {
  if (!id) return ICONE_NEUTRO;
  return ICONES.find((icone) => icone.id === id) ?? ICONE_NEUTRO;
}

export const TODOS_ICONES: readonly IconInfo[] = ICONES;
