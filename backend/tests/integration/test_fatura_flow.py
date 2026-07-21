"""Testes de integração do CRUD de Fatura: TestClient + banco real (SQLite
em memória). Cobre isolamento entre usuários (posse transitiva via
Cartão), derivação de datas do ciclo, unicidade (cartão, mês), cálculo de
valor_total/status a partir de Transacao reais inseridas no banco, e as
ações de negócio (fechar, registrar pagamento, excluir) via HTTP real.
"""
from datetime import date
from decimal import Decimal

from app.models import Transacao
from app.models.enums import TipoTransacao


def _mes_referencia_com_vencimento_futuro() -> str:
    """Bug real encontrado na varredura de 2026-07: `test_fechar_fatura_
    congela_valor_total`/`test_registrar_pagamento_parcial_e_depois_total`
    usavam `mes_referencia="2026-07-01"` fixo (vencimento dia 17 do
    cartão fake), o que `FaturaService._derivar_status` compara com
    `date.today()` pra decidir ATRASADA - bomba-relógio que quebrava
    sozinha assim que o relógio real passasse de 17/07/2026. Mês seguinte
    ao atual garante vencimento sempre no futuro."""
    hoje = date.today()
    if hoje.month == 12:
        return f"{hoje.year + 1}-01-01"
    return f"{hoje.year}-{hoje.month + 1:02d}-01"


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente"):
    resposta = client.post("/contas", json={"nome": nome}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_cartao(client, headers, conta_id, nome="Nubank", dia_fechamento=10, dia_vencimento=17):
    payload = {
        "nome": nome,
        "conta_pagamento_id": conta_id,
        "instituicao": "Nu Pagamentos",
        "bandeira": "MASTERCARD",
        "ultimos_quatro_digitos": "1234",
        "limite": "5000.00",
        "dia_fechamento": dia_fechamento,
        "dia_vencimento": dia_vencimento,
    }
    resposta = client.post("/cartoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_fatura(client, headers, cartao_id, mes_referencia="2026-07-01"):
    resposta = client.post(
        "/faturas", json={"cartao_id": cartao_id, "mes_referencia": mes_referencia}, headers=headers
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _importar_fatura(client, headers, cartao_id, mes_referencia="2026-05-01", valor_total="450.00"):
    resposta = client.post(
        "/faturas/importar",
        json={"cartao_id": cartao_id, "mes_referencia": mes_referencia, "valor_total": valor_total},
        headers=headers,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _usuario_id(client, headers):
    return client.get("/auth/me", headers=headers).json()["id"]


def test_criar_fatura_sem_autenticacao_retorna_401(client):
    resposta = client.post("/faturas", json={"cartao_id": 1, "mes_referencia": "2026-07-01"})
    assert resposta.status_code == 401


def test_criar_e_obter_fatura(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)

    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-07-01")

    assert fatura["cartao_id"] == cartao["id"]
    assert fatura["mes_referencia"] == "2026-07-01"
    assert fatura["data_fechamento"] == "2026-07-10"
    assert fatura["data_vencimento"] == "2026-07-17"
    assert fatura["status"] == "ABERTA"
    assert fatura["valor_total"] == "0.00" or fatura["valor_total"] == "0"
    assert fatura["valor_pago"] == "0.00" or fatura["valor_pago"] == "0"

    resposta = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == fatura["id"]


def test_criar_fatura_com_mes_referencia_nao_e_primeiro_dia_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = client.post(
        "/faturas", json={"cartao_id": cartao["id"], "mes_referencia": "2026-07-15"}, headers=headers
    )
    assert resposta.status_code == 422


def test_criar_fatura_com_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)
    cartao_bruno = _criar_cartao(client, headers_bruno, conta_bruno["id"])

    resposta = client.post(
        "/faturas",
        json={"cartao_id": cartao_bruno["id"], "mes_referencia": "2026-07-01"},
        headers=headers_ana,
    )
    assert resposta.status_code == 404


def test_criar_fatura_com_cartao_inexistente_retorna_404(client):
    headers = _registrar_e_logar(client)
    resposta = client.post(
        "/faturas", json={"cartao_id": 99999, "mes_referencia": "2026-07-01"}, headers=headers
    )
    assert resposta.status_code == 404


def test_criar_fatura_duplicada_mesmo_cartao_mesmo_mes_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-07-01")

    resposta = client.post(
        "/faturas", json={"cartao_id": cartao["id"], "mes_referencia": "2026-07-01"}, headers=headers
    )
    assert resposta.status_code == 409


def test_criar_fatura_com_vencimento_no_mes_seguinte(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=28, dia_vencimento=5)

    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-07-01")

    assert fatura["data_fechamento"] == "2026-07-28"
    assert fatura["data_vencimento"] == "2026-08-05"


def test_listar_faturas_retorna_apenas_as_do_cartao_informado(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao_a = _criar_cartao(client, headers, conta["id"], nome="Cartao A")
    cartao_b = _criar_cartao(client, headers, conta["id"], nome="Cartao B")
    _criar_fatura(client, headers, cartao_a["id"], mes_referencia="2026-07-01")
    _criar_fatura(client, headers, cartao_b["id"], mes_referencia="2026-07-01")

    resposta = client.get(f"/faturas?cartao_id={cartao_a['id']}", headers=headers)
    assert resposta.status_code == 200
    faturas = resposta.json()
    assert len(faturas) == 1
    assert faturas[0]["cartao_id"] == cartao_a["id"]


def test_listar_faturas_com_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)
    cartao_bruno = _criar_cartao(client, headers_bruno, conta_bruno["id"])

    resposta = client.get(f"/faturas?cartao_id={cartao_bruno['id']}", headers=headers_ana)
    assert resposta.status_code == 404


def test_obter_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(client, headers_ana, cartao_ana["id"])

    resposta = client.get(f"/faturas/{fatura_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_valor_total_aberta_reflete_transacoes_reais_do_ciclo(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-07-01")
    usuario_id = _usuario_id(client, headers)

    compra = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("120.50"),
        data=date(2026, 7, 3),
        descricao="Compra no cartao",
        cartao_id=cartao["id"],
        fatura_id=fatura["id"],
    )
    db_session.add(compra)
    db_session.commit()

    resposta = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["valor_total"] == "120.50"
    assert resposta.json()["status"] == "ABERTA"


def test_fechar_fatura_congela_valor_total(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    usuario_id = _usuario_id(client, headers)

    compra = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("200.00"),
        data=date(2026, 7, 3),
        descricao="Compra",
        cartao_id=cartao["id"],
        fatura_id=fatura["id"],
    )
    db_session.add(compra)
    db_session.commit()

    resposta = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "FECHADA"
    assert corpo["valor_total"] == "200.00"

    resposta_get = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta_get.json()["valor_total"] == "200.00"


def test_fechar_fatura_ja_fechada_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)
    assert resposta.status_code == 422


def test_fechar_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(client, headers_ana, cartao_ana["id"])

    resposta = client.post(f"/faturas/{fatura_ana['id']}/fechar", headers=headers_bruno)
    assert resposta.status_code == 404


def test_registrar_pagamento_parcial_e_depois_total(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    usuario_id = _usuario_id(client, headers)

    compra = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("50.00"),
        data=date(2026, 7, 3),
        descricao="Compra",
        cartao_id=cartao["id"],
        fatura_id=fatura["id"],
    )
    db_session.add(compra)
    db_session.commit()
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta_parcial = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "30.00", "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta_parcial.status_code == 201
    assert resposta_parcial.json()["valor_pago"] == "30.00"
    assert resposta_parcial.json()["status"] == "PARCIALMENTE_PAGA"

    resposta_final = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "20.00", "data": "2026-07-22"},
        headers=headers,
    )
    assert resposta_final.status_code == 201
    assert resposta_final.json()["valor_pago"] == "50.00"
    assert resposta_final.json()["status"] == "PAGA"


