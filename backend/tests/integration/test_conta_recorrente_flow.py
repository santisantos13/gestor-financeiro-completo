"""Testes de integração do CRUD de ContaRecorrente: TestClient + banco real
(SQLite em memória). Cobre validação estrutural (conta XOR cartão),
rejeição de frequência não suportada (SEMANAL/ANUAL - YAGNI), geração lazy
de ocorrências reais via TransacaoService/FaturaService (não fakes) tanto
na criação quanto via sincronização explícita, ausência de geração
duplicada (`GET /transacoes?origem_recorrente_id=` e `UniqueConstraint` do
banco), efeito real em `saldo_atual`, PATCH em campos do template (sem
afetar ocorrências já geradas), soft delete via DELETE e posse entre
usuários.
"""
from datetime import date, timedelta


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente", saldo_inicial="0.00"):
    resposta = client.post("/contas", json={"nome": nome, "saldo_inicial": saldo_inicial}, headers=headers)
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


def _criar_conta_recorrente(client, headers, **overrides):
    payload = {
        "descricao": "Aluguel",
        "valor": "1500.00",
        "tipo": "DESPESA",
        "dia_vencimento": 1,
        "data_inicio": "2026-01-01",
    }
    payload.update(overrides)
    payload = {chave: valor for chave, valor in payload.items() if valor is not None}
    return client.post("/contas-recorrentes", json=payload, headers=headers)


def _primeiro_dia_meses_atras(referencia: date, meses: int) -> str:
    ano, mes = referencia.year, referencia.month
    for _ in range(meses):
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
    return date(ano, mes, 1).isoformat()


def _primeiro_dia_proximo_mes(referencia: date) -> str:
    ano, mes = referencia.year, referencia.month
    mes += 1
    if mes == 13:
        mes = 1
        ano += 1
    return date(ano, mes, 1).isoformat()


# --- autenticação / estrutura -----------------------------------------------

def test_criar_conta_recorrente_sem_autenticacao_retorna_401(client):
    resposta = client.post(
        "/contas-recorrentes",
        json={"descricao": "x", "valor": "10.00", "tipo": "DESPESA", "dia_vencimento": 1, "data_inicio": "2026-01-01"},
    )
    assert resposta.status_code == 401


def test_criar_conta_recorrente_sem_conta_e_sem_cartao_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = _criar_conta_recorrente(client, headers)
    assert resposta.status_code == 422


def test_criar_conta_recorrente_com_conta_e_cartao_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    resposta = _criar_conta_recorrente(client, headers, conta_id=conta["id"], cartao_id=cartao["id"])
    assert resposta.status_code == 422


# --- dia_vencimento × família de frequência (expansão 2026-07-20) ----------
# Substitui o antigo bloqueio de frequências não-MENSAL: todas as 8
# frequências são aceitas, mas dia_vencimento é obrigatório na família
# baseada em meses e proibido na baseada em dias.

def test_criar_conta_recorrente_semanal_com_dia_vencimento_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    # o helper manda dia_vencimento por padrão - SEMANAL não o aceita.
    resposta = _criar_conta_recorrente(client, headers, conta_id=conta["id"], frequencia="SEMANAL")
    assert resposta.status_code == 422


def test_criar_conta_recorrente_anual_com_dia_vencimento_e_aceita(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_conta_recorrente(client, headers, conta_id=conta["id"], frequencia="ANUAL")
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["frequencia"] == "ANUAL"


def test_criar_conta_recorrente_com_data_fim_anterior_a_data_inicio_retorna_422(client):
    # achado da revisao tecnica final: sem essa checagem, a recorrencia era
    # aceita e nunca gerava nenhuma ocorrencia - silenciosamente.
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], data_inicio="2026-06-01", data_fim="2026-01-01"
    )
    assert resposta.status_code == 422


def test_atualizar_conta_recorrente_data_fim_para_antes_de_data_inicio_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], data_inicio="2026-06-01"
    ).json()

    resposta = client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}", json={"data_fim": "2026-01-01"}, headers=headers
    )
    assert resposta.status_code == 422


