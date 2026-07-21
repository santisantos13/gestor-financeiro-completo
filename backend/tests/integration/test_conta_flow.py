"""Testes de integração do CRUD de Conta: TestClient + banco real (SQLite
em memória), cobrindo autenticação obrigatória, isolamento multi-tenant
(BOLA), soft delete e o cálculo de saldo_atual com Transacao/Transferencia
reais no banco (Transacao/Transferencia ainda não têm CRUD próprio nesta
etapa, então são inseridas direto via `db_session`, simulando dados que um
futuro endpoint de Transação criaria)."""
from datetime import date
from decimal import Decimal

from app.models import Transacao, Transferencia
from app.models.enums import StatusTransacao, TipoTransacao


def _usuario_id(client, headers):
    resposta = client.get("/auth/me", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["id"]


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente", saldo_inicial="100.00"):
    resposta = client.post("/contas", json={"nome": nome, "saldo_inicial": saldo_inicial}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_criar_conta_sem_autenticacao_retorna_401(client):
    resposta = client.post("/contas", json={"nome": "Conta Corrente"})
    assert resposta.status_code == 401


def test_criar_e_obter_conta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, nome="Nubank", saldo_inicial="500.00")

    assert conta["nome"] == "Nubank"
    assert conta["tipo"] == "CORRENTE"
    assert conta["saldo_inicial"] == "500.00"
    assert conta["saldo_atual"] == "500.00"
    assert conta["ativo"] is True

    resposta = client.get(f"/contas/{conta['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == conta["id"]


def test_criar_conta_com_nome_vazio_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/contas", json={"nome": ""}, headers=headers)
    assert resposta.status_code == 422


def test_saldo_atual_reflete_transacoes_pagas_transferencias_e_ignora_pendentes(client, db_session):
    headers = _registrar_e_logar(client)
    conta_origem = _criar_conta(client, headers, nome="Origem", saldo_inicial="1000.00")
    conta_destino = _criar_conta(client, headers, nome="Destino", saldo_inicial="0.00")

    usuario_id = _usuario_id(client, headers)

    # receita PAGA: soma
    db_session.add(
        Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.RECEITA,
            valor=Decimal("200.00"),
            data=date.today(),
            descricao="Salario",
            status=StatusTransacao.PAGO,
            conta_id=conta_origem["id"],
        )
    )
    # despesa PAGA: subtrai
    db_session.add(
        Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.DESPESA,
            valor=Decimal("50.00"),
            data=date.today(),
            descricao="Mercado",
            status=StatusTransacao.PAGO,
            conta_id=conta_origem["id"],
        )
    )
    # despesa PENDENTE: NAO deve afetar o saldo atual
    db_session.add(
        Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.DESPESA,
            valor=Decimal("999.00"),
            data=date.today(),
            descricao="Conta a pagar ainda",
            status=StatusTransacao.PENDENTE,
            conta_id=conta_origem["id"],
        )
    )
    # transferencia da origem para o destino: subtrai da origem, soma no destino
    db_session.add(
        Transferencia(
            usuario_id=usuario_id,
            conta_origem_id=conta_origem["id"],
            conta_destino_id=conta_destino["id"],
            valor=Decimal("300.00"),
            data=date.today(),
        )
    )
    db_session.commit()

    resposta_origem = client.get(f"/contas/{conta_origem['id']}", headers=headers)
    resposta_destino = client.get(f"/contas/{conta_destino['id']}", headers=headers)

    # 1000 (inicial) + 200 (receita paga) - 50 (despesa paga) - 300 (transferencia enviada)
    # a despesa PENDENTE de 999 nao entra
    assert resposta_origem.json()["saldo_atual"] == "850.00"
    # 0 (inicial) + 300 (transferencia recebida)
    assert resposta_destino.json()["saldo_atual"] == "300.00"


