"""Testes de integração do CRUD de Cartao: TestClient + banco real (SQLite
em memória). Cobre isolamento entre usuários, unicidade de nome, validação
cruzada de posse da Conta vinculada, cálculo de limite_disponivel e soft
delete via HTTP real.
"""
from datetime import date
from decimal import Decimal

from app.models.enums import StatusFatura, TipoTransacao


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


def _payload_cartao(conta_pagamento_id, **overrides):
    payload = {
        "nome": "Nubank",
        "conta_pagamento_id": conta_pagamento_id,
        "instituicao": "Nu Pagamentos",
        "bandeira": "MASTERCARD",
        "ultimos_quatro_digitos": "1234",
        "limite": "5000.00",
        "dia_fechamento": 10,
        "dia_vencimento": 17,
    }
    payload.update(overrides)
    return payload


def _criar_cartao(client, headers, conta_pagamento_id, **overrides):
    resposta = client.post("/cartoes", json=_payload_cartao(conta_pagamento_id, **overrides), headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_criar_cartao_sem_autenticacao_retorna_401(client):
    resposta = client.post("/cartoes", json=_payload_cartao(1))
    assert resposta.status_code == 401


def test_criar_e_obter_cartao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    assert cartao["nome"] == "Nubank"
    assert cartao["conta_pagamento_id"] == conta["id"]
    assert cartao["bandeira"] == "MASTERCARD"
    assert cartao["limite"] == "5000.00"
    assert cartao["limite_disponivel"] == "5000.00"  # sem gastos ainda
    assert cartao["ativo"] is True

    resposta = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == cartao["id"]


def test_criar_cartao_com_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)

    resposta = client.post("/cartoes", json=_payload_cartao(conta_bruno["id"]), headers=headers_ana)
    assert resposta.status_code == 404


def test_criar_cartao_com_conta_inexistente_retorna_404(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/cartoes", json=_payload_cartao(99999), headers=headers)
    assert resposta.status_code == 404


def test_criar_cartao_com_limite_negativo_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/cartoes", json=_payload_cartao(conta["id"], limite="-100.00"), headers=headers
    )
    assert resposta.status_code == 422


def test_criar_cartao_com_dia_fechamento_invalido_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/cartoes", json=_payload_cartao(conta["id"], dia_fechamento=32), headers=headers
    )
    assert resposta.status_code == 422


def test_criar_cartao_com_dia_vencimento_zero_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/cartoes", json=_payload_cartao(conta["id"], dia_vencimento=0), headers=headers
    )
    assert resposta.status_code == 422


def test_criar_cartao_com_ultimos_digitos_invalidos_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/cartoes",
        json=_payload_cartao(conta["id"], ultimos_quatro_digitos="12a4"),
        headers=headers,
    )
    assert resposta.status_code == 422


def test_criar_cartao_com_bandeira_invalida_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = client.post(
        "/cartoes", json=_payload_cartao(conta["id"], bandeira="BANDEIRA_INEXISTENTE"), headers=headers
    )
    assert resposta.status_code == 422


def test_criar_cartao_com_nome_duplicado_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_cartao(client, headers, conta["id"], nome="Nubank")

    resposta = client.post("/cartoes", json=_payload_cartao(conta["id"], nome="Nubank"), headers=headers)
    assert resposta.status_code == 409


