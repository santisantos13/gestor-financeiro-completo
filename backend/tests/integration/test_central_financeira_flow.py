"""Testes de integração da Central Financeira: TestClient + banco real
(SQLite em memória). Cobre os 11 endpoints agregadores via HTTP de verdade
- autenticação obrigatória, isolamento entre usuários (dados de um usuário
nunca vazam para a Central de outro), estado vazio (usuário novo não quebra
nenhum endpoint) e alguns valores agregados de ponta a ponta (criando dados
reais via os próprios endpoints de domínio, nunca inserindo direto no
banco - a Central é testada exatamente como o frontend a consumiria).
"""
from datetime import date, timedelta
from decimal import Decimal


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente", saldo_inicial="1000.00"):
    resposta = client.post("/contas", json={"nome": nome, "saldo_inicial": saldo_inicial}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_cartao(client, headers, conta_id, nome="Cartao"):
    payload = {
        "nome": nome,
        "conta_pagamento_id": conta_id,
        "instituicao": "Banco",
        "bandeira": "VISA",
        "ultimos_quatro_digitos": "1234",
        "limite": "5000.00",
        "dia_fechamento": 10,
        "dia_vencimento": 20,
    }
    resposta = client.post("/cartoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_transacao(client, headers, **overrides):
    payload = {
        "tipo": "DESPESA",
        "valor": "50.00",
        "data": str(date.today()),
        "descricao": "Lançamento qualquer",
        "status": "PAGO",
    }
    payload.update(overrides)
    resposta = client.post("/transacoes", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_categoria(client, headers, nome="Categoria"):
    resposta = client.post("/categorias", json={"nome": nome}, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_financiamento(client, headers, conta_id, **overrides):
    payload = {
        "descricao": "Carro",
        "instituicao_financeira": "Banco X",
        "valor_financiado": "10000.00",
        "taxa_juros": "0.01",
        "sistema_amortizacao": "PRICE",
        "num_parcelas": 12,
        "data_inicio": str(date.today()),
        "conta_id": conta_id,
    }
    payload.update(overrides)
    resposta = client.post("/financiamentos", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_meta(client, headers, **overrides):
    payload = {"descricao": "Viagem", "valor_alvo": "2000.00"}
    payload.update(overrides)
    resposta = client.post("/metas", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_transferencia(client, headers, conta_origem_id, conta_destino_id, **overrides):
    payload = {
        "conta_origem_id": conta_origem_id,
        "conta_destino_id": conta_destino_id,
        "valor": "300.00",
        "data": str(date.today()),
    }
    payload.update(overrides)
    resposta = client.post("/transferencias", json=payload, headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


ENDPOINTS = [
    "/resumo",
    "/saldo-consolidado",
    "/contas",
    "/cartoes",
    "/faturas",
    "/financiamentos",
    "/emprestimos",
    "/metas",
    "/agenda",
    "/calendario",
    "/visao-mensal",
    "/indicadores",
    "/atividades",
    "/graficos/tendencias",
    "/graficos/periodo",
]


# --- autenticação ------------------------------------------------------------

def test_todos_os_endpoints_exigem_autenticacao(client):
    for endpoint in ENDPOINTS:
        resposta = client.get(f"/central-financeira{endpoint}")
        assert resposta.status_code == 401, f"{endpoint} deveria exigir autenticação"


# --- estado vazio (usuário novo, sem nenhum dado cadastrado) ------------------

def test_usuario_novo_sem_nenhum_dado_nao_quebra_nenhum_endpoint(client):
    """A tela não pode quebrar nem mostrar erro para um usuário recém-
    criado - todo endpoint deve devolver 200 com listas vazias/zeros."""
    headers = _registrar_e_logar(client)
    for endpoint in ENDPOINTS:
        resposta = client.get(f"/central-financeira{endpoint}", headers=headers)
        assert resposta.status_code == 200, f"{endpoint}: {resposta.text}"


def test_usuario_novo_saldo_consolidado_e_zero(client):
    headers = _registrar_e_logar(client)
    resposta = client.get("/central-financeira/saldo-consolidado", headers=headers)
    dados = resposta.json()
    assert dados["saldo_total"] == "0"
    assert dados["contas"] == []


def test_usuario_novo_indicadores_gerais_todos_zerados(client):
    headers = _registrar_e_logar(client)
    dados = client.get("/central-financeira/indicadores", headers=headers).json()
    assert dados == {
        "contas_ativas": 0,
        "cartoes_ativos": 0,
        "faturas_em_aberto": 0,
        "financiamentos_ativos": 0,
        "emprestimos_ativos": 0,
        "metas_ativas": 0,
        "percentual_medio_metas": "0.00",
        "parcelas_atrasadas": 0,
    }


# --- resumo das contas / saldo consolidado ------------------------------------

def test_saldo_consolidado_soma_saldo_atual_de_todas_as_contas_ativas(client):
    headers = _registrar_e_logar(client)
    _criar_conta(client, headers, nome="Corrente", saldo_inicial="1000.00")
    _criar_conta(client, headers, nome="Poupança", saldo_inicial="500.00")

    dados = client.get("/central-financeira/saldo-consolidado", headers=headers).json()

    assert dados["saldo_total"] == "1500.00"
    assert {c["nome"] for c in dados["contas"]} == {"Corrente", "Poupança"}


def test_resumo_contas_reflete_saldo_atualizado_apos_transacao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="1000.00")
    _criar_transacao(client, headers, tipo="DESPESA", valor="300.00", status="PAGO", conta_id=conta["id"])

    dados = client.get("/central-financeira/contas", headers=headers).json()

    assert dados["contas"][0]["saldo_atual"] == "700.00"


# --- resumo dos cartões / faturas ---------------------------------------------

def test_resumo_cartoes_reflete_gasto_em_fatura_aberta(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    _criar_transacao(client, headers, tipo="DESPESA", valor="250.00", cartao_id=cartao["id"])

    resumo_cartoes = client.get("/central-financeira/cartoes", headers=headers).json()
    resumo_faturas = client.get("/central-financeira/faturas", headers=headers).json()

    assert resumo_cartoes["total_utilizado"] == "250.00"
    assert resumo_cartoes["cartoes"][0]["limite_disponivel"] == "4750.00"
    assert resumo_faturas["faturas"][0]["valor_total"] == "250.00"
    assert resumo_faturas["faturas"][0]["status"] == "ABERTA"


def test_resumo_cartoes_sem_nenhum_cartao_cadastrado(client):
    headers = _registrar_e_logar(client)
    dados = client.get("/central-financeira/cartoes", headers=headers).json()
    assert dados == {"cartoes": [], "total_utilizado": "0"}


# --- resumo agregado dos cartões ("Dashboard de Cartões") ------------------------


def test_resumo_cartoes_agregado_soma_limites_e_calcula_percentual(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao_a = _criar_cartao(client, headers, conta["id"], nome="Cartao A")
    cartao_b = _criar_cartao(client, headers, conta["id"], nome="Cartao B")
    _criar_transacao(client, headers, tipo="DESPESA", valor="1000.00", cartao_id=cartao_a["id"])

    dados = client.get("/central-financeira/cartoes/agregado", headers=headers).json()

    assert dados["limite_total"] == "10000.00"
    assert dados["limite_usado_total"] == "1000.00"
    assert dados["limite_disponivel_total"] == "9000.00"
    assert dados["percentual_usado_geral"] == "10.00"
    assert dados["quantidade_cartoes"] == 2
    assert dados["faturas_em_aberto"] == 1
    assert len(dados["proximos_vencimentos"]) == 1
    assert dados["proximos_vencimentos"][0]["cartao_id"] == cartao_a["id"]
    assert {item["nome"] for item in dados["distribuicao_uso"]} == {"Cartao A", "Cartao B"}


def test_resumo_cartoes_agregado_sem_nenhum_cartao_cadastrado(client):
    headers = _registrar_e_logar(client)
    dados = client.get("/central-financeira/cartoes/agregado", headers=headers).json()
    assert dados == {
        "limite_total": "0",
        "limite_disponivel_total": "0",
        "limite_usado_total": "0",
        "percentual_usado_geral": "0",
        "quantidade_cartoes": 0,
        "faturas_em_aberto": 0,
        "proximos_vencimentos": [],
        "distribuicao_uso": [],
    }


# --- resumo de financiamentos ---------------------------------------------------

def test_resumo_financiamentos_traz_metricas_de_parcelas(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_financiamento(client, headers, conta["id"], num_parcelas=4)

    dados = client.get("/central-financeira/financiamentos", headers=headers).json()

    financiamento = dados["financiamentos"][0]
    assert financiamento["parcelas_pagas"] == 0
    assert financiamento["parcelas_restantes"] == 4
    assert financiamento["valor_total_pago"] == "0"
    assert financiamento["proxima_parcela_data"] is not None


def test_pagar_parcela_reflete_em_parcelas_pagas_do_resumo(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    financiamento = _criar_financiamento(client, headers, conta["id"], num_parcelas=2)

    resposta_pagamento = client.post(
        f"/financiamentos/{financiamento['id']}/parcelas/1/pagar", headers=headers
    )
    assert resposta_pagamento.status_code == 200, resposta_pagamento.text
    financiamento_pago = resposta_pagamento.json()

    dados = client.get("/central-financeira/financiamentos", headers=headers).json()
    resumo = dados["financiamentos"][0]
    assert resumo["parcelas_pagas"] == 1
    assert resumo["parcelas_restantes"] == 1
    # saldo_devedor e sempre LIDO do FinanciamentoService, nunca recalculado
    # pela Central - deve bater exatamente com o que o proprio endpoint de
    # pagamento (fonte da verdade) devolveu.
    assert resumo["saldo_devedor"] == financiamento_pago["saldo_devedor"]
    assert Decimal(resumo["saldo_devedor"]) < Decimal(financiamento["saldo_devedor"])


def test_resumo_emprestimos_vazio_quando_usuario_nao_tem_emprestimo(client):
    headers = _registrar_e_logar(client)
    _criar_conta(client, headers)
    dados = client.get("/central-financeira/emprestimos", headers=headers).json()
    assert dados == {"emprestimos": []}


# --- progresso das metas -------------------------------------------------------

def test_progresso_metas_reflete_aportes_pagos(client):
    # Aportes/resgates são Transferencia real para o cofrinho da Meta (ver
    # docs/analise-arquitetural-metas-transferencias.md) - não mais uma
    # Transacao com meta_id.
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")
    _criar_transferencia(
        client, headers, conta["id"], meta["conta_id"], valor="250.00"
    )

    dados = client.get("/central-financeira/metas", headers=headers).json()

    assert dados["metas"][0]["valor_acumulado"] == "250.00"
    assert dados["metas"][0]["percentual"] == "25.00"


# --- resumo financeiro geral / visão mensal ------------------------------------

def test_resumo_financeiro_reflete_entradas_saidas_e_saldo_do_mes_corrente(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="0")
    hoje = date.today()
    _criar_transacao(client, headers, tipo="RECEITA", valor="1000.00", status="PAGO", conta_id=conta["id"], data=str(hoje))
    _criar_transacao(client, headers, tipo="DESPESA", valor="400.00", status="PAGO", conta_id=conta["id"], data=str(hoje))

    dados = client.get("/central-financeira/resumo", headers=headers).json()

    assert dados["entradas_mes"] == "1000.00"
    assert dados["saidas_mes"] == "400.00"
    assert dados["fluxo_caixa_mes"] == "600.00"
    assert dados["saldo_total"] == "600.00"


def test_resumo_financeiro_ignora_transacao_pendente_nas_entradas_saidas(client):
    """`entradas_mes`/`saidas_mes` só somam `status=PAGO` - uma transação
    PENDENTE do mês corrente não deveria inflar o resumo."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="0")
    hoje = date.today()
    _criar_transacao(client, headers, tipo="RECEITA", valor="9999.00", status="PENDENTE", conta_id=conta["id"], data=str(hoje))

    dados = client.get("/central-financeira/resumo", headers=headers).json()
    assert Decimal(dados["entradas_mes"]) == Decimal("0")


def test_visao_mensal_aceita_periodo_explicito_diferente_do_atual(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="0")
    mes_passado = date.today().replace(day=1) - timedelta(days=1)
    _criar_transacao(
        client, headers, tipo="RECEITA", valor="500.00", status="PAGO", conta_id=conta["id"], data=str(mes_passado)
    )

    dados = client.get(
        "/central-financeira/visao-mensal",
        params={"ano": mes_passado.year, "mes": mes_passado.month},
        headers=headers,
    ).json()

    assert dados["ano"] == mes_passado.year
    assert dados["mes"] == mes_passado.month
    assert dados["entradas"] == "500.00"


def test_resumo_financeiro_com_mes_fora_de_faixa_devolve_422(client):
    """`mes=13` chegaria em `calendar.monthrange` e levantaria um ValueError
    não tratado (500) se não fosse validado no Router - ver
    docs/revisao-tecnica-central-financeira.md."""
    headers = _registrar_e_logar(client)
    resposta = client.get(
        "/central-financeira/resumo", params={"mes": 13, "ano": 2026}, headers=headers
    )
    assert resposta.status_code == 422


def test_visao_mensal_com_ano_fora_de_faixa_devolve_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.get(
        "/central-financeira/visao-mensal", params={"mes": 1, "ano": 30000}, headers=headers
    )
    assert resposta.status_code == 422


def test_agenda_financeira_com_dias_negativo_devolve_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.get("/central-financeira/agenda", params={"dias": -1}, headers=headers)
    assert resposta.status_code == 422


# --- agenda financeira ----------------------------------------------------------

def test_agenda_financeira_lista_parcela_de_financiamento_futura(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_financiamento(client, headers, conta["id"], num_parcelas=3)

    dados = client.get("/central-financeira/agenda", params={"dias": 90}, headers=headers).json()

    assert len(dados["eventos"]) >= 1
    assert dados["eventos"][0]["origem_tipo"] == "FINANCIAMENTO"


def test_agenda_financeira_respeita_janela_de_dias(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    futuro_distante = date.today() + timedelta(days=200)
    _criar_transacao(
        client, headers, tipo="DESPESA", valor="80.00", status="PENDENTE", conta_id=conta["id"], data=str(futuro_distante)
    )

    dados = client.get("/central-financeira/agenda", params={"dias": 30}, headers=headers).json()
    assert dados["eventos"] == []


def test_agenda_financeira_inclui_fatura_mesmo_com_mais_de_tres_ciclos_de_historico(client):
    """Mesmo bug/correção de
    `test_calendario_financeiro_inclui_fatura_mesmo_com_mais_de_tres_ciclos_de_historico`,
    aplicado a `agenda_financeira` - os dois usavam a mesma chamada
    (`FaturaService.listar(..., limit=3)`, ordem ascendente) e tinham o
    mesmo bug."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    hoje = date.today()

    for n in range(4, 0, -1):
        resposta = client.post(
            "/faturas",
            json={"cartao_id": cartao["id"], "mes_referencia": str(_mes_referencia_ha_n_meses(hoje, n))},
            headers=headers,
        )
        assert resposta.status_code == 201, resposta.text

    mes_referencia_futuro = _mes_referencia_ha_n_meses(hoje, -1)
    fatura_futura = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": str(mes_referencia_futuro)},
        headers=headers,
    ).json()

    dados = client.get("/central-financeira/agenda", params={"dias": 60}, headers=headers).json()

    ids_fatura = [e["origem_id"] for e in dados["eventos"] if e["origem_tipo"] == "FATURA"]
    assert fatura_futura["id"] in ids_fatura


# --- calendário financeiro (Etapa de Transferências/Calendário) -----------------

def test_calendario_financeiro_com_mes_fora_de_faixa_devolve_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.get(
        "/central-financeira/calendario", params={"mes": 13, "ano": 2026}, headers=headers
    )
    assert resposta.status_code == 422


def test_calendario_financeiro_inclui_transacao_paga_do_mes_atual(client):
    """Diferente de `/agenda` (só PENDENTE), o calendário inclui uma
    transação já PAGA do mês corrente - é exatamente o gap que motivou o
    endpoint novo."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_transacao(client, headers, tipo="RECEITA", valor="1000.00", status="PAGO", conta_id=conta["id"])

    dados = client.get("/central-financeira/calendario", headers=headers).json()

    eventos_receita = [e for e in dados["eventos"] if e["categoria"] == "RECEITA"]
    assert len(eventos_receita) == 1
    assert eventos_receita[0]["status"] == "PAGO"
    assert eventos_receita[0]["origem_tipo"] == "TRANSACAO"


def test_calendario_financeiro_categoriza_parcela_de_financiamento_com_cor_propria(client):
    """Pedido do usuário (2026-07-21, "pode dar uma cor"): parcela de
    Financiamento não deve mais aparecer com a mesma categoria genérica
    (DESPESA) de qualquer outra transação - ganha `categoria=FINANCIAMENTO`
    própria (cor dedicada na legenda do calendário)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    financiamento = _criar_financiamento(client, headers, conta["id"], num_parcelas=3)

    dados = client.get("/central-financeira/calendario", headers=headers).json()

    eventos_financiamento = [e for e in dados["eventos"] if e["origem_tipo"] == "FINANCIAMENTO"]
    assert len(eventos_financiamento) >= 1
    assert all(e["categoria"] == "FINANCIAMENTO" for e in eventos_financiamento)
    assert all(e["origem_id"] == financiamento["id"] for e in eventos_financiamento)


def test_calendario_financeiro_exclui_compra_de_cartao(client):
    """Bug real corrigido (2026-07-20, pedido explícito do usuário: "o
    ideal é que no calendário apareça apenas pagamento de faturas, faturas
    abertas, etc"). Uma compra no cartão nasce sempre `status=PAGO`
    (`TransacaoService.criar`), então não era filtrada nem por
    `agenda_financeira` (só `PENDENTE`) nem pelo antigo `calendario_financeiro`
    (que aceitava qualquer status) - cada parcela de uma compra parcelada
    virava um evento próprio, redundante com o evento de "Vencimento —
    fatura" do mesmo ciclo. O cartão continua representado no calendário só
    pelos eventos de Fatura (fechamento/vencimento), nunca por transação
    individual."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    _criar_transacao(client, headers, tipo="DESPESA", valor="80.00", cartao_id=cartao["id"])
    # compra de CONTA continua aparecendo normalmente, no mesmo mês.
    _criar_transacao(client, headers, tipo="DESPESA", valor="30.00", conta_id=conta["id"])

    dados = client.get("/central-financeira/calendario", headers=headers).json()

    eventos_despesa = [e for e in dados["eventos"] if e["categoria"] == "DESPESA"]
    assert len(eventos_despesa) == 1
    assert eventos_despesa[0]["valor"] == "30.00"


def _mes_referencia_ha_n_meses(hoje: date, n: int) -> date:
    mes = hoje.month - n
    ano = hoje.year
    while mes <= 0:
        mes += 12
        ano -= 1
    return date(ano, mes, 1)


def test_calendario_financeiro_inclui_fatura_mesmo_com_mais_de_tres_ciclos_de_historico(client):
    """Bug real corrigido em 2026-07-21 ("calendário não exibe fechamento/
    vencimento de fatura"): `calendario_financeiro` busca as faturas do
    cartão com `limit=3` esperando as 3 MAIS RECENTES (o ciclo atual +
    folga), mas usava `FaturaService.listar` - que ordena por
    `mes_referencia` ASCENDENTE (pedido do usuário para a tela de listagem
    de faturas, 2026-07-20). Qualquer cartão com mais de 3 meses de fatura
    no histórico passava a nunca mais mostrar o ciclo ATUAL no calendário,
    só os 3 mais antigos - corrigido usando `listar_recentes` (ordem
    DESCENDENTE), método novo e separado porque as duas telas têm ordens
    opostas e nenhuma relação entre si."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"])
    hoje = date.today()

    # 4 ciclos antigos - mais que o `limit=3` do calendário, exatamente o
    # cenário que expunha o bug.
    for n in range(4, 0, -1):
        resposta = client.post(
            "/faturas",
            json={"cartao_id": cartao["id"], "mes_referencia": str(_mes_referencia_ha_n_meses(hoje, n))},
            headers=headers,
        )
        assert resposta.status_code == 201, resposta.text

    fatura_atual = client.post(
        "/faturas",
        json={"cartao_id": cartao["id"], "mes_referencia": str(date(hoje.year, hoje.month, 1))},
        headers=headers,
    ).json()

    dados = client.get(
        "/central-financeira/calendario", params={"ano": hoje.year, "mes": hoje.month}, headers=headers
    ).json()

    categorias_da_fatura_atual = {
        e["categoria"] for e in dados["eventos"] if e["origem_id"] == fatura_atual["id"]
    }
    assert categorias_da_fatura_atual & {"FATURA_FECHAMENTO", "FATURA_VENCIMENTO"}


def test_calendario_financeiro_inclui_transferencia_ativa_do_mes(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Corrente", saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, nome="Poupança", saldo_inicial="0.00")
    _criar_transferencia(client, headers, origem["id"], destino["id"], valor="300.00")

    dados = client.get("/central-financeira/calendario", headers=headers).json()

    eventos_transferencia = [e for e in dados["eventos"] if e["categoria"] == "TRANSFERENCIA"]
    assert len(eventos_transferencia) == 1
    assert eventos_transferencia[0]["origem_tipo"] == "TRANSFERENCIA"
    assert eventos_transferencia[0]["valor"] == "300.00"
    assert eventos_transferencia[0]["descricao"] == "Corrente → Poupança"


def test_calendario_financeiro_exclui_transferencia_cancelada(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, saldo_inicial="0.00")
    transferencia = _criar_transferencia(client, headers, origem["id"], destino["id"])
    client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)

    dados = client.get("/central-financeira/calendario", headers=headers).json()
    assert [e for e in dados["eventos"] if e["categoria"] == "TRANSFERENCIA"] == []


def test_calendario_financeiro_inclui_meta_com_prazo_no_mes_atual(client):
    headers = _registrar_e_logar(client)
    _criar_meta(client, headers, descricao="Viagem", valor_alvo="5000.00", data_alvo=str(date.today()))

    dados = client.get("/central-financeira/calendario", headers=headers).json()

    eventos_meta = [e for e in dados["eventos"] if e["categoria"] == "META"]
    assert len(eventos_meta) == 1
    assert eventos_meta[0]["origem_tipo"] == "META"
    assert eventos_meta[0]["valor"] == "5000.00"


# --- isolamento entre usuários --------------------------------------------------

def test_dados_de_outro_usuario_nunca_aparecem_na_central(client):
    headers_a = _registrar_e_logar(client, email="a@example.com")
    headers_b = _registrar_e_logar(client, email="b@example.com")

    conta_a = _criar_conta(client, headers_a, nome="Conta de A", saldo_inicial="1000.00")
    _criar_conta(client, headers_b, nome="Conta de B", saldo_inicial="99999.00")
    _criar_meta(client, headers_a, descricao="Meta de A")
    _criar_meta(client, headers_b, descricao="Meta de B")

    resumo_a = client.get("/central-financeira/saldo-consolidado", headers=headers_a).json()
    metas_a = client.get("/central-financeira/metas", headers=headers_a).json()

    assert resumo_a["saldo_total"] == "1000.00"
    assert [c["nome"] for c in resumo_a["contas"]] == ["Conta de A"]
    assert [m["descricao"] for m in metas_a["metas"]] == ["Meta de A"]


# --- central de atividades (Sprint de Refinamento Premium, item 17) -----------

def test_atividades_recentes_usuario_novo_devolve_lista_vazia(client):
    headers = _registrar_e_logar(client)
    dados = client.get("/central-financeira/atividades", headers=headers).json()
    assert dados["atividades"] == []


def test_atividades_recentes_inclui_transacao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_transacao(
        client, headers, tipo="DESPESA", valor="42.00", descricao="Mercado", conta_id=conta["id"]
    )

    dados = client.get("/central-financeira/atividades", headers=headers).json()

    origens = {(a["origem_tipo"], a["descricao"]) for a in dados["atividades"]}
    assert ("TRANSACAO", "Mercado") in origens
    item = next(a for a in dados["atividades"] if a["descricao"] == "Mercado")
    assert item["valor"] == "42.00"


def test_atividades_recentes_inclui_transferencia_ativa(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Corrente", saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, nome="Poupança", saldo_inicial="0.00")
    _criar_transferencia(client, headers, origem["id"], destino["id"], valor="300.00")

    dados = client.get("/central-financeira/atividades", headers=headers).json()

    transferencias = [a for a in dados["atividades"] if a["origem_tipo"] == "TRANSFERENCIA"]
    assert len(transferencias) == 1
    assert transferencias[0]["valor"] == "300.00"
    assert transferencias[0]["descricao"] == "Transferência entre contas"


def test_atividades_recentes_exclui_transferencia_cancelada(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, saldo_inicial="0.00")
    transferencia = _criar_transferencia(client, headers, origem["id"], destino["id"])
    client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)

    dados = client.get("/central-financeira/atividades", headers=headers).json()
    assert [a for a in dados["atividades"] if a["origem_tipo"] == "TRANSFERENCIA"] == []


def test_atividades_recentes_inclui_meta_concluida_via_aporte(client):
    """Meta é concluída quando o cofrinho (`meta.conta_id`) recebe aportes
    (transferências) que somam o `valor_alvo` - ver `MetaService.criar` e
    docstring de `_anexar_progresso`. Isso deve aparecer como uma
    atividade "Meta concluída"."""
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Corrente", saldo_inicial="2000.00")
    meta = _criar_meta(client, headers, descricao="Viagem", valor_alvo="2000.00")
    _criar_transferencia(
        client, headers, origem["id"], meta["conta_id"], valor="2000.00", descricao="Aporte"
    )

    dados = client.get("/central-financeira/atividades", headers=headers).json()

    metas_concluidas = [a for a in dados["atividades"] if a["origem_tipo"] == "META"]
    assert len(metas_concluidas) == 1
    assert metas_concluidas[0]["descricao"] == "Meta concluída: Viagem"
    assert metas_concluidas[0]["valor"] == "2000.00"


def test_atividades_recentes_exclui_parcelas_futuras_de_financiamento(client):
    """Bug de continuação relatado pelo usuário (2026-07-21, mesmo dia da
    correção de `criado_em` → `data`): Financiamento pré-gera TODAS as
    parcelas na criação do contrato, muitas décadas à frente - sem um
    corte por data, "Transações recentes" (que ordena por `data DESC`)
    sempre mostrava as parcelas MAIS distantes no futuro primeiro (maior
    valor de `data` de toda a tabela), em vez do que de fato já
    aconteceu. "Recente" é sempre passado; agendado futuro já tem sua
    própria seção (Hoje/Agenda)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    # Financiamento com data_inicio bem no futuro: TODAS as parcelas
    # nascem com `data` > hoje (nenhuma delas deve aparecer aqui).
    _criar_financiamento(
        client, headers, conta["id"], num_parcelas=3, data_inicio=str(date.today() + timedelta(days=60)),
    )
    _criar_transacao(
        client, headers, tipo="DESPESA", valor="50.00", descricao="Compra de hoje", conta_id=conta["id"],
    )

    dados = client.get("/central-financeira/atividades", headers=headers).json()

    origens = [a["origem_tipo"] for a in dados["atividades"]]
    assert "FINANCIAMENTO" not in origens
    descricoes = [a["descricao"] for a in dados["atividades"]]
    assert descricoes == ["Compra de hoje"]


def test_atividades_recentes_ordenadas_da_mais_recente_para_a_mais_antiga(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    _criar_transacao(client, headers, descricao="Primeira", conta_id=conta["id"])
    _criar_transacao(client, headers, descricao="Segunda", conta_id=conta["id"])
    _criar_transacao(client, headers, descricao="Terceira", conta_id=conta["id"])

    dados = client.get("/central-financeira/atividades", headers=headers).json()

    data_horas = [a["data_hora"] for a in dados["atividades"]]
    assert data_horas == sorted(data_horas, reverse=True)


def test_atividades_recentes_respeita_parametro_limit(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    for indice in range(5):
        _criar_transacao(client, headers, descricao=f"Lançamento {indice}", conta_id=conta["id"])

    dados = client.get(
        "/central-financeira/atividades", params={"limit": 2}, headers=headers
    ).json()

    assert len(dados["atividades"]) == 2


def test_atividades_recentes_nao_vazam_entre_usuarios(client):
    headers_a = _registrar_e_logar(client, email="ativ-a@example.com")
    headers_b = _registrar_e_logar(client, email="ativ-b@example.com")
    conta_a = _criar_conta(client, headers_a)
    conta_b = _criar_conta(client, headers_b)
    _criar_transacao(client, headers_a, descricao="Gasto de A", conta_id=conta_a["id"])
    _criar_transacao(client, headers_b, descricao="Gasto de B", conta_id=conta_b["id"])

    dados_a = client.get("/central-financeira/atividades", headers=headers_a).json()

    descricoes = [a["descricao"] for a in dados_a["atividades"]]
    assert descricoes == ["Gasto de A"]


# --- gráficos (docs/analise-arquitetural-graficos.md) ---------------------------

def test_graficos_tendencias_usuario_novo_devolve_baseline_zero(client):
    headers = _registrar_e_logar(client)
    dados = client.get("/central-financeira/graficos/tendencias", params={"meses": 3}, headers=headers).json()

    assert len(dados["meses"]) == 3
    assert all(m["saldo_total"] == "0" for m in dados["meses"])
    assert all(m["entradas"] == "0" and m["saidas"] == "0" for m in dados["meses"])


def test_graficos_tendencias_reflete_saldo_inicial_e_movimentacao_do_mes(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers, saldo_inicial="1000.00")
    _criar_transacao(client, headers, tipo="RECEITA", valor="500.00", status="PAGO", conta_id=conta["id"])
    _criar_transacao(client, headers, tipo="DESPESA", valor="80.00", status="PAGO", conta_id=conta["id"])

    dados = client.get("/central-financeira/graficos/tendencias", params={"meses": 3}, headers=headers).json()

    mes_atual = dados["meses"][-1]
    assert mes_atual["saldo_total"] == "1420.00"
    assert mes_atual["entradas"] == "500.00"
    assert mes_atual["saidas"] == "80.00"
    # Meses anteriores (sem nenhum lançamento) ficam no ponto de partida.
    assert dados["meses"][0]["saldo_total"] == "1000.00"


def test_graficos_tendencias_valida_limite_de_meses(client):
    headers = _registrar_e_logar(client)
    resposta = client.get("/central-financeira/graficos/tendencias", params={"meses": 37}, headers=headers)
    assert resposta.status_code == 422


def test_graficos_periodo_usuario_novo_devolve_listas_vazias(client):
    headers = _registrar_e_logar(client)
    dados = client.get("/central-financeira/graficos/periodo", headers=headers).json()
    assert dados["gastos_por_categoria"] == []
    assert dados["gastos_por_cartao"] == []


def test_graficos_periodo_agrupa_despesas_por_categoria(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    categoria = _criar_categoria(client, headers, nome="Mercado")
    _criar_transacao(
        client, headers, tipo="DESPESA", valor="120.00", status="PAGO",
        conta_id=conta["id"], categoria_id=categoria["id"],
    )
    _criar_transacao(client, headers, tipo="DESPESA", valor="30.00", status="PAGO", conta_id=conta["id"])

    dados = client.get("/central-financeira/graficos/periodo", headers=headers).json()

    por_id = {item["categoria_id"]: item for item in dados["gastos_por_categoria"]}
    assert por_id[categoria["id"]]["categoria_nome"] == "Mercado"
    assert por_id[categoria["id"]]["total"] == "120.00"
    assert por_id[None]["categoria_nome"] == "Sem categoria"
    assert por_id[None]["total"] == "30.00"


def test_graficos_periodo_agrupa_gastos_por_cartao(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    cartao = _criar_cartao(client, headers, conta["id"], nome="Nubank")
    _criar_transacao(client, headers, tipo="DESPESA", valor="200.00", cartao_id=cartao["id"])

    dados = client.get("/central-financeira/graficos/periodo", headers=headers).json()

    assert dados["gastos_por_cartao"] == [
        {"cartao_id": cartao["id"], "cartao_nome": "Nubank", "total": "200.00"}
    ]


def test_graficos_periodo_respeita_mes_selecionado(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    categoria = _criar_categoria(client, headers)
    mes_passado = _mes_referencia_ha_n_meses(date.today(), 2)
    _criar_transacao(
        client, headers, tipo="DESPESA", valor="90.00", status="PAGO",
        conta_id=conta["id"], categoria_id=categoria["id"], data=str(mes_passado),
    )

    dados_mes_atual = client.get("/central-financeira/graficos/periodo", headers=headers).json()
    dados_mes_passado = client.get(
        "/central-financeira/graficos/periodo",
        params={"ano": mes_passado.year, "mes": mes_passado.month},
        headers=headers,
    ).json()

    assert dados_mes_atual["gastos_por_categoria"] == []
    assert dados_mes_passado["gastos_por_categoria"][0]["total"] == "90.00"


def test_graficos_nao_vazam_entre_usuarios(client):
    headers_a = _registrar_e_logar(client, email="graf-a@example.com")
    headers_b = _registrar_e_logar(client, email="graf-b@example.com")
    conta_a = _criar_conta(client, headers_a, saldo_inicial="1000.00")
    conta_b = _criar_conta(client, headers_b, saldo_inicial="0.00")

    dados_a = client.get("/central-financeira/graficos/tendencias", headers=headers_a).json()
    dados_b = client.get("/central-financeira/graficos/tendencias", headers=headers_b).json()

    assert dados_a["meses"][-1]["saldo_total"] == "1000.00"
    assert dados_b["meses"][-1]["saldo_total"] == "0.00"
