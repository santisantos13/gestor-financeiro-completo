"""Testes de integração do CRUD de Transferência: TestClient + banco real
(SQLite em memória). Cobre isolamento entre usuários, validação estrutural
(origem != destino), posse/ativo das duas contas envolvidas, o efeito real
no saldo_atual das duas contas (via `GET /contas/{id}`, mesmo cálculo já
testado em test_conta_flow.py), cancelamento desfazendo o efeito no saldo
mas preservando o histórico (a transferência continua existindo e visível),
e ausência de `PATCH`/`DELETE` físico.
"""


def _registrar_e_logar(client, email="ana@example.com", senha="12345678"):
    resposta = client.post("/auth/registrar", json={"nome": "Ana", "email": email, "senha": senha})
    assert resposta.status_code == 201, resposta.text
    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200, resposta_login.text
    tokens = resposta_login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _criar_conta(client, headers, nome="Conta Corrente", saldo_inicial="1000.00"):
    resposta = client.post(
        "/contas", json={"nome": nome, "saldo_inicial": saldo_inicial}, headers=headers
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _criar_transferencia(client, headers, **overrides):
    payload = {
        "conta_origem_id": None,
        "conta_destino_id": None,
        "valor": "300.00",
        "data": "2026-07-14",
        "descricao": "Reserva de emergência",
    }
    payload.update(overrides)
    payload = {chave: valor for chave, valor in payload.items() if valor is not None}
    return client.post("/transferencias", json=payload, headers=headers)


def _saldo(client, headers, conta_id):
    return client.get(f"/contas/{conta_id}", headers=headers).json()["saldo_atual"]


# --- autenticação / estrutura -----------------------------------------------

def test_criar_transferencia_sem_autenticacao_retorna_401(client):
    resposta = client.post(
        "/transferencias",
        json={"conta_origem_id": 1, "conta_destino_id": 2, "valor": "10.00", "data": "2026-07-14"},
    )
    assert resposta.status_code == 401


def test_criar_transferencia_com_origem_igual_destino_retorna_422(client):
    headers = _registrar_e_logar(client)
    conta = _criar_conta(client, headers)
    resposta = _criar_transferencia(
        client, headers, conta_origem_id=conta["id"], conta_destino_id=conta["id"]
    )
    assert resposta.status_code == 422


def test_criar_transferencia_com_valor_zero_ou_negativo_retorna_422(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    resposta = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"], valor="0.00"
    )
    assert resposta.status_code == 422


# --- criar: posse cruzada -----------------------------------------------

def test_criar_transferencia_entre_contas_proprias_e_aceito(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem", saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, nome="Destino", saldo_inicial="0.00")

    resposta = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"], valor="300.00"
    )
    assert resposta.status_code == 201, resposta.text
    transferencia = resposta.json()
    assert transferencia["conta_origem_id"] == origem["id"]
    assert transferencia["conta_destino_id"] == destino["id"]
    assert transferencia["ativo"] is True


def test_criar_transferencia_com_conta_origem_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    origem_bruno = _criar_conta(client, headers_bruno, nome="Origem Bruno")
    destino_ana = _criar_conta(client, headers_ana, nome="Destino Ana")

    resposta = _criar_transferencia(
        client, headers_ana, conta_origem_id=origem_bruno["id"], conta_destino_id=destino_ana["id"]
    )
    assert resposta.status_code == 404


def test_criar_transferencia_com_conta_destino_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    origem_ana = _criar_conta(client, headers_ana, nome="Origem Ana")
    destino_bruno = _criar_conta(client, headers_bruno, nome="Destino Bruno")

    resposta = _criar_transferencia(
        client, headers_ana, conta_origem_id=origem_ana["id"], conta_destino_id=destino_bruno["id"]
    )
    assert resposta.status_code == 404


def test_criar_transferencia_com_conta_origem_inativa_retorna_422(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    client.delete(f"/contas/{origem['id']}", headers=headers)

    resposta = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    )
    assert resposta.status_code == 422


def test_criar_transferencia_com_conta_destino_inativa_retorna_422(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    client.delete(f"/contas/{destino['id']}", headers=headers)

    resposta = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    )
    assert resposta.status_code == 422


# --- efeito real no saldo (fonte única de verdade, sem Transacao) ----------

def test_criar_transferencia_move_saldo_entre_as_duas_contas(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem", saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, nome="Destino", saldo_inicial="0.00")

    _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"], valor="300.00"
    )

    assert _saldo(client, headers, origem["id"]) == "700.00"
    assert _saldo(client, headers, destino["id"]) == "300.00"


def test_criar_transferencia_nao_gera_nenhuma_transacao(client):
    # achado explicitamente reafirmado: Transferencia continua fora de
    # Transacao - nao deve aparecer em GET /transacoes.
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem", saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, nome="Destino", saldo_inicial="0.00")

    _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"], valor="300.00"
    )

    resposta_origem = client.get(f"/transacoes?conta_id={origem['id']}", headers=headers)
    resposta_destino = client.get(f"/transacoes?conta_id={destino['id']}", headers=headers)
    assert resposta_origem.json() == []
    assert resposta_destino.json() == []


