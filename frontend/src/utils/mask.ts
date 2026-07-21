/**
 * Infraestrutura de máscara — Etapa F5 (Sistema de Formulários). Puramente
 * funções de string/dígito, sem biblioteca pesada (`Intl.NumberFormat`
 * nativo cobre a formatação pt-BR). Cada campo mascarado guarda o dígito
 * puro digitado pelo usuário e deriva tanto o texto exibido quanto o valor
 * "real" (a forma que vai para o Zod/RHF/backend) a partir dele — nunca o
 * inverso, para não haver duas fontes de verdade sobre o que foi digitado.
 * Ver docs/analise-arquitetural-frontend.md, seção 12 (`CurrencyInput` como
 * primitivo de máscara reutilizável).
 */

const numberFormatter = new Intl.NumberFormat("pt-BR");

/** Remove tudo que não é dígito 0-9. */
export function onlyDigits(value: string): string {
  return value.replace(/\D/g, "");
}

/**
 * Formata uma sequência de dígitos como decimal de casas fixas, estilo
 * "digitação de calculadora" (os últimos `decimalPlaces` dígitos são
 * sempre a parte decimal — digitar da esquerda para a direita empurra o
 * valor, como em um caixa eletrônico). Ex.: `decimalPlaces=2`,
 * digits="12345" → "123,45". Sem separador de milhar quando
 * `groupThousands` é `false` (usado por `PercentageField`, que nunca passa
 * de 3 dígitos inteiros).
 */
export function formatDigitsAsFixedDecimal(
  digits: string,
  decimalPlaces: number,
  groupThousands = true,
): string {
  const semZerosEsquerda = digits.replace(/^0+(?=\d)/, "");
  if (semZerosEsquerda === "") return "";

  const comZeroPadding = semZerosEsquerda.padStart(decimalPlaces + 1, "0");
  const parteInteira = comZeroPadding.slice(0, comZeroPadding.length - decimalPlaces) || "0";
  const parteDecimal = decimalPlaces > 0 ? comZeroPadding.slice(-decimalPlaces) : "";

  const inteiroFormatado = groupThousands
    ? numberFormatter.format(BigInt(parteInteira))
    : parteInteira;

  return decimalPlaces > 0 ? `${inteiroFormatado},${parteDecimal}` : inteiroFormatado;
}

/** Mesma lógica de `formatDigitsAsFixedDecimal`, mas devolve a forma
 * "backend" (`.` como separador decimal, sem separador de milhar) — ex.
 * digits="12345", decimalPlaces=2 → "123.45". String vazia quando não há
 * dígito nenhum (campo vazio, nunca "0.00" forçado). */
export function digitsToDecimalString(digits: string, decimalPlaces: number): string {
  const semZerosEsquerda = digits.replace(/^0+(?=\d)/, "");
  if (semZerosEsquerda === "") return "";

  const comZeroPadding = semZerosEsquerda.padStart(decimalPlaces + 1, "0");
  const parteInteira = comZeroPadding.slice(0, comZeroPadding.length - decimalPlaces) || "0";
  const parteDecimal = decimalPlaces > 0 ? comZeroPadding.slice(-decimalPlaces) : "";

  return decimalPlaces > 0 ? `${parteInteira}.${parteDecimal}` : parteInteira;
}

/** Caminho inverso de `digitsToDecimalString` — usado para inicializar o
 * display de um campo mascarado a partir de um valor já existente no
 * formulário (ex. editando um registro). "123.45" → "12345". */
export function decimalStringToDigits(value: string, decimalPlaces: number): string {
  if (!value) return "";
  const numero = Number(value);
  if (Number.isNaN(numero)) return "";
  return Math.round(Math.abs(numero) * 10 ** decimalPlaces).toString();
}

// ---------------------------------------------------------------------
// Data (DD/MM/AAAA digitado, ISO "AAAA-MM-DD" como valor real)
// ---------------------------------------------------------------------

/** Aplica a máscara `DD/MM/AAAA` progressivamente enquanto o usuário
 * digita (máximo 8 dígitos). */
export function digitsToDateDisplay(digits: string): string {
  const d = digits.slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

/** Converte 8 dígitos DDMMAAAA num ISO "AAAA-MM-DD" válido — string vazia
 * se incompleto ou se a data não existe no calendário (ex. 31/02). */
export function dateDigitsToIso(digits: string): string {
  if (digits.length !== 8) return "";
  const dia = Number(digits.slice(0, 2));
  const mes = Number(digits.slice(2, 4));
  const ano = Number(digits.slice(4, 8));
  if (mes < 1 || mes > 12 || dia < 1) return "";

  const data = new Date(ano, mes - 1, dia);
  const valida = data.getFullYear() === ano && data.getMonth() === mes - 1 && data.getDate() === dia;
  if (!valida) return "";

  return `${String(ano).padStart(4, "0")}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
}

/** Caminho inverso — "AAAA-MM-DD" → "DDMMAAAA" (para inicializar o display
 * a partir de um valor ISO já existente). */
export function isoToDateDigits(iso: string): string {
  const partes = iso.split("-");
  if (partes.length !== 3) return "";
  const [ano, mes, dia] = partes;
  if (!ano || !mes || !dia) return "";
  return `${dia.padStart(2, "0")}${mes.padStart(2, "0")}${ano.padStart(4, "0")}`;
}

// ---------------------------------------------------------------------
// Hora (HH:MM digitado)
// ---------------------------------------------------------------------

export function digitsToTimeDisplay(digits: string): string {
  const d = digits.slice(0, 4);
  if (d.length <= 2) return d;
  return `${d.slice(0, 2)}:${d.slice(2)}`;
}

/** 4 dígitos HHMM → "HH:MM" válido, string vazia se incompleto/inválido. */
export function timeDigitsToValue(digits: string): string {
  if (digits.length !== 4) return "";
  const hora = Number(digits.slice(0, 2));
  const minuto = Number(digits.slice(2, 4));
  if (hora > 23 || minuto > 59) return "";
  return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
}

export function valueToTimeDigits(value: string): string {
  return onlyDigits(value).slice(0, 4);
}

// ---------------------------------------------------------------------
// Combinação data + hora (DateTimeField)
// ---------------------------------------------------------------------

/** Junta uma data ISO e uma hora "HH:MM" num datetime local
 * "AAAA-MM-DDTHH:MM" — string vazia se qualquer uma das partes faltar
 * (nunca um datetime parcialmente preenchido). */
export function joinIsoDateTime(isoDate: string, time: string): string {
  if (!isoDate || !time) return "";
  return `${isoDate}T${time}`;
}

export function splitIsoDateTime(isoDateTime: string): { date: string; time: string } {
  if (!isoDateTime) return { date: "", time: "" };
  const [date = "", time = ""] = isoDateTime.split("T");
  return { date, time: time.slice(0, 5) };
}
