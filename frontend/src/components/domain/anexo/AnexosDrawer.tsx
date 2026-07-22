import { useRef, useState } from "react";
import { Paperclip, Plus, Trash2, Upload } from "lucide-react";
import { Drawer } from "../../ui/Drawer";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { Skeleton } from "../../ui/Skeleton";
import { useAnexosPorTransacao, useCriarAnexo, useExcluirAnexo } from "../../../hooks/useAnexoQueries";
import { useToast } from "../../../hooks/useToast";
import { getErrorMessage } from "../../../utils/errors";
import { formatDateTime } from "../../../utils/date";
import { formatBytes } from "../../../utils/format";
import type { AnexoRead } from "../../../types/anexo";

export interface AnexosDrawerProps {
  transacaoId: number | null;
  transacaoDescricao?: string;
  onClose: () => void;
}

const FORM_VAZIO = { nomeOriginal: "", caminhoArquivo: "", mimeType: undefined as string | undefined, tamanhoBytes: undefined as number | undefined };

/**
 * Drawer de anexos de UMA Transação — mesma mecânica de
 * `FinanciamentoDrawer.tsx` (Tier 2, docs/analise-arquitetural-overlays.md).
 * Sem upload real de arquivo (o backend é metadados apenas, ver
 * docs/analise-arquitetural-anexo-frontend.md): "Selecionar arquivo" só lê
 * `File.name`/`File.type`/`File.size` do navegador para pré-preencher o
 * formulário — nenhum byte é lido ou enviado. `caminho_arquivo` continua
 * sendo texto livre editável pelo usuário (referência de onde o arquivo
 * está guardado de verdade).
 *
 * Exclusão usa confirmação INLINE por linha (não `ConfirmAction` por cima
 * do Drawer já aberto) — mesmo raciocínio anti-backdrop-duplicado de
 * `FinanciamentoDrawer`.
 */
export function AnexosDrawer({ transacaoId, transacaoDescricao, onClose }: AnexosDrawerProps) {
  const toast = useToast();
  const { data: anexos, isLoading } = useAnexosPorTransacao(transacaoId);
  const criarAnexo = useCriarAnexo();
  const excluirAnexo = useExcluirAnexo();

  const [adicionando, setAdicionando] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [confirmandoExcluirId, setConfirmandoExcluirId] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function selecionarArquivo(arquivo: File) {
    setForm({
      nomeOriginal: arquivo.name,
      caminhoArquivo: arquivo.name,
      mimeType: arquivo.type || undefined,
      tamanhoBytes: arquivo.size,
    });
  }

  function fecharFormulario() {
    setAdicionando(false);
    setForm(FORM_VAZIO);
    if (inputRef.current) inputRef.current.value = "";
  }

  function fecharDrawer() {
    fecharFormulario();
    setConfirmandoExcluirId(null);
    onClose();
  }

  async function salvarAnexo() {
    if (!transacaoId || !form.nomeOriginal.trim() || !form.caminhoArquivo.trim()) return;
    try {
      await criarAnexo.mutateAsync({
        transacao_id: transacaoId,
        nome_original: form.nomeOriginal.trim(),
        caminho_arquivo: form.caminhoArquivo.trim(),
        mime_type: form.mimeType,
        tamanho_bytes: form.tamanhoBytes,
      });
      toast.success("Anexo adicionado.");
      fecharFormulario();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function confirmarExcluir(anexo: AnexoRead) {
    if (!transacaoId) return;
    try {
      await excluirAnexo.mutateAsync({ id: anexo.id, transacaoId });
      toast.success(`Anexo "${anexo.nome_original}" removido.`);
      setConfirmandoExcluirId(null);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  return (
    <Drawer
      open={transacaoId != null}
      title="Anexos"
      description={transacaoDescricao}
      onClose={fecharDrawer}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : anexos && anexos.length > 0 ? (
          <ul className="space-y-1.5">
            {anexos.map((anexo) => (
              <li
                key={anexo.id}
                className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm"
              >
                {confirmandoExcluirId === anexo.id ? (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-text-secondary">Remover este anexo?</span>
                    <span className="flex shrink-0 gap-2">
                      <Button size="sm" variant="secondary" onClick={() => setConfirmandoExcluirId(null)}>
                        Cancelar
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        loading={excluirAnexo.isPending}
                        onClick={() => confirmarExcluir(anexo)}
                      >
                        Remover
                      </Button>
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-2">
                      <Paperclip size={14} className="shrink-0 text-text-tertiary" aria-hidden="true" />
                      <span className="min-w-0">
                        <span className="block truncate text-text-primary">{anexo.nome_original}</span>
                        <span className="block text-caption text-text-tertiary">
                          {formatDateTime(anexo.data_upload)}
                          {anexo.tamanho_bytes != null ? ` · ${formatBytes(anexo.tamanho_bytes)}` : ""}
                        </span>
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setConfirmandoExcluirId(anexo.id)}
                      aria-label={`Remover ${anexo.nome_original}`}
                      className="shrink-0 rounded-sm p-1.5 text-text-tertiary transition-colors duration-fast ease-out hover:bg-surface-3 hover:text-negative"
                    >
                      <Trash2 size={14} aria-hidden="true" />
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-md border border-dashed border-border py-6 text-center text-sm text-text-tertiary">
            Nenhum anexo nesta transação.
          </p>
        )}

        {adicionando ? (
          <div className="space-y-3 rounded-md border border-border-subtle bg-surface-2 p-3">
            <input
              ref={inputRef}
              type="file"
              className="sr-only"
              onChange={(event) => {
                const arquivo = event.target.files?.[0];
                if (arquivo) selecionarArquivo(arquivo);
              }}
            />
            <Button type="button" variant="secondary" size="sm" onClick={() => inputRef.current?.click()}>
              <Upload size={14} aria-hidden="true" />
              Selecionar arquivo (opcional)
            </Button>

            <div>
              <label className="mb-1 block text-caption text-text-tertiary">Nome do arquivo</label>
              <Input
                value={form.nomeOriginal}
                onChange={(event) => setForm((atual) => ({ ...atual, nomeOriginal: event.target.value }))}
                placeholder="comprovante.pdf"
              />
            </div>

            <div>
              <label className="mb-1 block text-caption text-text-tertiary">Caminho ou link</label>
              <Input
                value={form.caminhoArquivo}
                onChange={(event) => setForm((atual) => ({ ...atual, caminhoArquivo: event.target.value }))}
                placeholder="Link do Drive/Dropbox ou caminho local"
              />
              <p className="mt-1 text-caption text-text-tertiary">
                O app ainda não armazena o arquivo em si — só a referência de onde ele está
                guardado.
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button size="sm" variant="secondary" onClick={fecharFormulario}>
                Cancelar
              </Button>
              <Button
                size="sm"
                loading={criarAnexo.isPending}
                disabled={!form.nomeOriginal.trim() || !form.caminhoArquivo.trim()}
                onClick={salvarAnexo}
              >
                Salvar
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" size="sm" className="w-full" onClick={() => setAdicionando(true)}>
            <Plus size={14} aria-hidden="true" />
            Adicionar anexo
          </Button>
        )}
      </div>
    </Drawer>
  );
}
