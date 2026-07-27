import { describe, it, expect } from "vitest";
import { agruparCaudaLonga } from "./agruparCaudaLonga";

interface ItemTeste {
  nome: string;
  total: number;
}

describe("agruparCaudaLonga", () => {
  it("devolve a lista intacta quando está dentro do limite", () => {
    const itens: ItemTeste[] = [{ nome: "A", total: 10 }, { nome: "B", total: 5 }];
    expect(agruparCaudaLonga(itens, (i) => i.total, () => ({ nome: "Outros", total: 0 }), 6)).toEqual(itens);
  });

  it("agrupa a cauda além do limite num único item 'Outros'", () => {
    const itens: ItemTeste[] = [
      { nome: "A", total: 100 },
      { nome: "B", total: 80 },
      { nome: "C", total: 60 },
      { nome: "D", total: 10 },
      { nome: "E", total: 5 },
      { nome: "F", total: 3 },
      { nome: "G", total: 2 },
    ];
    const resultado = agruparCaudaLonga(
      itens,
      (i) => i.total,
      (soma, qtd) => ({ nome: `Outros (${qtd})`, total: soma }),
      6,
    );

    expect(resultado).toHaveLength(6);
    expect(resultado.slice(0, 5)).toEqual(itens.slice(0, 5));
    expect(resultado[5]).toEqual({ nome: "Outros (2)", total: 5 });
  });
});
