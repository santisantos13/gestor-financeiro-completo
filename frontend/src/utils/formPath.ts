/**
 * Resolve um caminho tipo `"endereco.cep"` ou `"itens.0.valor"` dentro do
 * objeto `formState.errors` do React Hook Form — usado por todo `*Field`
 * genérico para achar a mensagem de erro do próprio campo sem depender de
 * nomes de campo sempre serem de primeiro nível. Puro, sem dependência de
 * RHF (RHF não exporta um `get` público estável entre versões).
 */
export function getByPath(source: unknown, path: string): unknown {
  return path
    .split(/[.[\]]+/)
    .filter(Boolean)
    .reduce<unknown>((acc, key) => {
      if (acc == null || typeof acc !== "object") return undefined;
      return (acc as Record<string, unknown>)[key];
    }, source);
}

/** Extrai `message` de um nó de erro do RHF (`FieldError`), se houver. */
export function getFieldErrorMessage(errors: unknown, name: string): string | undefined {
  const node = getByPath(errors, name);
  if (node && typeof node === "object" && "message" in node) {
    const message = (node as { message?: unknown }).message;
    return typeof message === "string" ? message : undefined;
  }
  return undefined;
}