def test_listar_contas_retorna_apenas_as_do_usuario_autenticado(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    _criar_conta(client, headers_ana, nome="Conta da Ana")
    _criar_conta(client, headers_bruno, nome="Conta do Bruno")

    resposta = client.get("/contas", headers=headers_ana)
    assert resposta.status_code == 200
    nomes = [c["nome"] for c in resposta.json()]
    assert nomes == ["Conta da Ana"]


def test_obter_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    conta_ana = _criar_conta(client, headers_ana)

    resposta = client.get(f"/contas/{conta_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_atualizar_conta_parcial(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, nome="Nome Original", saldo_inicial="100.00")

    resposta = client.patch(f"/contas/{conta['id']}", json={"nome": "Nome Novo"}, headers=headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Nome Novo"
    assert corpo["saldo_inicial"] == "100.00"  # nao enviado, preservado


def test_atualizar_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)

    resposta = client.patch(f"/contas/{conta_ana['id']}", json={"nome": "Hackeado"}, headers=headers_bruno)
    assert resposta.status_code == 404


def test_desativar_conta_e_soft_delete(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    resposta = client.delete(f"/contas/{conta['id']}", headers=headers)
    assert resposta.status_code == 204

    # a conta continua acessivel diretamente por id (nao foi apagada)...
    resposta_get = client.get(f"/contas/{conta['id']}", headers=headers)
    assert resposta_get.status_code == 200
    assert resposta_get.json()["ativo"] is False

    # ...mas some da listagem padrao (que so mostra ativas)
    resposta_listagem = client.get("/contas", headers=headers)
    assert resposta_listagem.json() == []

    # e continua aparecendo se pedirmos explicitamente as inativas tambem
    resposta_todas = client.get("/contas?apenas_ativas=false", headers=headers)
    assert len(resposta_todas.json()) == 1


def test_desativar_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)

    resposta = client.delete(f"/contas/{conta_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


# ---- Exclusão definitiva (hard delete) - Etapa F10 ----


def test_excluir_conta_permanente_sem_vinculo_apaga_a_linha(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    resposta = client.delete(f"/contas/{conta['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    # diferente do soft delete: a conta REALMENTE some, nem com
    # apenas_ativas=false ela reaparece.
    resposta_get = client.get(f"/contas/{conta['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_conta_permanente_com_transacao_vinculada_retorna_422(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    usuario_id = _usuario_id(client, headers)

    db_session.add(
        Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.DESPESA,
            valor=Decimal("10.00"),
            data=date.today(),
            descricao="Qualquer coisa",
            status=StatusTransacao.PENDENTE,
            conta_id=conta["id"],
        )
    )
    db_session.commit()

    resposta = client.delete(f"/contas/{conta['id']}/permanente", headers=headers)
    assert resposta.status_code == 422

    # a conta continua existindo intacta apos o bloqueio
    resposta_get = client.get(f"/contas/{conta['id']}", headers=headers)
    assert resposta_get.status_code == 200


def test_excluir_conta_permanente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)

    resposta = client.delete(f"/contas/{conta_ana['id']}/permanente", headers=headers_bruno)
    assert resposta.status_code == 404


def test_excluir_conta_permanente_com_financiamento_vinculado_retorna_422(client):
    """Corrige um gap encontrado em `existe_vinculo` (ver
    docs/analise-arquitetural-exclusao-conta-com-historico.md):
    Financiamento/Empréstimo/ContaRecorrente/Parcelamento vinculados
    diretamente à conta (não via Transacao/Transferencia/Cartão) agora
    também bloqueiam a exclusão "segura" (apagar_vinculos=False)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    financiamento = client.post(
        "/financiamentos",
        json={
            "descricao": "Apartamento",
            "instituicao_financeira": "Banco X",
            "valor_financiado": "100000.00",
            "taxa_juros": "0.0150",
            "sistema_amortizacao": "PRICE",
            "num_parcelas": 24,
            "data_inicio": "2026-07-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    )
    assert financiamento.status_code == 201, financiamento.text

    resposta = client.delete(f"/contas/{conta['id']}/permanente", headers=headers)
    assert resposta.status_code == 422

    resposta_get = client.get(f"/contas/{conta['id']}", headers=headers)
    assert resposta_get.status_code == 200


# ---- Exclusão com apagar_vinculos=True (pedido explícito do usuário) ----
# docs/analise-arquitetural-exclusao-conta-com-historico.md


def test_excluir_conta_permanente_com_apagar_vinculos_remove_transacao_e_transferencia(
    client, db_session
):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    outra_conta = _criar_conta(client, headers, nome="Outra")
    usuario_id = _usuario_id(client, headers)

    db_session.add(
        Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.DESPESA,
            valor=Decimal("10.00"),
            data=date.today(),
            descricao="Mercado",
            status=StatusTransacao.PAGO,
            conta_id=conta["id"],
        )
    )
    db_session.commit()

    transferencia = client.post(
        "/transferencias",
        json={
            "conta_origem_id": conta["id"],
            "conta_destino_id": outra_conta["id"],
            "valor": "50.00",
            "data": "2026-07-15",
            "descricao": "Reserva",
        },
        headers=headers,
    ).json()

    # Sem apagar_vinculos ainda bloqueia, mesmo comportamento de sempre.
    resposta_bloqueada = client.delete(f"/contas/{conta['id']}/permanente", headers=headers)
    assert resposta_bloqueada.status_code == 422

    resposta = client.delete(
        f"/contas/{conta['id']}/permanente?apagar_vinculos=true", headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/contas/{conta['id']}", headers=headers).status_code == 404
    assert client.get(f"/transferencias/{transferencia['id']}", headers=headers).status_code == 404
    # a outra conta (não excluída) continua intacta
    assert client.get(f"/contas/{outra_conta['id']}", headers=headers).status_code == 200


def test_excluir_conta_permanente_com_apagar_vinculos_remove_cartao_e_seu_historico(client):
    """A cascata de Conta reaproveita a cascata inteira já implementada
    para Cartão (apaga faturas e transações do cartão junto) - não existe
    "trocar a conta de pagamento de um cartão" no sistema."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    cartao = client.post(
        "/cartoes",
        json={
            "nome": "Nubank",
            "conta_pagamento_id": conta["id"],
            "instituicao": "Nu Pagamentos",
            "bandeira": "MASTERCARD",
            "ultimos_quatro_digitos": "1234",
            "limite": "5000.00",
            "dia_fechamento": 10,
            "dia_vencimento": 17,
        },
        headers=headers,
    ).json()

    fatura = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-06-01"},
        headers=headers,
    ).json()

    resposta = client.delete(
        f"/contas/{conta['id']}/permanente?apagar_vinculos=true", headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/contas/{conta['id']}", headers=headers).status_code == 404
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).status_code == 404
    assert client.get(f"/faturas/{fatura['id']}", headers=headers).status_code == 404


def test_excluir_conta_permanente_com_apagar_vinculos_remove_financiamento_e_recorrencia(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    financiamento = client.post(
        "/financiamentos",
        json={
            "descricao": "Apartamento",
            "instituicao_financeira": "Banco X",
            "valor_financiado": "100000.00",
            "taxa_juros": "0.0150",
            "sistema_amortizacao": "PRICE",
            "num_parcelas": 24,
            "data_inicio": "2026-07-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()

    emprestimo = client.post(
        "/emprestimos",
        json={
            "descricao": "Empréstimo pessoal",
            "instituicao_financeira": "Banco X",
            "valor_liberado": "10000.00",
            "taxa_juros": "0.0150",
            "sistema_amortizacao": "PRICE",
            "num_parcelas": 12,
            "data_inicio": "2026-07-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()

    recorrente = client.post(
        "/contas-recorrentes",
        json={
            "descricao": "Aluguel",
            "valor": "1500.00",
            "tipo": "DESPESA",
            "dia_vencimento": 1,
            "data_inicio": "2026-01-01",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()

    resposta = client.delete(
        f"/contas/{conta['id']}/permanente?apagar_vinculos=true", headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/contas/{conta['id']}", headers=headers).status_code == 404
    assert client.get(f"/financiamentos/{financiamento['id']}", headers=headers).status_code == 404
    assert client.get(f"/emprestimos/{emprestimo['id']}", headers=headers).status_code == 404
    assert client.get(f"/contas-recorrentes/{recorrente['id']}", headers=headers).status_code == 404


def test_excluir_conta_permanente_com_apagar_vinculos_remove_parcelamento_da_conta(client):
    """Parcelamento direto na Conta (sem passar por Cartão): o cabeçalho
    tem que ser apagado junto, não só desvinculado -
    `ck_parcelamento_cartao_xor_conta` é XOR/NOT NULL em conjunto, não
    existe deixar `conta_id` nulo sozinho. Bug real corrigido em
    2026-07-21 ("excluir cartão/conta falha com Falha de conexão com o
    servidor"): esse cabeçalho ficava órfão silenciosamente no SQLite de
    desenvolvimento, mas bloqueava a exclusão da conta com `IntegrityError`
    no Postgres de produção, onde a FK é enforced de verdade."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    parcelamento = client.post(
        "/parcelamentos",
        json={
            "descricao": "Móveis",
            "valor_total": "900.00",
            "num_parcelas": 3,
            "data_inicio": "2026-06-15",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()
    assert parcelamento["conta_id"] == conta["id"]

    resposta = client.delete(
        f"/contas/{conta['id']}/permanente?apagar_vinculos=true", headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/contas/{conta['id']}", headers=headers).status_code == 404
    assert client.get(f"/parcelamentos/{parcelamento['id']}", headers=headers).status_code == 404


def test_excluir_conta_oculta_cofrinho_de_meta_sempre_bloqueia_mesmo_com_apagar_vinculos(client):
    """Conta oculta = cofrinho automático de uma Meta - a relação é
    invertida (a Meta é dona da conta). Nunca deve ser apagável
    diretamente, nem com apagar_vinculos=True - excluir a Meta é quem
    decide o destino correto do cofrinho."""
    headers = _registrar_e_logar(client)
    meta_resposta = client.post(
        "/metas",
        json={"descricao": "Viagem para o Japão", "valor_alvo": "15000.00"},
        headers=headers,
    )
    assert meta_resposta.status_code == 201, meta_resposta.text
    meta = meta_resposta.json()
    conta_id_cofrinho = meta["conta_id"]

    resposta = client.delete(
        f"/contas/{conta_id_cofrinho}/permanente?apagar_vinculos=true", headers=headers
    )
    assert resposta.status_code == 422

    resposta_get = client.get(f"/contas/{conta_id_cofrinho}", headers=headers)
    assert resposta_get.status_code == 200


# ---- Extrato (histórico expansível) - docs/analise-arquitetural-extrato-conta.md ----


def _mes_anterior(referencia: date) -> tuple[int, int]:
    if referencia.month == 1:
        return referencia.year - 1, 12
    return referencia.year, referencia.month - 1


def test_extrato_conta_categoriza_e_soma_cada_tipo_de_movimentacao(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, nome="Origem", saldo_inicial="1000.00")
    outra_conta = _criar_conta(client, headers, nome="Destino", saldo_inicial="0.00")
    usuario_id = _usuario_id(client, headers)
    hoje = date.today()

    db_session.add_all(
        [
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.RECEITA,
                valor=Decimal("500.00"),
                data=hoje,
                descricao="Salário",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("200.00"),
                data=hoje,
                descricao="Mercado",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("150.00"),
                data=hoje,
                descricao="Pagamento fatura Nubank",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
                fatura_paga_id=999,
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("300.00"),
                data=hoje,
                descricao="Parcela financiamento",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
                financiamento_id=777,
                numero_parcela=1,
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("100.00"),
                data=hoje,
                descricao="Parcela empréstimo",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
                emprestimo_id=888,
                numero_parcela=1,
            ),
            # PENDENTE: nunca aparece no extrato (não alterou o saldo ainda).
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("999.00"),
                data=hoje,
                descricao="Conta a pagar ainda",
                status=StatusTransacao.PENDENTE,
                conta_id=conta["id"],
            ),
            # importada=True: histórico pré-app, nunca alterou o saldo real.
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("9999.00"),
                data=hoje,
                descricao="Parcela já paga antes do app",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
                financiamento_id=777,
                numero_parcela=2,
                importada=True,
            ),
        ]
    )
    db_session.commit()

    transferencia_enviada = client.post(
        "/transferencias",
        json={
            "conta_origem_id": conta["id"],
            "conta_destino_id": outra_conta["id"],
            "valor": "250.00",
            "data": hoje.isoformat(),
            "descricao": "Reserva",
        },
        headers=headers,
    )
    assert transferencia_enviada.status_code == 201, transferencia_enviada.text

    transferencia_recebida = client.post(
        "/transferencias",
        json={
            "conta_origem_id": outra_conta["id"],
            "conta_destino_id": conta["id"],
            "valor": "80.00",
            "data": hoje.isoformat(),
            "descricao": "Estorno",
        },
        headers=headers,
    )
    assert transferencia_recebida.status_code == 201, transferencia_recebida.text

    # compra no cartão: NUNCA deve aparecer no extrato da Conta (pertence ao
    # Cartão até a fatura ser paga) - `conta_id` é nulo, `cartao_id` é o
    # cartão, então já fica fora só pelo filtro `conta_id = X`.
    cartao = client.post(
        "/cartoes",
        json={
            "nome": "Nubank",
            "conta_pagamento_id": conta["id"],
            "instituicao": "Nu Pagamentos",
            "bandeira": "MASTERCARD",
            "ultimos_quatro_digitos": "1234",
            "limite": "5000.00",
            "dia_fechamento": 10,
            "dia_vencimento": 17,
        },
        headers=headers,
    ).json()
    compra_cartao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "123.00",
            "data": hoje.isoformat(),
            "descricao": "Compra no cartão",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    assert compra_cartao.status_code == 201, compra_cartao.text

    resposta = client.get(f"/contas/{conta['id']}/extrato", headers=headers)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()

    categorias = {m["categoria"] for m in corpo["movimentacoes"]}
    assert categorias == {
        "RECEITA",
        "DESPESA",
        "PAGAMENTO_FATURA",
        "PAGAMENTO_FINANCIAMENTO",
        "PAGAMENTO_EMPRESTIMO",
        "TRANSFERENCIA_ENVIADA",
        "TRANSFERENCIA_RECEBIDA",
    }
    assert len(corpo["movimentacoes"]) == 7
    assert all("Compra no cartão" != m["descricao"] for m in corpo["movimentacoes"])
    assert all("antes do app" not in m["descricao"] for m in corpo["movimentacoes"])
    assert all("ainda" not in m["descricao"] for m in corpo["movimentacoes"])

    resumo = corpo["resumo"]
    assert resumo["saldo_inicial"] == "1000.00"
    # 500 (receita) + 80 (transferência recebida)
    assert resumo["entradas_periodo"] == "580.00"
    # 200 + 150 + 300 + 100 (transações) + 250 (transferência enviada)
    assert resumo["saidas_periodo"] == "1000.00"
    assert resumo["saldo_liquido_periodo"] == "-420.00"
    assert resumo["quantidade_movimentacoes"] == 7
    assert resumo["ultima_movimentacao"] == hoje.isoformat()
    # 1000 (inicial) + (500-200-150-300-100) transações pagas líquidas
    # - 250 (transferência enviada) + 80 (transferência recebida)
    assert resumo["saldo_atual"] == "580.00"


def test_extrato_conta_filtra_por_ano_e_mes(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    usuario_id = _usuario_id(client, headers)
    hoje = date.today()
    ano_anterior, mes_anterior = _mes_anterior(hoje)

    db_session.add_all(
        [
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.RECEITA,
                valor=Decimal("100.00"),
                data=hoje,
                descricao="Deste mês",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.RECEITA,
                valor=Decimal("200.00"),
                data=date(ano_anterior, mes_anterior, 1),
                descricao="Do mês anterior",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
        ]
    )
    db_session.commit()

    resposta_atual = client.get(f"/contas/{conta['id']}/extrato", headers=headers)
    assert [m["descricao"] for m in resposta_atual.json()["movimentacoes"]] == ["Deste mês"]

    resposta_anterior = client.get(
        f"/contas/{conta['id']}/extrato?ano={ano_anterior}&mes={mes_anterior}", headers=headers
    )
    assert [m["descricao"] for m in resposta_anterior.json()["movimentacoes"]] == ["Do mês anterior"]


def test_extrato_conta_resumo_mes_atual_independe_do_periodo_navegado(client, db_session):
    """`resumo_mes_atual` é sempre o mês corrente de verdade (`date.today()`)
    - navegar para outro período no `resumo` principal não deve mudá-lo."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    usuario_id = _usuario_id(client, headers)
    hoje = date.today()
    ano_anterior, mes_anterior = _mes_anterior(hoje)

    db_session.add(
        Transacao(
            usuario_id=usuario_id,
            tipo=TipoTransacao.RECEITA,
            valor=Decimal("500.00"),
            data=hoje,
            descricao="Salário deste mês",
            status=StatusTransacao.PAGO,
            conta_id=conta["id"],
        )
    )
    db_session.commit()

    resposta = client.get(
        f"/contas/{conta['id']}/extrato?ano={ano_anterior}&mes={mes_anterior}", headers=headers
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()

    # o período navegado (mês anterior) não tem nenhuma movimentação
    assert corpo["resumo"]["quantidade_movimentacoes"] == 0
    assert corpo["movimentacoes"] == []
    # mas o resumo do mês atual continua refletindo a receita real de hoje
    assert corpo["resumo_mes_atual"]["entradas_mes"] == "500.00"
    assert corpo["resumo_mes_atual"]["saldo_mes"] == "500.00"
    assert corpo["resumo_mes_atual"]["maior_entrada"]["descricao"] == "Salário deste mês"


def test_extrato_conta_maior_entrada_e_maior_saida_do_mes(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    usuario_id = _usuario_id(client, headers)
    hoje = date.today()

    db_session.add_all(
        [
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.RECEITA,
                valor=Decimal("300.00"),
                data=hoje,
                descricao="Salário",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.RECEITA,
                valor=Decimal("900.00"),
                data=hoje,
                descricao="Bônus",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("50.00"),
                data=hoje,
                descricao="Mercado",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
            Transacao(
                usuario_id=usuario_id,
                tipo=TipoTransacao.DESPESA,
                valor=Decimal("700.00"),
                data=hoje,
                descricao="Aluguel",
                status=StatusTransacao.PAGO,
                conta_id=conta["id"],
            ),
        ]
    )
    db_session.commit()

    resposta = client.get(f"/contas/{conta['id']}/extrato", headers=headers)
    assert resposta.status_code == 200, resposta.text
    resumo_mes = resposta.json()["resumo_mes_atual"]

    assert resumo_mes["maior_entrada"] == {"data": hoje.isoformat(), "descricao": "Bônus", "valor": "900.00"}
    assert resumo_mes["maior_saida"] == {"data": hoje.isoformat(), "descricao": "Aluguel", "valor": "700.00"}


def test_extrato_conta_transferencia_cancelada_nao_aparece(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    outra_conta = _criar_conta(client, headers, nome="Outra")

    transferencia = client.post(
        "/transferencias",
        json={
            "conta_origem_id": conta["id"],
            "conta_destino_id": outra_conta["id"],
            "valor": "50.00",
            "data": date.today().isoformat(),
            "descricao": "Cancelada depois",
        },
        headers=headers,
    ).json()

    cancelar = client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)
    assert cancelar.status_code == 200, cancelar.text

    resposta = client.get(f"/contas/{conta['id']}/extrato", headers=headers)
    assert resposta.json()["movimentacoes"] == []


def test_extrato_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)

    resposta = client.get(f"/contas/{conta_ana['id']}/extrato", headers=headers_bruno)
    assert resposta.status_code == 404


def test_extrato_conta_sem_movimentacao_devolve_listas_vazias_e_zeros(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="300.00")

    resposta = client.get(f"/contas/{conta['id']}/extrato", headers=headers)
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()

    assert corpo["movimentacoes"] == []
    assert corpo["resumo"]["saldo_atual"] == "300.00"
    assert corpo["resumo"]["saldo_inicial"] == "300.00"
    assert corpo["resumo"]["entradas_periodo"] == "0.00"
    assert corpo["resumo"]["saidas_periodo"] == "0.00"
    assert corpo["resumo"]["quantidade_movimentacoes"] == 0
    assert corpo["resumo"]["ultima_movimentacao"] is None
    assert corpo["resumo_mes_atual"]["maior_entrada"] is None
    assert corpo["resumo_mes_atual"]["maior_saida"] is None