def test_registrar_pagamento_em_fatura_aberta_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])  # ainda ABERTA

    resposta = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "10.00", "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta.status_code == 422


def test_registrar_pagamento_de_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(client, headers_ana, cartao_ana["id"])
    client.post(f"/faturas/{fatura_ana['id']}/fechar", headers=headers_ana)

    resposta = client.post(
        f"/faturas/{fatura_ana['id']}/pagamentos",
        json={"valor": "10.00", "data": "2026-07-20"},
        headers=headers_bruno,
    )
    assert resposta.status_code == 404


def test_pagamento_completo_muda_status_para_paga(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])
    usuario_id = _usuario_id(client, headers)

    compra = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("100.00"),
        data=date(2026, 7, 3),
        descricao="Compra",
        cartao_id=cartao["id"],
        fatura_id=fatura["id"],
    )
    db_session.add(compra)
    db_session.commit()

    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "100.00", "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "PAGA"


def test_excluir_fatura_aberta_sem_transacoes(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])

    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_fatura_fechada_sem_transacoes_retorna_204(client):
    # Ciclo fechado por engano (sem nenhuma compra) - sem histórico real,
    # a exclusão continua permitida mesmo já FECHADA (regra relaxada:
    # o que importa é estar vazia, não o status).
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_fatura_aberta_com_transacao_vinculada_desvincula_sem_apagar(client, db_session):
    """Mudança de regra (2026-07-24, pedido do usuário): ter uma compra
    vinculada não bloqueia mais a exclusão da fatura - o usuário precisa
    poder desfazer/corrigir uma fatura cadastrada errada mesmo já tendo
    lançado uma compra nela. A transação nunca é apagada junto - só perde o
    vínculo (`fatura_id` volta a `None`), continua existindo normalmente em
    Transações."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])
    usuario_id = _usuario_id(client, headers)

    compra = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("50.00"),
        data=date(2026, 7, 3),
        descricao="Compra",
        cartao_id=cartao["id"],
        fatura_id=fatura["id"],
    )
    db_session.add(compra)
    db_session.commit()
    db_session.refresh(compra)

    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get_fatura = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta_get_fatura.status_code == 404

    resposta_get_transacao = client.get(f"/transacoes/{compra.id}", headers=headers)
    assert resposta_get_transacao.status_code == 200
    assert resposta_get_transacao.json()["fatura_id"] is None


def test_excluir_fatura_fechada_com_transacao_vinculada_desvincula_sem_apagar(client, db_session):
    # Independente do status, o comportamento é o mesmo: desvincula, nunca
    # apaga a transação.
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])
    usuario_id = _usuario_id(client, headers)

    compra = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("50.00"),
        data=date(2026, 7, 3),
        descricao="Compra",
        cartao_id=cartao["id"],
        fatura_id=fatura["id"],
    )
    db_session.add(compra)
    db_session.commit()
    db_session.refresh(compra)

    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get_transacao = client.get(f"/transacoes/{compra.id}", headers=headers)
    assert resposta_get_transacao.status_code == 200
    assert resposta_get_transacao.json()["fatura_id"] is None


def test_excluir_fatura_com_pagamento_vinculado_desvincula_sem_apagar(client):
    """Este era o caso concreto reportado pelo usuário: uma fatura já
    parcialmente/totalmente paga não podia ser excluída de jeito nenhum -
    ruim quando o valor foi lançado errado e o usuário só percebe depois de
    já ter registrado o pagamento. O pagamento (`fatura_paga_id`) continua
    existindo como uma despesa normal na conta de pagamento, só sem mais
    vínculo com o ciclo excluído."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta_pagamento = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "50.00", "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta_pagamento.status_code == 201

    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get_fatura = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta_get_fatura.status_code == 404

    resposta_transacoes = client.get(f"/transacoes?conta_id={conta['id']}", headers=headers)
    pagamentos = [t for t in resposta_transacoes.json() if t["descricao"].startswith("Pagamento de fatura")]
    assert len(pagamentos) == 1
    assert pagamentos[0]["fatura_paga_id"] is None