def test_criar_conta_recorrente_sem_frequencia_usa_mensal(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()
    assert conta_recorrente["frequencia"] == "MENSAL"


# --- criação: geração lazy de ocorrências reais até "hoje" ------------------

def test_criar_conta_recorrente_de_conta_gera_ocorrencias_ate_hoje(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 3)

    resposta = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    )
    assert resposta.status_code == 201, resposta.text
    conta_recorrente = resposta.json()
    assert conta_recorrente["status"] == "ATIVA"
    # cursor materializado ja avancou para alem de hoje (tudo vencido gerado)
    assert conta_recorrente["proxima_execucao"] > date.today().isoformat()

    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    assert len(ocorrencias) == 4  # mes de data_inicio + 3 seguintes, ate o mes atual
    assert all(o["tipo"] == "DESPESA" for o in ocorrencias)
    assert all(o["conta_id"] == conta["id"] for o in ocorrencias)
    assert all(o["origem_recorrente_id"] == conta_recorrente["id"] for o in ocorrencias)
    assert all(o["numero_parcela"] is None for o in ocorrencias)


def test_criar_conta_recorrente_com_data_inicio_no_futuro_nao_gera_ocorrencia(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_proximo_mes(date.today())

    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    ).json()

    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    assert ocorrencias == []


def test_criar_conta_recorrente_de_cartao_gera_ocorrencias_pagas_vinculadas_a_fatura(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], dia_fechamento=10, dia_vencimento=17)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)

    conta_recorrente = _criar_conta_recorrente(
        client, headers, cartao_id=cartao["id"], conta_id=None, dia_vencimento=1, data_inicio=data_inicio
    ).json()

    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    assert len(ocorrencias) == 2
    assert all(o["status"] == "PAGO" for o in ocorrencias)  # status de cartao e sempre forcado
    assert all(o["fatura_id"] is not None for o in ocorrencias)


# --- saldo reflete as ocorrências geradas (sao Transacao de verdade) -------

def test_saldo_atual_reflete_ocorrencias_geradas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="1000.00")
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)

    _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], valor="1500.00", dia_vencimento=1, data_inicio=data_inicio
    )

    # ocorrencias de CONTA nascem PENDENTE (nao afetam saldo_atual ainda,
    # mesma semantica ja usada por Transacao avulsa - so PAGO conta).
    resposta = client.get(f"/contas/{conta['id']}", headers=headers)
    assert resposta.json()["saldo_atual"] == "1000.00"


# --- gerar-ocorrencias-pendentes: sincronização explícita e idempotente ----

def test_gerar_ocorrencias_pendentes_e_idempotente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 2)

    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    ).json()

    resposta_sync = client.post(
        f"/contas-recorrentes/{conta_recorrente['id']}/gerar-ocorrencias-pendentes", headers=headers
    )
    assert resposta_sync.status_code == 200
    assert resposta_sync.json() == []  # nada pendente: criar() ja gerou tudo ate hoje

    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    assert len(ocorrencias) == 3


def test_gerar_ocorrencias_pendentes_em_recorrencia_desativada_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()
    client.delete(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers)

    resposta = client.post(
        f"/contas-recorrentes/{conta_recorrente['id']}/gerar-ocorrencias-pendentes", headers=headers
    )
    assert resposta.status_code == 422


def test_gerar_ocorrencias_pendentes_sem_autenticacao_retorna_401(client):
    resposta = client.post("/contas-recorrentes/1/gerar-ocorrencias-pendentes")
    assert resposta.status_code == 401


# --- não permite geração duplicada (POST /transacoes manual) ---------------

def test_criar_transacao_manual_com_origem_recorrente_e_data_ja_usada_retorna_409(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)

    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    ).json()
    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    data_existente = ocorrencias[0]["data"]

    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "1500.00",
            "data": data_existente,
            "descricao": "Duplicata manual",
            "conta_id": conta["id"],
            "origem_recorrente_id": conta_recorrente["id"],
        },
        headers=headers,
    )
    assert resposta.status_code == 409


