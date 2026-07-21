"""Apaga usuarios de teste (e todos os dados vinculados a eles) do banco
financas.db.

IMPORTANTE - leia antes de rodar:
  1. Feche o app primeiro (parar.bat na raiz do projeto). Rodar isto com o
     backend ainda de pe pode falhar com "database is locked".
  2. Este projeto NUNCA liga PRAGMA foreign_keys=ON na conexao do FastAPI
     (decisao deliberada documentada no codigo) - por isso um DELETE direto
     sem essa pragma NAO apaga em cascata, so deixaria linhas orfas
     espalhadas em contas/cartoes/transacoes/faturas/tags/categorias/metas
     etc. Este script liga a pragma explicitamente so para esta conexao,
     fazendo os `ondelete="CASCADE"` ja declarados no schema (ver
     app/models/*.py, ForeignKey("usuarios.id", ondelete="CASCADE"))
     funcionarem de verdade - apaga o usuario E tudo que pertence a ele, em
     qualquer tabela, de uma vez. Testado numa copia do banco real antes de
     ser entregue: zero linhas orfas depois do DELETE.
  3. Isto e IRREVERSIVEL. Faca backup do arquivo antes se tiver duvida:
     copie backend/financas.db para outro lugar antes de confirmar.

Uso: de duplo clique em apagar_usuarios_teste.bat (que chama este script),
ou rode "python apagar_usuarios_teste.py" a partir desta pasta.
"""
import sqlite3
import sys
from pathlib import Path

# IDs a apagar - ajuste aqui se os IDs certos forem outros.
# id=3 "Santhiago 2" (santiagosantos0201@gmail.com), id=4 "test" (email.test@gmail.com)
IDS_PARA_APAGAR = [3, 4]

# Trava de seguranca: nunca deixa apagar o id 1 (conta principal conhecida:
# santiagosantos2021@gmail.com) mesmo que IDS_PARA_APAGAR seja editado sem querer.
ID_PROTEGIDO = 1

DB_PATH = Path(__file__).resolve().parent.parent / "backend" / "financas.db"


def main() -> None:
    if ID_PROTEGIDO in IDS_PARA_APAGAR:
        print(f"ERRO: id {ID_PROTEGIDO} esta na lista de apagar - abortando por seguranca.")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"ERRO: nao encontrei o banco em {DB_PATH}")
        sys.exit(1)

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    print(f"Banco: {DB_PATH}\n")
    print("Usuarios encontrados para os IDs informados:\n")
    encontrados = []
    for uid in IDS_PARA_APAGAR:
        row = cur.execute("SELECT id, nome, email FROM usuarios WHERE id = ?", (uid,)).fetchone()
        if row:
            encontrados.append(row)
            print(f"  id={row[0]}  nome={row[1]!r}  email={row[2]!r}")
        else:
            print(f"  id={uid}  (nao encontrado - sera ignorado)")

    if not encontrados:
        print("\nNenhum dos IDs informados existe no banco. Nada a fazer.")
        return

    print(
        "\nIsto vai apagar PERMANENTEMENTE esses usuarios e TODOS os dados "
        "vinculados a eles (contas, cartoes, faturas, transacoes, tags, "
        "categorias personalizadas, metas, financiamentos, emprestimos, "
        "parcelamentos, transferencias, sessoes, etc). Nao pode ser desfeito."
    )
    resposta = input("\nDigite CONFIRMAR (em maiusculas) para prosseguir: ")
    if resposta != "CONFIRMAR":
        print("Cancelado - nada foi apagado.")
        return

    ids_reais = [row[0] for row in encontrados]
    placeholders = ",".join("?" * len(ids_reais))
    cur.execute(f"DELETE FROM usuarios WHERE id IN ({placeholders})", ids_reais)
    con.commit()
    print(f"\nPronto: {cur.rowcount} usuario(s) apagado(s), com todos os dados vinculados.")
    con.close()


if __name__ == "__main__":
    main()