def test_criar_cartao_com_mesmo_nome_em_usuarios_diferentes_e_permitido(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_bruno = _criar_conta(client, headers_bruno)

    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"], nome="Nubank")
    cartao_bruno = _criar_cartao(client, headers_bruno, conta_bruno["id"], nome="Nubank")
    assert cartao_ana["id"] != cartao_bruno["id"]


def test_criar_cartao_com_nome_de_cartao_desativado_reativa(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    original = _criar_cartao(client, headers, conta["id"], nome="Nubank", limite="5000.00")
    client.delete(f"/cartoes/{original['id']}", headers=headers)

    recriado = _criar_cartao(client, headers, conta["id"], nome="Nubank", limite="8000.00")

    assert recriado["id"] == original["id"]
    assert recriado["ativo"] is True
    assert recriado["limite"] == "8000.00"


def test_listar_cartoes_retorna_apenas_os_do_usuario_autenticado(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_bruno = _criar_conta(client, headers_bruno)

    _criar_cartao(client, headers_ana, conta_ana["id"], nome="Cartao da Ana")
    _criar_cartao(client, headers_bruno, conta_bruno["id"], nome="Cartao do Bruno")

    resposta = client.get("/cartoes", headers=headers_ana)
    nomes = [c["nome"] for c in resposta.json()]
    assert nomes == ["Cartao da Ana"]


def test_obter_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])

    resposta = client.get(f"/cartoes/{cartao_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_atualizar_cartao_parcial(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], nome="Original")

    resposta = client.patch(f"/cartoes/{cartao['id']}", json={"limite": "9000.00"}, headers=headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Original"
    assert corpo["limite"] == "9000.00"


def test_atualizar_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])

    resposta = client.patch(
        f"/cartoes/{cartao_ana['id']}", json={"nome": "Hackeado"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


def test_atualizar_conta_pagamento_para_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_bruno = _criar_conta(client, headers_bruno)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])

    resposta = client.patch(
        f"/cartoes/{cartao_ana['id']}",
        json={"conta_pagamento_id": conta_bruno["id"]},
        headers=headers_ana,
    )
    assert resposta.status_code == 404


def test_atualizar_nome_para_nome_ja_usado_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_cartao(client, headers, conta["id"], nome="Nubank")
    inter = _criar_cartao(client, headers, conta["id"], nome="Inter")

    resposta = client.patch(f"/cartoes/{inter['id']}", json={"nome": "Nubank"}, headers=headers)
    assert resposta.status_code == 409


def test_atualizar_renomeando_para_nome_de_cartao_inativo_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    inativo = _criar_cartao(client, headers, conta["id"], nome="Nubank")
    client.delete(f"/cartoes/{inativo['id']}", headers=headers)
    outro = _criar_cartao(client, headers, conta["id"], nome="Inter")

    resposta = client.patch(f"/cartoes/{outro['id']}", json={"nome": "Nubank"}, headers=headers)
    assert resposta.status_code == 409


def test_atualizar_ativo_true_reativa_cartao_diretamente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    client.delete(f"/cartoes/{cartao['id']}", headers=headers)

    resposta = client.patch(f"/cartoes/{cartao['id']}", json={"ativo": True}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is True


def test_desativar_cartao_e_soft_delete(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = client.delete(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta_get.status_code == 200
    assert resposta_get.json()["ativo"] is False

    resposta_listagem = client.get("/cartoes", headers=headers)
    assert resposta_listagem.json() == []

    resposta_todos = client.get("/cartoes?apenas_ativos=false", headers=headers)
    assert len(resposta_todos.json()) == 1


def test_desativar_cartao_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])

    resposta = client.delete(f"/cartoes/{cartao_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


# --- limite_disponivel calculado a partir de dados reais no banco --------

def test_limite_disponivel_ignora_despesa_de_cartao_sem_fatura_associada(client, db_session):
    """Invariante invertida em 2026-07-20 (bug real relatado pelo usuário -
    ver `test_excluir_fatura_com_compra_vinculada_libera_o_limite`). Esta
    era a premissa ANTIGA: uma compra "sem fatura associada (ciclo ainda
    não fechado)" já consumia limite de imediato - escrita numa etapa em
    que a geração de Fatura ainda não existia. Hoje `TransacaoService.criar`
    SEMPRE resolve `fatura_id` via `resolver_fatura_aberta` no momento da
    criação de uma compra de cartão (nunca fica em branco por opção do
    usuário) - a ÚNICA forma real de uma compra ficar sem fatura associada
    é a exclusão da fatura pelo próprio usuário (`FaturaService.excluir`),
    e nesse caso ela deve parar de contar como dívida ativa (não há mais
    fatura para vincular um pagamento). Este teste simula esse estado
    diretamente no banco (inserção sem passar pelo Service, mesma técnica
    do teste antigo) só para provar que `somar_gastos_nao_pagos` ignora
    esse caso hoje - não é mais um jeito válido de lançar uma compra."""
    from app.models import Transacao

    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    usuario_id = client.get("/auth/me", headers=headers).json()["id"]
    transacao = Transacao(
        usuario_id=usuario_id,
        tipo=TipoTransacao.DESPESA,
        valor=Decimal("350.00"),
        data=date(2026, 7, 1),
        descricao="Compra no cartao",
        cartao_id=cartao["id"],
    )
    db_session.add(transacao)
    db_session.commit()

    resposta = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["limite_disponivel"] == "5000.00"


def test_limite_disponivel_ignora_despesas_de_fatura_ja_paga(client):
    """Uma despesa cuja fatura ja foi PAGA (pagamento real, via
    `POST /faturas/{id}/pagamentos`) nao consome mais limite - o ciclo foi
    quitado, o espaco esta livre de novo.

    Reescrito (correção do bug "limite disponível não volta ao pagar
    fatura", 2026-07): a versão anterior deste teste forçava
    `Fatura.status = PAGA` direto no banco, sem nenhuma Transacao de
    pagamento por trás - uma situação que o fluxo real da aplicação nunca
    produz (`status` só grava ABERTA/FECHADA; "paga" é sempre derivado de
    `valor_pago >= valor_total`). Esse teste passava mesmo com o bug real
    presente. Agora o teste passa pelo fluxo real: cria a fatura, fecha o
    ciclo, registra o pagamento total via endpoint, e só então confere que
    o limite voltou."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    fatura = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-06-01"},
        headers=headers,
    ).json()

    transacao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "350.00",
            "data": "2026-06-02",
            "descricao": "Compra a ser paga",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    assert transacao.status_code == 201, transacao.text

    # Antes de fechar/pagar, a despesa já consome limite.
    resposta_antes = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta_antes.json()["limite_disponivel"] == "4650.00"

    fechada = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)
    assert fechada.status_code == 200, fechada.text
    valor_total = fechada.json()["valor_total"]
    assert valor_total == "350.00"

    pagamento = client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": valor_total, "data": "2026-06-18", "descricao": "Pagamento da fatura"},
        headers=headers,
    )
    assert pagamento.status_code == 201, pagamento.text

    resposta = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["limite_disponivel"] == "5000.00"


def test_limite_disponivel_volta_ao_excluir_transacao_de_compra(client):
    """Bug relatado pelo usuário (2026-07-20): excluir uma compra do cartão
    precisa liberar o limite imediatamente - `limite_disponivel` nunca lê um
    contador incremental, é somado ao vivo (`CartaoRepository.
    somar_gastos_nao_pagos`), então basta a linha sumir da tabela
    `Transacao` para a próxima leitura já refletir. Este teste cobre
    exatamente esse cenário via fluxo HTTP real, sem fatura fechada no
    meio (o caminho mais simples: compra avulsa, ciclo ainda ABERTO)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    transacao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "350.00",
            "data": "2026-07-02",
            "descricao": "Compra a ser excluída",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    ).json()

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4650.00"

    resposta = client.delete(f"/transacoes/{transacao['id']}", headers=headers)
    assert resposta.status_code == 204

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "5000.00"


def test_limite_disponivel_recalcula_ao_editar_valor_da_compra(client):
    """Editar o valor de uma compra ainda em ciclo ABERTO precisa refletir
    de imediato no limite - mesmo raciocínio do teste de exclusão acima,
    mas via PATCH em vez de DELETE."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    transacao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "350.00",
            "data": "2026-07-02",
            "descricao": "Compra a ser editada",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    ).json()
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4650.00"

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"valor": "1000.00"}, headers=headers
    )
    assert resposta.status_code == 200

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4000.00"


def test_limite_disponivel_libera_parcelas_futuras_ao_cancelar_parcelamento(client):
    """Excluir UMA parcela de uma compra parcelada no cartão (pelo endpoint
    genérico de Transação) cancela o Parcelamento inteiro - todas as
    parcelas ainda destravadas (fatura ABERTA) somem, não só a clicada (bug
    real corrigido em 2026-07-20, ver docstring de
    `TransacaoService.excluir`). O limite consumido pelas parcelas
    canceladas precisa voltar por completo."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    parcelamento = client.post(
        "/parcelamentos",
        json={
            "descricao": "Notebook",
            "valor_total": "900.00",
            "num_parcelas": 3,
            "data_inicio": "2026-07-15",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    ).json()

    # As 3 parcelas de R$300 já consomem limite de imediato (nenhuma fatura
    # fechada ainda - todos os ciclos resolvidos nascem ABERTOS).
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4100.00"

    parcelas = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert len(parcelas) == 3

    resposta = client.delete(f"/transacoes/{parcelas[0]['id']}", headers=headers)
    assert resposta.status_code == 204

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "5000.00"
    parcelamento_atualizado = client.get(f"/parcelamentos/{parcelamento['id']}", headers=headers).json()
    assert parcelamento_atualizado["ativo"] is False


def test_limite_disponivel_e_independente_entre_cartoes_do_mesmo_usuario(client):
    """Uma compra no cartão A nunca deve afetar o limite do cartão B - a
    soma em `CartaoRepository.somar_gastos_nao_pagos` é sempre escopada por
    `cartao_id`."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao_a = _criar_cartao(client, headers, conta["id"], nome="Cartao A", limite="5000.00")
    cartao_b = _criar_cartao(client, headers, conta["id"], nome="Cartao B", limite="2000.00")

    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "500.00",
            "data": "2026-07-02",
            "descricao": "Compra só no cartão A",
            "cartao_id": cartao_a["id"],
        },
        headers=headers,
    )

    assert client.get(f"/cartoes/{cartao_a['id']}", headers=headers).json()["limite_disponivel"] == "4500.00"
    assert client.get(f"/cartoes/{cartao_b['id']}", headers=headers).json()["limite_disponivel"] == "2000.00"


def test_limite_disponivel_soma_faturas_nao_pagas_de_multiplos_ciclos(client):
    """Duas faturas ABERTAS/FECHADAS do MESMO cartão, cada uma com compras
    próprias e nenhuma paga ainda: o limite consumido é a soma dos dois
    ciclos - só uma fatura paga (a de junho, neste teste) libera a parte
    dela."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    fatura_junho = client.post(
        "/faturas", json={"cartao_id": cartao["id"], "mes_referencia": "2026-06-01"}, headers=headers
    ).json()
    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "300.00",
            "data": "2026-06-05",
            "descricao": "Compra de junho",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "200.00",
            "data": "2026-07-05",
            "descricao": "Compra de julho",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )

    # As duas faturas somadas: 300 (junho) + 200 (julho, ainda ABERTA).
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4500.00"

    fechada = client.post(f"/faturas/{fatura_junho['id']}/fechar", headers=headers).json()
    client.post(
        f"/faturas/{fatura_junho['id']}/pagamentos",
        json={"valor": fechada["valor_total"], "data": "2026-06-18", "descricao": "Pagamento de junho"},
        headers=headers,
    )

    # Só a parte de junho (300) volta - julho (200, ainda ABERTA) continua consumindo.
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4800.00"


