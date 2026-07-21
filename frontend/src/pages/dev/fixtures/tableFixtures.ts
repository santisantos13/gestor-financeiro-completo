/**
 * Dado 100% sintético para o laboratório `/dev/tables` (Etapa F4) — nenhuma
 * entidade real do backend (não é Conta, Cartão, Transação etc.), conforme
 * exigido: "Nenhuma regra de negócio. Nenhuma entidade específica. Tudo
 * genérico." O formato (`RegistroDemo`) existe só para ter colunas de tipos
 * variados (texto, número, enum, data) o bastante para exercitar busca,
 * filtro, ordenação e ações da tabela.
 */

export type StatusDemo = "ativo" | "pendente" | "arquivado";

export interface RegistroDemo {
  id: number;
  nome: string;
  categoria: string;
  status: StatusDemo;
  valor: number;
  atualizadoEm: string; // AAAA-MM-DD
}

const CATEGORIAS = ["Alpha", "Beta", "Gama", "Delta", "Épsilon"];
const STATUS: StatusDemo[] = ["ativo", "pendente", "arquivado"];
const NOMES = [
  "Registro",
  "Item",
  "Entrada",
  "Elemento",
  "Unidade",
  "Componente",
  "Bloco",
  "Nó",
];

/** PRNG determinístico (mulberry32) — mesma massa de dado a cada reload,
 * sem depender de `Math.random()` nem de qualquer chamada de rede. */
function criarGerador(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Gera `quantidade` registros fictícios. Usado com milhares de linhas na
 * página `/dev/tables` para validar performance de busca/filtro/ordenação/
 * paginação client-side (docs/analise-arquitetural-frontend.md, seção 13).
 */
export function gerarRegistrosDemo(quantidade: number): RegistroDemo[] {
  const rand = criarGerador(42);
  const registros: RegistroDemo[] = [];

  for (let i = 1; i <= quantidade; i++) {
    const nome = `${NOMES[Math.floor(rand() * NOMES.length)]} ${String(i).padStart(4, "0")}`;
    const categoria = CATEGORIAS[Math.floor(rand() * CATEGORIAS.length)];
    const status = STATUS[Math.floor(rand() * STATUS.length)];
    const valor = Math.round(rand() * 10000 * 100) / 100;
    const diasAtras = Math.floor(rand() * 720);
    const data = new Date(2026, 6, 16);
    data.setDate(data.getDate() - diasAtras);
    const atualizadoEm = data.toISOString().slice(0, 10);

    registros.push({ id: i, nome, categoria, status, valor, atualizadoEm });
  }

  return registros;
}