def test_criar_transacao_manual_com_origem_recorrente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)
    conta_recorrente_bruno = _criar_conta_recorrente(client, headers_bruno, conta_id=conta_bruno["id"]).json()

    conta_ana = _criar_conta(client, headers_ana)
    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "10.00",
            "data": "2026-01-01",
            "descricao": "x",
            "conta_id": conta_ana["id"],
            "origem_recorrente_id": conta_recorrente_bruno["id"],
        },
        headers=headers_ana,
    )
    assert resposta.status_code == 404


# --- PATCH em campos do template (diferente de Parcelamento/Fatura) -------

def test_atualizar_conta_recorrente_altera_apenas_campos_enviados(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], descricao="Original", valor="100.00"
    ).json()

    resposta = client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}", json={"valor": "200.00"}, headers=headers
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["descricao"] == "Original"
    assert corpo["valor"] == "200.00"


def test_atualizar_frequencia_para_semanal_sem_limpar_dia_vencimento_retorna_422(client):
    """MENSAL (com dia_vencimento) -> SEMANAL exige enviar
    dia_vencimento: null junto - o PATCH que só troca a frequência deixa o
    par inválido (dia_vencimento não se aplica à família baseada em dias)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()

    resposta = client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}", json={"frequencia": "SEMANAL"}, headers=headers
    )
    assert resposta.status_code == 422

    resposta_ok = client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}",
        json={"frequencia": "SEMANAL", "dia_vencimento": None},
        headers=headers,
    )
    assert resposta_ok.status_code == 200
    assert resposta_ok.json()["frequencia"] == "SEMANAL"
    assert resposta_ok.json()["dia_vencimento"] is None


def test_atualizar_conta_recorrente_estrutura_invalida_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()

    resposta = client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}", json={"cartao_id": cartao["id"]}, headers=headers
    )
    assert resposta.status_code == 422


def test_atualizar_conta_recorrente_nao_gera_nem_apaga_ocorrencias(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)
    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    ).json()

    client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}", json={"valor": "9999.00"}, headers=headers
    )

    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    assert len(ocorrencias) == 2
    # o valor das ocorrencias JA GERADAS nao muda retroativamente.
    assert all(o["valor"] == "1500.00" for o in ocorrencias)


def test_atualizar_conta_recorrente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_recorrente = _criar_conta_recorrente(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.patch(
        f"/contas-recorrentes/{conta_recorrente['id']}", json={"descricao": "Hackeado"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


# --- posse -------------------------------------------------------------------

def test_criar_conta_recorrente_com_conta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_bruno = _criar_conta(client, headers_bruno)

    resposta = _criar_conta_recorrente(client, headers_ana, conta_id=conta_bruno["id"])
    assert resposta.status_code == 404


def test_obter_conta_recorrente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_recorrente = _criar_conta_recorrente(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.get(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_listar_contas_recorrentes_retorna_apenas_as_do_usuario(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_bruno = _criar_conta(client, headers_bruno)
    _criar_conta_recorrente(client, headers_ana, conta_id=conta_ana["id"], descricao="Da Ana")
    _criar_conta_recorrente(client, headers_bruno, conta_id=conta_bruno["id"], descricao="Do Bruno")

    resposta = client.get("/contas-recorrentes", headers=headers_ana)
    assert resposta.status_code == 200
    descricoes = [cr["descricao"] for cr in resposta.json()]
    assert descricoes == ["Da Ana"]


# --- ciclo de vida: DELETE encerra (nunca apaga), pausar/reativar ----------

def test_delete_encerra_em_vez_de_apagar(client):
    """Decisão do usuário (2026-07-20): DELETE preserva o template como
    histórico (status=ENCERRADA) e todas as transações já geradas - nunca
    exclusão física."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()

    resposta = client.delete(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers)
    assert resposta_get.status_code == 200  # continua existindo
    assert resposta_get.json()["status"] == "ENCERRADA"

    # listagem sem filtro mostra TUDO (encerradas são histórico);
    # com filtro por status, some.
    assert len(client.get("/contas-recorrentes", headers=headers).json()) == 1
    assert client.get("/contas-recorrentes?status_filtro=ATIVA", headers=headers).json() == []