# --- importar (fatura histórica) --------------------------------------------

def test_importar_fatura_sem_autenticacao_retorna_401(client):
    resposta = client.post(
        "/faturas/importar", json={"cartao_id": 1, "mes_referencia": "2026-05-01", "valor_total": "100.00"}
    )
    assert resposta.status_code == 401


def test_importar_fatura_nasce_fechada_com_valor_total_informado(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    fatura = _importar_fatura(client, headers, cartao["id"], mes_referencia="2026-05-01", valor_total="450.00")

    assert fatura["status"] in ("FECHADA", "ATRASADA")  # nunca ABERTA
    assert fatura["valor_total"] == "450.00"
    assert fatura["importada"] is True
    assert fatura["valor_pago"] == "0.00"


def test_importar_fatura_com_ciclo_ainda_nao_fechado_retorna_422(client):
    """Pedido do usuário (2026-07-20): importar é para ciclo HISTÓRICO, já
    encerrado - um mes_referencia cujo fechamento ainda não chegou não pode
    nascer FECHADA (não faz sentido "fechar" um ciclo futuro). Para esse
    caso o caminho correto é fatura normal + ajuste manual."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = client.post(
        "/faturas/importar",
        json={
            "cartao_id": cartao["id"],
            "mes_referencia": _mes_referencia_com_vencimento_futuro(),
            "valor_total": "300.00",
        },
        headers=headers,
    )
    assert resposta.status_code == 422, resposta.text


# --- ajuste-manual (saldo já usado, sem Transacao) --------------------------

def test_ajustar_saldo_inicial_sem_autenticacao_retorna_401(client):
    resposta = client.patch("/faturas/1/ajuste-manual", json={"ajuste_manual": "100.00"})
    assert resposta.status_code == 401


def test_ajustar_saldo_inicial_em_fatura_aberta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())

    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "800.00"}, headers=headers
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["ajuste_manual"] == "800.00"
    assert corpo["valor_total"] == "800.00"


def test_ajustar_saldo_inicial_reflete_no_limite_disponivel_do_cartao(client):
    """O ponto central do pedido do usuário: o saldo declarado precisa
    consumir limite exatamente como uma compra real consumiria, mesmo sem
    nenhuma Transacao por trás."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())

    cartao_antes = client.get(f"/cartoes/{cartao['id']}", headers=headers).json()
    assert cartao_antes["limite_disponivel"] == "5000.00"

    client.patch(f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "800.00"}, headers=headers)

    cartao_depois = client.get(f"/cartoes/{cartao['id']}", headers=headers).json()
    assert cartao_depois["limite_disponivel"] == "4200.00"


