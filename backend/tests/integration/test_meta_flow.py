"""Testes de integração do CRUD de Meta: TestClient + banco real (SQLite
em memória). Cobre isolamento entre usuários, unicidade de descrição, soft
delete via HTTP real, exclusão definitiva (hard delete) e o refatoramento
de aportes/resgates como Transferência (ver
docs/analise-arquitetural-metas-transferencias.md):

- `conta_id` deixou de ser um campo aceito em `POST/PATCH /metas` - é
  sempre o "cofrinho" (Conta oculta) provisionado automaticamente pelo
  MetaService na criação. Enviar `conta_id` no payload agora é
  silenciosamente ignorado (comportamento padrão do Pydantic v2 para campo
  desconhecido).
- `valor_acumulado` passa a somar DUAS fontes: o histórico legado
  (`Transacao.meta_id`, CONGELADO - nenhuma Transacao nova pode mais ser
  marcada assim, só simulável aqui inserindo direto no banco via
  `db_session`) e o saldo do cofrinho (soma de `Transferencia` reais via
  `POST /transferencias`).
- `meta_id` deixou de ser um campo aceito em `POST/PATCH /transacoes` -
  enviá-lo também é silenciosamente ignorado. O filtro de LEITURA
  `GET /transacoes?meta_id=` continua funcionando (sustenta o histórico
  legado).
"""
from datetime import date

from app.models import Conta, Transacao
from app.models.enums import StatusTransacao, TipoTransacao


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _usuario_id_da_conta(db_session, conta_id):
    """Não existe endpoint "quem sou eu" - descobrimos o usuario_id
    olhando direto no banco a partir de uma Conta que sabemos ser dele
    (só usado para simular a Transacao legada via db_session abaixo)."""
    return db_session.get(Conta, conta_id).usuario_id