def test_limite_disponivel_desconta_fatura_importada_nao_paga(client):
    """Bug real (2026-07-20): fatura HISTÓRICA importada (`/faturas/importar`)
    nasce FECHADA com `valor_total` declarado direto pelo usuário e nenhuma
    Transacao por trás - `somar_gastos_nao_pagos` não tinha nenhum termo que
    lesse `valor_total` de fatura importada, então essa dívida era invisível
    para `limite_disponivel` até ser paga."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="5000.00")

    fatura = client.post(
        "/faturas/importar",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-05-01", "valor_total": "796.60"},
        headers=headers,
    )
    assert fatura.status_code == 201, fatura.text
    fatura = fatura.json()
    assert fatura["status"] in ("FECHADA", "ATRASADA")  # nunca ABERTA

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "4203.40"

    client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "796.60", "data": "2026-05-18", "descricao": "Pagamento da fatura importada"},
        headers=headers,
    )

    # Paga: limite volta integralmente.
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "5000.00"


def test_cartao_sem_nenhuma_movimentacao_tem_limite_disponivel_igual_ao_limite_total(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="3200.00")

    resposta = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta.json()["limite_disponivel"] == "3200.00"


def test_excluir_fatura_com_compra_vinculada_libera_o_limite(client):
    """Bug real relatado pelo usuário (2026-07-20, com print de tela):
    "excluí todas as faturas selecionadas e o limite não retornou para o
    cartão". Causa raiz: a compra fica com `fatura_id = NULL` após a
    exclusão (`FaturaRepository.desvincular_transacoes`), mas
    `CartaoRepository.somar_gastos_nao_pagos` ainda contava qualquer compra
    "sem fatura associada" como dívida ativa - uma regra que fazia sentido
    antes de `resolver_fatura_aberta` garantir que toda compra de cartão
    sempre nasce com fatura, mas que virou um beco sem saída depois
    (não existe mais fatura pra vincular um pagamento, e a compra nem
    aparece mais em Transações). Excluir a fatura agora libera o limite de
    imediato, mesmo sem nenhum pagamento ter sido registrado."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="2000.00")

    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "500.00",
            "data": "2026-07-05",
            "descricao": "Compra qualquer",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "1500.00"

    fatura = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers).json()[0]
    resposta = client.delete(f"/faturas/{fatura['id']}", headers=headers)
    assert resposta.status_code == 204

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "2000.00"