# --- obter / listar -----------------------------------------------------

def test_obter_transferencia_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    origem = _criar_conta(client, headers_ana, nome="Origem")
    destino = _criar_conta(client, headers_ana, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers_ana, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()

    resposta = client.get(f"/transferencias/{transferencia['id']}", headers=headers_bruno)
    assert resposta.status_code == 404


def test_listar_transferencias_retorna_apenas_as_do_usuario(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    origem_ana = _criar_conta(client, headers_ana, nome="Origem Ana")
    destino_ana = _criar_conta(client, headers_ana, nome="Destino Ana")
    origem_bruno = _criar_conta(client, headers_bruno, nome="Origem Bruno")
    destino_bruno = _criar_conta(client, headers_bruno, nome="Destino Bruno")
    _criar_transferencia(
        client, headers_ana, conta_origem_id=origem_ana["id"], conta_destino_id=destino_ana["id"]
    )
    _criar_transferencia(
        client, headers_bruno, conta_origem_id=origem_bruno["id"], conta_destino_id=destino_bruno["id"]
    )

    resposta = client.get("/transferencias", headers=headers_ana)
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


# --- sem PATCH genérico e sem DELETE físico ---------------------------------

def test_transferencia_nao_tem_patch_generico(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()

    resposta = client.patch(
        f"/transferencias/{transferencia['id']}", json={"valor": "999.00"}, headers=headers
    )
    assert resposta.status_code == 405


def test_transferencia_nao_tem_delete_fisico(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()

    resposta = client.delete(f"/transferencias/{transferencia['id']}", headers=headers)
    assert resposta.status_code == 405


# --- cancelar: desfaz o efeito financeiro, preserva o histórico ------------

def test_cancelar_transferencia_desfaz_o_saldo_das_duas_contas(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem", saldo_inicial="1000.00")
    destino = _criar_conta(client, headers, nome="Destino", saldo_inicial="0.00")
    transferencia = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"], valor="300.00"
    ).json()

    assert _saldo(client, headers, origem["id"]) == "700.00"
    assert _saldo(client, headers, destino["id"]) == "300.00"

    resposta = client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    # saldo volta ao estado anterior a transferencia
    assert _saldo(client, headers, origem["id"]) == "1000.00"
    assert _saldo(client, headers, destino["id"]) == "0.00"


def test_cancelar_transferencia_preserva_o_historico(client):
    # a transferencia continua existindo e visivel via GET - so deixa de
    # afetar o saldo. Cancelamento nunca e um "apagar".
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()

    client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)

    resposta = client.get(f"/transferencias/{transferencia['id']}", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False


def test_transferencia_cancelada_some_da_listagem_padrao_mas_aparece_com_apenas_ativas_false(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()
    client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)

    resposta_padrao = client.get("/transferencias", headers=headers)
    assert resposta_padrao.json() == []

    resposta_todas = client.get("/transferencias?apenas_ativas=false", headers=headers)
    assert len(resposta_todas.json()) == 1


def test_cancelar_transferencia_ja_cancelada_retorna_422(client):
    headers = _registrar_e_logar(client)
    origem = _criar_conta(client, headers, nome="Origem")
    destino = _criar_conta(client, headers, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()
    client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)

    resposta = client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers)
    assert resposta.status_code == 422


def test_cancelar_transferencia_de_outro_usuario_retorna_404(client):
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    origem = _criar_conta(client, headers_ana, nome="Origem")
    destino = _criar_conta(client, headers_ana, nome="Destino")
    transferencia = _criar_transferencia(
        client, headers_ana, conta_origem_id=origem["id"], conta_destino_id=destino["id"]
    ).json()

    resposta = client.post(f"/transferencias/{transferencia['id']}/cancelar", headers=headers_bruno)
    assert resposta.status_code == 404


# --- atomicidade: falha na validação não deixa resíduo no banco ------------

def test_criar_transferencia_invalida_nao_deixa_nenhum_registro_orfao(client):
    # requisito explícito: "nunca permitir que apenas um dos lados seja
    # criado". Como a modelagem final não gera duas Transacoes (decisão
    # explícita do usuário - Transferencia continua fora de Transacao), o
    # risco de "meio criado" seria uma Transferencia inconsistente
    # persistida mesmo com a validação falhando. Confirma que uma
    # tentativa rejeitada (conta de outro usuário) não deixa nenhuma linha
    # no banco - a sessão do request nunca chega a commitar nada.
    headers_ana = _registrar_e_logar(client, email="ana@example.com")
    headers_bruno = _registrar_e_logar(client, email="bruno@example.com")
    origem_ana = _criar_conta(client, headers_ana, nome="Origem Ana")
    destino_bruno = _criar_conta(client, headers_bruno, nome="Destino Bruno")

    resposta = _criar_transferencia(
        client, headers_ana, conta_origem_id=origem_ana["id"], conta_destino_id=destino_bruno["id"]
    )
    assert resposta.status_code == 404

    resposta_listagem = client.get("/transferencias", headers=headers_ana)
    assert resposta_listagem.json() == []
    assert _saldo(client, headers_ana, origem_ana["id"]) == "1000.00"  # saldo_inicial padrão, intocado