def _criar_conta(client, headers, nome="Conta Corrente", saldo_inicial="1000.00"):
    resposta = client.post(
        "/contas", json={"nome": nome, "saldo_inicial": saldo_inicial}, headers=headers
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _payload_meta(**overrides):
    payload = {
        "descricao": "Viagem para o Japão",
        "valor_alvo": "15000.00",
    }
    payload.update(overrides)
    return payload


def _criar_meta(client, headers, **overrides):
    resposta = client.post("/metas", json=_payload_meta(**overrides), headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _aportar(client, headers, conta_origem_id, meta, valor="100.00", **overrides):
    """Aporte = Transferencia real da Conta do usuário para o cofrinho da
    Meta (`meta["conta_id"]`) - reaproveita 100% o endpoint existente de
    Transferência, sem endpoint dedicado (ver seção 4 da análise)."""
    payload = {
        "conta_origem_id": conta_origem_id,
        "conta_destino_id": meta["conta_id"],
        "valor": valor,
        "data": "2026-07-15",
        "descricao": "Aporte",
    }
    payload.update(overrides)
    return client.post("/transferencias", json=payload, headers=headers)


def _resgatar(client, headers, meta, conta_destino_id, valor="100.00", **overrides):
    """Resgate = Transferencia real do cofrinho da Meta de volta para uma
    Conta do usuário."""
    payload = {
        "conta_origem_id": meta["conta_id"],
        "conta_destino_id": conta_destino_id,
        "valor": valor,
        "data": "2026-07-16",
        "descricao": "Resgate",
    }
    payload.update(overrides)
    return client.post("/transferencias", json=payload, headers=headers)


def _inserir_transacao_legada_com_meta(db_session, usuario_id, conta_id, meta_id, **overrides):
    """Simula um registro CONGELADO de antes do refatoramento: uma
    Transacao com `meta_id` preenchido. Inserida direto no banco (não via
    API) porque `POST /transacoes` não aceita mais `meta_id` - é
    exatamente esse o comportamento que estamos validando (a leitura
    continua funcionando, só a escrita nova foi removida)."""
    dados = {
        "usuario_id": usuario_id,
        "tipo": TipoTransacao.RECEITA,
        "valor": "250.00",
        "data": date(2026, 6, 1),
        "descricao": "Aporte legado (pré-refatoramento)",
        "status": StatusTransacao.PAGO,
        "conta_id": conta_id,
        "meta_id": meta_id,
    }
    dados.update(overrides)
    transacao = Transacao(**dados)
    db_session.add(transacao)
    db_session.commit()
    db_session.refresh(transacao)
    return transacao


# --- autenticação / estrutura -----------------------------------------------

def test_criar_meta_sem_autenticacao_retorna_401(client):
    resposta = client.post("/metas", json=_payload_meta())
    assert resposta.status_code == 401


def test_criar_e_obter_meta(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)

    assert meta["descricao"] == "Viagem para o Japão"
    assert meta["valor_alvo"] == "15000.00"
    assert isinstance(meta["conta_id"], int)  # cofrinho provisionado automaticamente
    assert meta["ativo"] is True
    assert meta["valor_acumulado"] == "0.00" or meta["valor_acumulado"] == "0"
    assert meta["percentual"] == "0.00"

    resposta = client.get(f"/metas/{meta['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == meta["id"]


def test_criar_meta_com_valor_alvo_zero_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post("/metas", json=_payload_meta(valor_alvo="0"), headers=headers)
    assert resposta.status_code == 422


def test_criar_meta_ignora_conta_id_enviado_no_payload(client):
    """`conta_id` não é mais um campo aceito em POST /metas - o cofrinho é
    sempre o provisionado automaticamente, nunca escolhido pelo usuário."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)

    meta = _criar_meta(client, headers, conta_id=conta["id"])

    assert meta["conta_id"] != conta["id"]


def test_criar_meta_provisiona_cofrinho_oculto_que_nao_aparece_em_get_contas(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)

    contas = client.get("/contas", headers=headers).json()
    ids_visiveis = {c["id"] for c in contas}
    assert meta["conta_id"] not in ids_visiveis


def test_criar_meta_com_descricao_duplicada_retorna_409(client):
    headers = _registrar_e_logar(client)
    _criar_meta(client, headers, descricao="Viagem")

    resposta = client.post("/metas", json=_payload_meta(descricao="Viagem"), headers=headers)
    assert resposta.status_code == 409


def test_criar_meta_com_mesma_descricao_em_usuarios_diferentes_e_permitido(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    meta_ana = _criar_meta(client, headers_ana, descricao="Viagem")
    meta_bruno = _criar_meta(client, headers_bruno, descricao="Viagem")
    assert meta_ana["id"] != meta_bruno["id"]


def test_criar_meta_com_descricao_de_meta_desativada_reativa(client):
    headers = _registrar_e_logar(client)
    original = _criar_meta(client, headers, descricao="Viagem", valor_alvo="10000.00")
    client.delete(f"/metas/{original['id']}", headers=headers)

    recriada = _criar_meta(client, headers, descricao="Viagem", valor_alvo="20000.00")

    assert recriada["id"] == original["id"]
    assert recriada["ativo"] is True
    assert recriada["valor_alvo"] == "20000.00"
    assert recriada["conta_id"] == original["conta_id"]  # cofrinho preservado, não recriado


# --- obter / listar ------------------------------------------------------

def test_listar_metas_retorna_apenas_as_do_usuario_autenticado(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")

    _criar_meta(client, headers_ana, descricao="Meta da Ana")
    _criar_meta(client, headers_bruno, descricao="Meta do Bruno")

    resposta = client.get("/metas", headers=headers_ana)
    descricoes = [m["descricao"] for m in resposta.json()]
    assert descricoes == ["Meta da Ana"]


def test_obter_meta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    meta_ana = _criar_meta(client, headers_ana)

    resposta = client.get(f"/metas/{meta_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


# --- atualizar (PATCH) ------------------------------------------------------

def test_atualizar_meta_parcial(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers, descricao="Original")

    resposta = client.patch(f"/metas/{meta['id']}", json={"valor_alvo": "9000.00"}, headers=headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["descricao"] == "Original"
    assert corpo["valor_alvo"] == "9000.00"


def test_atualizar_meta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    meta_ana = _criar_meta(client, headers_ana)

    resposta = client.patch(
        f"/metas/{meta_ana['id']}", json={"descricao": "Hackeada"}, headers=headers_bruno
    )
    assert resposta.status_code == 404


def test_atualizar_meta_ignora_conta_id_enviado_no_payload(client):
    """`conta_id` também não é aceito em PATCH /metas - o cofrinho nunca
    troca depois de criado."""
    headers = _registrar_e_logar(client)
    outra_conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers)

    resposta = client.patch(
        f"/metas/{meta['id']}", json={"conta_id": outra_conta["id"]}, headers=headers
    )

    assert resposta.status_code == 200
    assert resposta.json()["conta_id"] == meta["conta_id"]


def test_atualizar_descricao_para_descricao_ja_usada_retorna_409(client):
    headers = _registrar_e_logar(client)
    _criar_meta(client, headers, descricao="Viagem")
    carro = _criar_meta(client, headers, descricao="Carro")

    resposta = client.patch(f"/metas/{carro['id']}", json={"descricao": "Viagem"}, headers=headers)
    assert resposta.status_code == 409


def test_atualizar_ativo_true_reativa_meta_diretamente(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)
    client.delete(f"/metas/{meta['id']}", headers=headers)

    resposta = client.patch(f"/metas/{meta['id']}", json={"ativo": True}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is True


# --- desativar (DELETE = soft delete) ---------------------------------------

def test_desativar_meta_e_soft_delete(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)

    resposta = client.delete(f"/metas/{meta['id']}", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/metas/{meta['id']}", headers=headers)
    assert resposta_get.status_code == 200
    assert resposta_get.json()["ativo"] is False

    resposta_listagem = client.get("/metas", headers=headers)
    assert resposta_listagem.json() == []

    resposta_todas = client.get("/metas?apenas_ativas=false", headers=headers)
    assert len(resposta_todas.json()) == 1


def test_desativar_meta_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    meta_ana = _criar_meta(client, headers_ana)

    resposta = client.delete(f"/metas/{meta_ana['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


# --- excluir (DELETE /permanente = hard delete) -----------------------------

def test_excluir_meta_permanente_sem_aportes_apaga_o_cofrinho_de_verdade(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)
    conta_id_cofrinho = meta["conta_id"]

    resposta = client.delete(f"/metas/{meta['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    resposta_get = client.get(f"/metas/{meta['id']}", headers=headers)
    assert resposta_get.status_code == 404


def test_excluir_meta_permanente_com_transferencias_no_cofrinho_desoculta_e_desativa_a_conta(client):
    """O cofrinho com dinheiro de verdade (Transferencia associada) nunca é
    apagado ao excluir a Meta - é desocultado e desativado, para o usuário
    não perder acesso/visibilidade ao histórico e ao saldo (mesmo raciocínio
    já usado em ContaService.excluir para contas com vínculo)."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")
    conta_id_cofrinho = meta["conta_id"]

    aporte = _aportar(client, headers, conta["id"], meta, valor="250.00")
    assert aporte.status_code == 201, aporte.text

    resposta = client.delete(f"/metas/{meta['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    assert client.get(f"/metas/{meta['id']}", headers=headers).status_code == 404

    cofrinho = client.get(f"/contas/{conta_id_cofrinho}", headers=headers)
    assert cofrinho.status_code == 200
    assert cofrinho.json()["ativo"] is False

    # a transferência em si nunca é apagada - continua existindo
    transferencia = client.get(f"/transferencias/{aporte.json()['id']}", headers=headers)
    assert transferencia.status_code == 200


def test_excluir_meta_permanente_com_aporte_legado_desvincula_sem_apagar_a_transacao(client, db_session):
    """A Transacao legada (aporte pré-refatoramento) nunca é apagada junto -
    só perde o vínculo (meta_id volta a None), continua existindo
    normalmente em Transações, mesmo padrão de Fatura.excluir."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")
    usuario_id = _usuario_id_da_conta(db_session, conta["id"])

    aporte_legado = _inserir_transacao_legada_com_meta(db_session, usuario_id, conta["id"], meta["id"])

    resposta = client.delete(f"/metas/{meta['id']}/permanente", headers=headers)
    assert resposta.status_code == 204

    assert client.get(f"/metas/{meta['id']}", headers=headers).status_code == 404

    resposta_transacao = client.get(f"/transacoes/{aporte_legado.id}", headers=headers)
    assert resposta_transacao.status_code == 200
    assert resposta_transacao.json()["meta_id"] is None


def test_excluir_meta_permanente_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    meta_ana = _criar_meta(client, headers_ana)

    resposta = client.delete(f"/metas/{meta_ana['id']}/permanente", headers=headers_bruno)
    assert resposta.status_code == 404

    assert client.get(f"/metas/{meta_ana['id']}", headers=headers_ana).status_code == 200


def test_excluir_meta_permanente_libera_a_descricao_para_reuso_imediato(client):
    """Diferente do soft delete (que reativa em vez de duplicar), o hard
    delete remove a linha de verdade - uma meta nova com a mesma descrição
    é uma criação normal."""
    headers = _registrar_e_logar(client)
    _criar_meta(client, headers, descricao="Viagem", valor_alvo="10000.00")

    resposta_exclusao = client.delete(f"/metas/1/permanente", headers=headers)
    assert resposta_exclusao.status_code == 204

    nova = _criar_meta(client, headers, descricao="Viagem", valor_alvo="5000.00")
    assert nova["valor_alvo"] == "5000.00"

    todas = client.get("/metas?apenas_ativas=false", headers=headers).json()
    assert len(todas) == 1


# --- valor_acumulado/percentual: aporte/resgate = Transferencia -------------

def test_valor_acumulado_soma_aporte_via_transferencia(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")

    resposta = _aportar(client, headers, conta["id"], meta, valor="250.00")
    assert resposta.status_code == 201, resposta.text

    atualizada = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert atualizada["valor_acumulado"] == "250.00"
    assert atualizada["percentual"] == "25.00"


def test_valor_acumulado_subtrai_resgate_via_transferencia(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")

    _aportar(client, headers, conta["id"], meta, valor="500.00")
    resposta = _resgatar(client, headers, meta, conta["id"], valor="100.00")
    assert resposta.status_code == 201, resposta.text

    atualizada = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert atualizada["valor_acumulado"] == "400.00"


def test_valor_acumulado_ignora_transferencia_cancelada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")

    aporte = _aportar(client, headers, conta["id"], meta, valor="300.00").json()
    assert client.get(f"/metas/{meta['id']}", headers=headers).json()["valor_acumulado"] == "300.00"

    resposta = client.post(f"/transferencias/{aporte['id']}/cancelar", headers=headers)
    assert resposta.status_code == 200

    atualizada = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert atualizada["valor_acumulado"] == "0.00" or atualizada["valor_acumulado"] == "0"


def test_percentual_pode_passar_de_100_se_meta_superada(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")

    _aportar(client, headers, conta["id"], meta, valor="1500.00")

    atualizada = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert atualizada["percentual"] == "150.00"


def test_valor_acumulado_soma_historico_legado_e_cofrinho(client, db_session):
    """Núcleo do refatoramento: valor_acumulado = soma do histórico
    CONGELADO (Transacao.meta_id, dado antigo) + saldo do cofrinho
    (Transferencia nova) - ver docs/analise-arquitetural-metas-transferencias.md,
    seção 3."""
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="1000.00")
    usuario_id = _usuario_id_da_conta(db_session, conta["id"])

    _inserir_transacao_legada_com_meta(db_session, usuario_id, conta["id"], meta["id"], valor="250.00")
    _aportar(client, headers, conta["id"], meta, valor="100.00")

    atualizada = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert atualizada["valor_acumulado"] == "350.00"


# --- meta_id em POST/PATCH /transacoes: escrita removida, leitura mantida ---

def test_criar_transacao_ignora_meta_id_enviado_no_payload(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers)

    resposta = client.post(
        "/transacoes",
        json={
            "tipo": "RECEITA",
            "valor": "100.00",
            "data": "2026-07-15",
            "descricao": "Não é mais aporte",
            "status": "PAGO",
            "conta_id": conta["id"],
            "meta_id": meta["id"],
        },
        headers=headers,
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["meta_id"] is None


def test_atualizar_transacao_ignora_meta_id_enviado_no_payload(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers)

    transacao = client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "50.00",
            "data": "2026-07-15",
            "descricao": "Avulsa",
            "conta_id": conta["id"],
        },
        headers=headers,
    ).json()

    resposta = client.patch(
        f"/transacoes/{transacao['id']}", json={"meta_id": meta["id"]}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.json()["meta_id"] is None


def test_listar_transacoes_filtra_por_meta_id_no_historico_legado(client, db_session):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers)
    usuario_id = _usuario_id_da_conta(db_session, conta["id"])

    legada = _inserir_transacao_legada_com_meta(db_session, usuario_id, conta["id"], meta["id"])
    client.post(
        "/transacoes",
        json={
            "tipo": "DESPESA",
            "valor": "20.00",
            "data": "2026-07-15",
            "descricao": "Avulsa",
            "conta_id": conta["id"],
        },
        headers=headers,
    )

    resposta = client.get(f"/transacoes?meta_id={meta['id']}", headers=headers)
    assert resposta.status_code == 200
    resultado = resposta.json()
    assert len(resultado) == 1
    assert resultado[0]["id"] == legada.id


# --- Refinamento de Metas: frequencia_contribuicao / campos de planejamento -

def test_criar_meta_com_frequencia_contribuicao(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers, frequencia_contribuicao="SEMANAL")
    assert meta["frequencia_contribuicao"] == "SEMANAL"


def test_criar_meta_sem_frequencia_contribuicao(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)
    assert meta["frequencia_contribuicao"] is None
    assert meta["contribuicao_sugerida_por_periodo"] is None
    assert meta["concluida_em"] is None


def test_atualizar_frequencia_contribuicao(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers, frequencia_contribuicao="MENSAL")

    resposta = client.patch(
        f"/metas/{meta['id']}", json={"frequencia_contribuicao": "DIARIA"}, headers=headers
    )
    assert resposta.status_code == 200
    assert resposta.json()["frequencia_contribuicao"] == "DIARIA"


def test_criar_meta_com_frequencia_invalida_retorna_422(client):
    headers = _registrar_e_logar(client)
    resposta = client.post(
        "/metas", json=_payload_meta(frequencia_contribuicao="ANUAL"), headers=headers
    )
    assert resposta.status_code == 422


def test_contribuicao_sugerida_por_periodo_aparece_com_frequencia_e_prazo(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(
        client,
        headers,
        valor_alvo="12000.00",
        data_alvo="2026-07-18",  # sobrescrito abaixo por um prazo relativo
        frequencia_contribuicao="MENSAL",
    )
    # Recalcula com um prazo relativo a "hoje" para não depender da data
    # fixa do teste envelhecer - 300 dias, 10 períodos mensais de 30 dias.
    import datetime as _dt

    novo_prazo = (_dt.date.today() + _dt.timedelta(days=300)).isoformat()
    atualizada = client.patch(f"/metas/{meta['id']}", json={"data_alvo": novo_prazo}, headers=headers).json()
    assert atualizada["contribuicao_sugerida_por_periodo"] == "1200.00"


def test_concluida_em_e_persistida_ao_atingir_100_por_cento(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    meta = _criar_meta(client, headers, valor_alvo="500.00")

    assert client.get(f"/metas/{meta['id']}", headers=headers).json()["concluida_em"] is None

    _aportar(client, headers, conta["id"], meta, valor="500.00")

    concluida = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert concluida["percentual"] == "100.00"
    import datetime as _dt

    assert concluida["concluida_em"] == _dt.date.today().isoformat()

    # Consultar de novo não muda a data já gravada (idempotente).
    concluida_de_novo = client.get(f"/metas/{meta['id']}", headers=headers).json()
    assert concluida_de_novo["concluida_em"] == concluida["concluida_em"]


def test_situacao_planejamento_e_none_sem_data_alvo(client):
    headers = _registrar_e_logar(client)
    meta = _criar_meta(client, headers)
    assert meta["situacao_planejamento"] is None
    assert meta["valor_planejado_ate_hoje"] is None
    assert meta["diferenca_planejado_realizado"] is None
    assert meta["data_prevista_conclusao"] is None