def test_ajustar_saldo_inicial_soma_com_transacoes_reais_no_limite_disponivel(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())

    compra = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "150.00",
            "data": fatura["mes_referencia"],
            "descricao": "Compra",
            "status": "PAGO",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    assert compra.status_code == 201, compra.text

    client.patch(f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "800.00"}, headers=headers)

    cartao_depois = client.get(f"/cartoes/{cartao['id']}", headers=headers).json()
    assert cartao_depois["limite_disponivel"] == "4050.00"  # 5000 - 150 - 800


def test_ajustar_saldo_inicial_editar_substitui_valor_anterior(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())

    client.patch(f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "500.00"}, headers=headers)
    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "200.00"}, headers=headers
    )

    assert resposta.json()["ajuste_manual"] == "200.00"
    assert resposta.json()["valor_total"] == "200.00"


def test_ajustar_saldo_inicial_com_valor_negativo_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())

    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "-10.00"}, headers=headers
    )
    assert resposta.status_code == 422


def test_ajustar_saldo_inicial_em_fatura_fechada_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "100.00"}, headers=headers
    )
    assert resposta.status_code == 422


def test_ajustar_saldo_inicial_de_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(
        client, headers_ana, cartao_ana["id"], mes_referencia=_mes_referencia_com_vencimento_futuro()
    )

    resposta = client.patch(
        f"/faturas/{fatura_ana['id']}/ajuste-manual", json={"ajuste_manual": "100.00"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


def test_fechar_fatura_congela_ajuste_manual_no_valor_total(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    client.patch(f"/faturas/{fatura['id']}/ajuste-manual", json={"ajuste_manual": "300.00"}, headers=headers)

    resposta = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["valor_total"] == "300.00"
    # `fechar()` zera `ajuste_manual` ao congelar - fica livre para uma
    # correção pós-fechamento nova (`ajustar_valor_pos_fechamento`), sem
    # nunca dobrar o valor já embutido no `valor_total` congelado acima.
    assert resposta.json()["ajuste_manual"] in ("0", "0.00")


# --- ajustar_valor_pos_fechamento (compra esquecida numa fatura já fechada) -
# Pedido explícito do usuário (2026-07-20): "quero adicionar uma transação em
# uma fatura que já foi fechada e paga, porém tinha esquecido dela antes".

def test_ajustar_valor_pos_fechamento_soma_ao_valor_total(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "80.00"}, headers=headers
    )

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["valor_total"] == "80.00"
    assert corpo["ajuste_manual"] == "80.00"


def test_ajustar_valor_pos_fechamento_acumula_em_chamadas_sucessivas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)
    client.patch(f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "80.00"}, headers=headers)

    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "20.00"}, headers=headers
    )

    assert resposta.json()["valor_total"] == "100.00"