def test_pausar_e_reativar_sem_retroativos(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)
    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    ).json()

    pausada = client.post(f"/contas-recorrentes/{conta_recorrente['id']}/pausar", headers=headers)
    assert pausada.status_code == 200
    assert pausada.json()["status"] == "PAUSADA"

    total_antes = len(
        client.get(f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers).json()
    )

    reativada = client.post(f"/contas-recorrentes/{conta_recorrente['id']}/reativar", headers=headers)
    assert reativada.status_code == 200
    assert reativada.json()["status"] == "ATIVA"
    assert reativada.json()["proxima_execucao"] > date.today().isoformat()

    total_depois = len(
        client.get(f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers).json()
    )
    assert total_depois == total_antes  # reativar nunca gera retroativos


def test_encerrar_explicito_preenche_data_fim(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()

    resposta = client.post(f"/contas-recorrentes/{conta_recorrente['id']}/encerrar", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ENCERRADA"
    assert resposta.json()["data_fim"] is not None

    # terminal: nem editar, nem pausar, nem encerrar de novo
    assert (
        client.patch(
            f"/contas-recorrentes/{conta_recorrente['id']}", json={"valor": "10.00"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(f"/contas-recorrentes/{conta_recorrente['id']}/pausar", headers=headers).status_code
        == 422
    )


def test_sincronizar_gera_pendentes_de_todos_os_templates(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)
    _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], descricao="A", dia_vencimento=1, data_inicio=data_inicio
    )

    # tudo já foi gerado na criação - sincronizar de novo é idempotente
    resposta = client.post("/contas-recorrentes/sincronizar", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json() == {"geradas": 0, "encerradas": 0}


def test_calendario_projeta_ocorrencias_futuras_como_previsto(client):
    """Expansão 2026-07-20: o calendário mostra ocorrências FUTURAS
    projetadas (até 90 dias), com `previsto=True`, sem persistir nada."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    amanha = date.today() + timedelta(days=1)
    _criar_conta_recorrente(
        client,
        headers,
        conta_id=conta["id"],
        descricao="Assinatura projetada",
        frequencia="DIARIA",
        dia_vencimento=None,
        data_inicio=amanha.isoformat(),
    )

    calendario = client.get(
        f"/central-financeira/calendario?ano={amanha.year}&mes={amanha.month}", headers=headers
    ).json()
    previstos = [e for e in calendario["eventos"] if e.get("previsto")]
    assert any(e["descricao"] == "Assinatura projetada" for e in previstos)
    assert all(e["data"] > date.today().isoformat() for e in previstos)

    # nada persistido: nenhuma Transacao real existe para o template
    transacoes = client.get("/transacoes", headers=headers).json()
    assert all(t["descricao"] != "Assinatura projetada" for t in transacoes)


def test_desativar_conta_recorrente_nao_apaga_ocorrencias_ja_geradas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    data_inicio = _primeiro_dia_meses_atras(date.today(), 1)
    conta_recorrente = _criar_conta_recorrente(
        client, headers, conta_id=conta["id"], dia_vencimento=1, data_inicio=data_inicio
    ).json()

    client.delete(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers)

    ocorrencias = client.get(
        f"/transacoes?origem_recorrente_id={conta_recorrente['id']}", headers=headers
    ).json()
    assert len(ocorrencias) == 2


def test_desativar_conta_recorrente_ja_desativada_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    conta_recorrente = _criar_conta_recorrente(client, headers, conta_id=conta["id"]).json()
    client.delete(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers)

    resposta = client.delete(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers)
    assert resposta.status_code == 422


def test_desativar_conta_recorrente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    conta_ana = _criar_conta(client, headers_ana)
    conta_recorrente = _criar_conta_recorrente(client, headers_ana, conta_id=conta_ana["id"]).json()

    resposta = client.delete(f"/contas-recorrentes/{conta_recorrente['id']}", headers=headers_bruno)
    assert resposta.status_code == 404