def test_excluir_faturas_em_lote_com_compra_e_pagamento_vinculados_libera_o_limite(client):
    """Mesmo cenário do bug real, mas reproduzindo exatamente o relato do
    usuário: seleção múltipla + exclusão em lote, com uma fatura que já
    tinha inclusive um pagamento parcial registrado antes de ser
    excluída."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], limite="2000.00")

    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "300.00",
            "data": "2026-07-05",
            "descricao": "Compra A",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )
    fatura = client.get(f"/faturas?cartao_id={cartao['id']}", headers=headers).json()[0]
    client.post(f"/faturas/{fatura['id']}/fechar", headers=headers)
    client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": "100.00", "data": "2026-07-18", "descricao": "Pagamento parcial"},
        headers=headers,
    )
    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "1700.00"

    resposta = client.post(
        "/faturas/excluir-em-lote", json={"fatura_ids": [fatura["id"]]}, headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).json()["limite_disponivel"] == "2000.00"


# ---- Exclusão definitiva (hard delete) - Etapa F10 ----


def test_excluir_cartao_permanente_sem_fatura_apaga_a_linha(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    resposta = client.delete(f"/cartoes/{cartao['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_cartao_permanente_com_fatura_retorna_422(client, db_session):
    from app.models import Fatura

    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    fatura = Fatura(
        cartao_id=cartao["id"],
        mes_referencia=date(2026, 6, 1),
        data_fechamento=date(2026, 6, 10),
        data_vencimento=date(2026, 6, 17),
        status=StatusFatura.ABERTA,
    )
    db_session.add(fatura)
    db_session.commit()

    resposta = client.delete(f"/cartoes/{cartao['id']}/permanente", headers=headers)
    assert resposta.status_code == 422

    resposta_get = client.get(f"/cartoes/{cartao['id']}", headers=headers)
    assert resposta_get.status_code == 200


def test_excluir_cartao_permanente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    cartao_ana = _criar_cartao(client, headers_ana, conta_ana["id"])

    resposta = client.delete(f"/cartoes/{cartao_ana['id']}/permanente", headers=headers_bruno)
    assert resposta.status_code == 404


# ---- Exclusão com apagar_transacoes=True (pedido explícito do usuário) ----
# docs/analise-arquitetural-exclusao-cartao-com-historico.md


def test_excluir_cartao_permanente_com_apagar_transacoes_remove_fatura_e_transacao_avulsa(
    client, db_session
):
    """Fluxo real (sem mexer direto no banco): fatura aberta + transação
    avulsa (não parcelada) no cartão. Com `apagar_transacoes=true`, a
    exclusão deixa de bloquear com 422 - fatura e transação somem junto com
    o cartão."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    fatura = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-06-01"},
        headers=headers,
    ).json()

    transacao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "350.00",
            "data": "2026-06-02",
            "descricao": "Compra a ser apagada",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    ).json()

    # Sem apagar_transacoes ainda bloqueia, mesmo comportamento de sempre.
    resposta_bloqueada = client.delete(f"/cartoes/{cartao['id']}/permanente", headers=headers)
    assert resposta_bloqueada.status_code == 422

    resposta = client.delete(
        f"/cartoes/{cartao['id']}/permanente?apagar_transacoes=true", headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).status_code == 404
    assert client.get(f"/faturas/{fatura['id']}", headers=headers).status_code == 404
    assert client.get(f"/transacoes/{transacao['id']}", headers=headers).status_code == 404