def test_ajustar_valor_pos_fechamento_reflete_no_limite_disponivel_do_cartao(client):
    """A compra esquecida não vira Transacao, mas precisa consumir limite
    igual uma compra real consumiria (`CartaoRepository.
    somar_gastos_nao_pagos` já soma `Fatura.ajuste_manual` de toda fatura
    não paga, sem filtro de status)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    antes = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert antes.json()["limite_disponivel"] == "5000.00"

    client.patch(f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "80.00"}, headers=headers)

    depois = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert depois.json()["limite_disponivel"] == "4920.00"


def test_ajustar_valor_pos_fechamento_em_fatura_paga_deixa_de_ser_paga(client):
    """Efeito colateral esperado: o valor pago não muda, mas o total
    aumenta - a fatura estava PAGA e passa a ter saldo em aberto."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    mes_referencia = _mes_referencia_com_vencimento_futuro()
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=mes_referencia)
    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "100.00",
            "data": mes_referencia[:8] + "02",
            "descricao": "Compra real",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    fechada = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)
    assert fechada.json()["valor_total"] == "100.00"
    client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "100.00", "data": mes_referencia[:8] + "05"},
        headers=headers,
    )
    paga = client.get(f"/faturas/{fatura['id']}", headers=headers)
    assert paga.json()["status"] == "PAGA"

    ajustada = client.patch(
        f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "40.00"}, headers=headers
    )

    assert ajustada.json()["status"] != "PAGA"
    assert ajustada.json()["valor_total"] == "140.00"
    assert ajustada.json()["valor_pago"] == "100.00"


def test_ajustar_valor_pos_fechamento_em_fatura_aberta_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())

    resposta = client.patch(
        f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "10.00"}, headers=headers
    )
    assert resposta.status_code == 422


def test_ajustar_valor_pos_fechamento_com_valor_zero_ou_negativo_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"], mes_referencia=_mes_referencia_com_vencimento_futuro())
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)

    resposta_zero = client.patch(
        f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "0.00"}, headers=headers
    )
    assert resposta_zero.status_code == 422

    resposta_negativa = client.patch(
        f"/faturas/{fatura['id']}/ajuste-pos-fechamento", json={"valor": "-10.00"}, headers=headers
    )
    assert resposta_negativa.status_code == 422


