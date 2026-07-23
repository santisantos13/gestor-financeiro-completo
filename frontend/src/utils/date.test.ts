/**
 * `formatDate`/`formatDateTime` agora respeitam a preferência de formato de
 * data (`lib/preferencesStore.ts`) em vez de um `Intl.DateTimeFormat`
 * fixo em pt-BR - teste unitário puro (sem render de componente), prova a
 * lógica de montagem da string nos 3 formatos suportados e o reset para o
 * padrão entre testes (o store é module-level, não reseta sozinho).
 */
import { describe, it, expect, afterEach } from "vitest";
import { formatDate, formatDateTime } from "./date";
import { setFormatoData, FORMATO_DATA_PADRAO } from "../lib/preferencesStore";

describe("formatDate", () => {
  afterEach(() => {
    setFormatoData(FORMATO_DATA_PADRAO);
  });

  it("usa DD/MM/AAAA por padrão", () => {
    expect(formatDate("2026-03-05")).toBe("05/03/2026");
  });

  it("usa AAAA-MM-DD quando a preferência é essa", () => {
    setFormatoData("AAAA-MM-DD");
    expect(formatDate("2026-03-05")).toBe("2026-03-05");
  });

  it("usa MM/DD/AAAA quando a preferência é essa", () => {
    setFormatoData("MM/DD/AAAA");
    expect(formatDate("2026-03-05")).toBe("03/05/2026");
  });

  it("devolve a string original para ISO malformado", () => {
    expect(formatDate("não-é-uma-data")).toBe("não-é-uma-data");
  });
});

describe("formatDateTime", () => {
  afterEach(() => {
    setFormatoData(FORMATO_DATA_PADRAO);
  });

  it("formata data (conforme a preferência) + hora", () => {
    setFormatoData("AAAA-MM-DD");
    const resultado = formatDateTime("2026-03-05T14:30:00");
    expect(resultado).toMatch(/^2026-03-05 \d{2}:\d{2}$/);
  });
});