def test_excluir_cartao_permanente_com_apagar_transacoes_cancela_parcelamento_do_cartao(
    client, db_session
):
    """Compra parcelada no cartão: a cascata precisa apagar as parcelas
    (via TransacaoService.excluir -> cancelar_parcelas_do_parcelamento,
    mesmo caminho de ParcelamentoService.cancelar()) sem quebrar mesmo
    quando uma chamada de exclusão já cascateia e remove outras parcelas do
    mesmo Parcelamento antes do loop chegar nelas."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    fatura = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-06-01"},
        headers=headers,
    ).json()

    parcelamento = client.post(
        "/parcelamentos",
        json={
            "descricao": "Notebook",
            "valor_total": "1000.00",
            "num_parcelas": 3,
            "data_inicio": "2026-06-15",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    ).json()
    assert parcelamento["cartao_id"] == cartao["id"]

    resposta = client.delete(
        f"/cartoes/{cartao['id']}/permanente?apagar_transacoes=true", headers=headers
    )
    assert resposta.status_code == 204

    assert client.get(f"/cartoes/{cartao['id']}", headers=headers).status_code == 404
    assert client.get(f"/faturas/{fatura['id']}", headers=headers).status_code == 404

    parcelas = client.get(
        f"/transacoes?parcelamento_id={parcelamento['id']}", headers=headers
    ).json()
    assert parcelas == []

    parcelamento_atualizado = client.get(
        f"/parcelamentos/{parcelamento['id']}", headers=headers
    ).json()
    assert parcelamento_atualizado["ativo"] is False


def test_excluir_cartao_permanente_com_apagar_transacoes_preserva_transacao_de_pagamento_da_fatura(
    client, db_session
):
    """A transação de PAGAMENTO de uma fatura (`fatura_paga_id`) é sempre
    uma transação de Conta (dinheiro real que já saiu do banco) - a
    cascata do cartão nunca deve apagá-la, só desvincular a fatura que
    deixou de existir (mesmo comportamento de FaturaService.excluir() já
    usado em qualquer exclusão de fatura paga)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])

    fatura = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": "2026-06-01"},
        headers=headers,
    ).json()

    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "350.00",
            "data": "2026-06-02",
            "descricao": "Compra a ser apagada",
            "cartao_id": cartao["id"],
        },
        headers=headers,
    )

    fechada = client.post(f"/faturas/{fatura['id']}/fechar", headers=headers).json()
    client.post(
        f"/faturas/{fatura['id']}/pagamentos",
        json={"valor": fechada["valor_total"], "data": "2026-06-18", "descricao": "Pagamento"},
        headers=headers,
    )
    # A transação de pagamento é sempre lançada na Conta (nunca no Cartão) -
    # filtrar por conta_id isola ela de qualquer transação de compra.
    transacao_pagamento = client.get(
        f"/transacoes?conta_id={conta['id']}", headers=headers
    ).json()[0]
    assert transacao_pagamento["fatura_paga_id"] == fatura["id"]

    resposta = client.delete(
        f"/cartoes/{cartao['id']}/permanente?apagar_transacoes=true", headers=headers
    )
    assert resposta.status_code == 204

    resposta_pagamento = client.get(f"/transacoes/{transacao_pagamento['id']}", headers=headers)
    assert resposta_pagamento.status_code == 200
    assert resposta_pagamento.json()["fatura_paga_id"] is None