def test_ajustar_valor_pos_fechamento_de_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana3@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno3@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(
        client, headers_ana, cartao_ana["id"], mes_referencia=_mes_referencia_com_vencimento_futuro()
    )
    client.post(f"/faturas/{fatura_ana['id']}/fechar", headers=headers_ana)

    resposta = client.patch(
        f"/faturas/{fatura_ana['id']}/ajuste-pos-fechamento", json={"valor": "10.00"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


def test_importar_fatura_duplicada_mesmo_cartao_mesmo_mes_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    _importar_fatura(client, headers, cartao["id"], mes_referencia="2026-05-01")

    resposta = client.post(
        "/faturas/importar",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-05-01", "valor_total": "100.00"},
        headers=headers,
    )
    assert resposta.status_code == 409


def test_importar_fatura_de_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana2@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno2@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)
    cartao_bruno = _criar_cartao(client, headers_bruno, conta_bruno["id"])

    resposta = client.post(
        "/faturas/importar",
        json={"cartao_id": cartao_bruno["id"], "mes_referencia": "2026-05-01", "valor_total": "100.00"},
        headers=headers_ana,
    )
    assert resposta.status_code == 404


def test_importar_fatura_depois_aceita_registrar_pagamento_normalmente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _importar_fatura(client, headers, cartao["id"], valor_total="300.00")

    resposta = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "300.00", "data": "2020-06-01", "descricao": "Pagamento retroativo"},
        headers=headers,
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["status"] == "PAGA"
    assert resposta.json()["valor_pago"] == "300.00"


def test_importar_fatura_pode_ser_excluida_sem_transacao_vinculada(client):
    # Mesma regra relaxada de exclusão (seção acima): uma fatura importada
    # sem nenhum pagamento/transação ainda vinculada pode ser desfeita, já
    # que "importar com o valor errado" é o mesmo tipo de engano que
    # "fechar por engano".
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _importar_fatura(client, headers, cartao["id"])

    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204


def test_excluir_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(client, headers_ana, cartao_ana["id"])

    resposta = client.delete(f"/faturas/{fatura_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


# ---- Exclusão em lote (pedido explícito do usuário) ----


def test_excluir_faturas_em_lote_remove_todas_as_informadas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura_a = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-05-01")
    fatura_b = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-06-01")
    fatura_c = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-07-01")

    resposta = client.post(
        "/faturas/excluir-em-lote",
        json={"fatura_ids": [fatura_a["id"], fatura_b["id"]]},
        headers=headers,
    )
    assert resposta.status_code == 204

    assert client.get(f"/faturas/{fatura_a['id']}", headers=headers).status_code == 404
    assert client.get(f"/faturas/{fatura_b['id']}", headers=headers).status_code == 404
    # não estava na lista - continua intacta
    assert client.get(f"/faturas/{fatura_c['id']}", headers=headers).status_code == 200


def test_excluir_faturas_em_lote_desvincula_transacoes_sem_apagar(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura = _criar_fatura(client, headers, cartao["id"])

    usuario_id = _usuario_id(client, headers)
    transacao = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("50.00"),
        data=date(2026, 7, 5),
        descricao="Compra",
        cartao_id=cartao["id"],
    )
    db_session.add(transacao)
    db_session.commit()
    db_session.refresh(transacao)
    transacao_id = transacao.id

    resposta = client.post(
        "/faturas/excluir-em-lote", json={"fatura_ids": [fatura["id"]]}, headers=headers
    )
    assert resposta.status_code == 204

    resposta_transacao = client.get(f"/transacoes/{transacao_id}", headers=headers)
    assert resposta_transacao.status_code == 200
    assert resposta_transacao.json()["fatura_id"] is None


def test_excluir_faturas_em_lote_com_id_invalido_no_meio_retorna_404(client):
    """Se qualquer id da lista não existir/não for do usuário, a rota
    inteira falha com 404 (`FaturaService.excluir_em_lote` propaga o
    `NotFoundError` do id inválido sem tolerância). A garantia de "nenhuma
    fatura fica parcialmente apagada" vem do commit único por request em
    `app/db/session.py::get_db` (só confirma se a rota inteira terminar
    sem exceção) - não testável aqui via HTTP porque o `client` de teste
    (`tests/integration/conftest.py`) reusa a MESMA sessão sem
    commit/rollback entre requisições (só pra dar `db_session` aos testes
    que também escrevem direto no banco), diferente do `get_db` real de
    produção."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura_a = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-05-01")
    fatura_b = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-06-01")

    resposta = client.post(
        "/faturas/excluir-em-lote",
        json={"fatura_ids": [fatura_a["id"], 999999, fatura_b["id"]]},
        headers=headers,
    )
    assert resposta.status_code == 404


def test_excluir_faturas_em_lote_com_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(client, headers_ana, cartao_ana["id"])

    resposta = client.post(
        "/faturas/excluir-em-lote", json={"fatura_ids": [fatura_ana["id"]]}, headers=headers_bruno
    )
    assert resposta.status_code == 404
    assert client.get(f"/faturas/{fatura_ana['id']}", headers=headers_ana).status_code == 200


def test_excluir_faturas_em_lote_com_lista_vazia_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/faturas/excluir-em-lote", json={"fatura_ids": []}, headers=headers)
    assert resposta.status_code == 422


# ---- Pagamento em lote (pedido explícito do usuário: "seria interessante
# poder pagar todas selecionadas") ----


def test_pagar_faturas_em_lote_paga_o_restante_de_cada_fatura_fechada(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    usuario_id = _usuario_id(client, headers)

    fatura_a = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-05-01")
    fatura_b = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-06-01")
    db_session.add_all(
        [
            Transacao(
                usuario_id=usuario_id, tipo=TipoTransacao.DESPESA, valor=Decimal("100.00"),
                data=date(2026, 5, 3), descricao="Compra A", cartao_id=cartao["id"], fatura_id=fatura_a["id"],
            ),
            Transacao(
                usuario_id=usuario_id, tipo=TipoTransacao.DESPESA, valor=Decimal("200.00"),
                data=date(2026, 6, 3), descricao="Compra B", cartao_id=cartao["id"], fatura_id=fatura_b["id"],
            ),
        ]
    )
    db_session.commit()
    client.post(f"/faturas/{fatura_a['id']}/fechar", headers=headers)
    client.post(f"/faturas/{fatura_b['id']}/fechar", headers=headers)

    resposta = client.post(
        "/faturas/pagar-em-lote",
        json={"fatura_ids": [fatura_a["id"], fatura_b["id"]], "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"pagas": 2}

    assert client.get(f"/faturas/{fatura_a['id']}", headers=headers).json()["status"] == "PAGA"
    assert client.get(f"/faturas/{fatura_b['id']}", headers=headers).json()["status"] == "PAGA"


def test_pagar_faturas_em_lote_pula_fatura_ainda_aberta(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    usuario_id = _usuario_id(client, headers)

    fatura_fechada = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-05-01")
    db_session.add(
        Transacao(
            usuario_id=usuario_id, tipo=TipoTransacao.DESPESA, valor=Decimal("100.00"),
            data=date(2026, 5, 3), descricao="Compra", cartao_id=cartao["id"], fatura_id=fatura_fechada["id"],
        )
    )
    db_session.commit()
    client.post(f"/faturas/{fatura_fechada['id']}/fechar", headers=headers)

    fatura_aberta = _criar_fatura(client, headers, cartao["id"], mes_referencia="2026-06-01")

    resposta = client.post(
        "/faturas/pagar-em-lote",
        json={"fatura_ids": [fatura_fechada["id"], fatura_aberta["id"]], "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {"pagas": 1}

    assert client.get(f"/faturas/{fatura_fechada['id']}", headers=headers).json()["status"] == "PAGA"
    assert client.get(f"/faturas/{fatura_aberta['id']}", headers=headers).json()["status"] == "ABERTA"


def test_pagar_faturas_em_lote_sem_nenhuma_elegivel_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    fatura_aberta = _criar_fatura(client, headers, cartao["id"])

    resposta = client.post(
        "/faturas/pagar-em-lote",
        json={"fatura_ids": [fatura_aberta["id"]], "data": "2026-07-20"},
        headers=headers,
    )
    assert resposta.status_code == 422


def test_pagar_faturas_em_lote_com_fatura_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])
    fatura_ana = _criar_fatura(client, headers_ana, cartao_ana["id"])

    resposta = client.post(
        "/faturas/pagar-em-lote",
        json={"fatura_ids": [fatura_ana["id"]], "data": "2026-07-20"},
        headers=headers_bruno,
    )
    assert resposta.status_code == 404


def test_pagar_faturas_em_lote_com_lista_vazia_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post(
        "/faturas/pagar-em-lote", json={"fatura_ids": [], "data": "2026-07-20"}, headers=headers
    )
    assert resposta.status_code == 422
