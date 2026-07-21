# Revisão técnica — Camada de Autenticação

Revisão crítica da implementação entregue (registro, login, JWT access token, refresh
token com rotation, logout escopado/global, autorização por papel). Mesmo formato da
revisão anterior (`revisao-tecnica-backend.md`): pontos priorizados, sem filtro de
cortesia. **Status: fechada.** Os três problemas reais encontrados nas duas rodadas desta
revisão já foram corrigidos e cobertos por teste de regressão; não há pendência conhecida
que justifique mais uma rodada antes de começar os CRUDs de domínio.

## Resumo

A arquitetura pedida foi seguida com consistência: `security.py` é a única porta de
entrada para JWT/bcrypt, `AuthService` concentra toda decisão de negócio, `Router` não
tem lógica, e `get_current_user()` é de fato o único ponto de decodificação de token
usado pelo resto do sistema. As 10 exigências específicas (multi-sessão, logout
escopado/global, SECRET_KEY obrigatório, preparo para rotação de chave e rate limiting,
expiração centralizada, logging sem dados sensíveis) estão todas implementadas ou
deliberadamente preparadas, como pedido. 50 testes passam (14 unitários de
`AuthService`, 13 unitários de `security.py`, 13 de integração via `TestClient`, mais os
10 pré-existentes de outras camadas).

## Problemas encontrados e corrigidos

### 1. `/auth/refresh` não atualizava `ip`/`user_agent` da sessão — CORRIGIDO

`AuthService.renovar()` reaproveitava o contexto da sessão **antiga** em vez do da
requisição de refresh atual, e o Router de `/refresh` nem recebia `Request`. Toda sessão
renovada carregava para sempre o `ip`/`user_agent` do login original, mesmo vindo de rede
ou dispositivo diferentes nos refreshes seguintes — esvaziando o propósito desses campos
(reconhecimento de dispositivo, detecção de anomalia).

**Correção:** `renovar()` agora recebe `contexto: ContextoRequisicao` como parâmetro
explícito (mesmo padrão de `autenticar()`), e `routes/auth.py` monta esse contexto a
partir da requisição de `/refresh` atual antes de chamar o Service. Coberto por
`test_refresh_grava_o_user_agent_da_requisicao_de_refresh_e_nao_o_do_login` (integração,
verifica direto no banco) e `test_renovar_usa_o_contexto_da_requisicao_atual_nao_o_da_sessao_anterior`
(unitário).

### 2. `AuthService` era montado em dois lugares — CORRIGIDO

`deps.py` já definia `get_auth_service` (padrão de injeção do projeto), mas
`routes/auth.py` ignorava essa dependency e definia sua própria `_auth_service(db)` local,
montando o mesmo objeto na mão — duplicação que divergiria silenciosamente se um dia
`AuthService` ganhasse um terceiro Repository.

**Correção:** `_auth_service()` foi removido de `routes/auth.py`; todas as rotas agora
recebem `auth_service: AuthServiceDep` (alias de `Annotated[AuthService,
Depends(get_auth_service)]`). `get_auth_service` em `deps.py` é hoje a única função deste
projeto que instancia `AuthService` — confirmado por busca em todo `app/` (`grep -rn
"AuthService(" app/` retorna uma única ocorrência).

### 3. Canal de tempo em `autenticar()` para e-mail inexistente — CORRIGIDO

Achado nesta segunda rodada de revisão, não fazia parte da lista original. O código
tinha `if usuario is None or not security.verificar_senha(...)`: por *short-circuit* do
`or`, quando o e-mail não existe, `verificar_senha` (que roda bcrypt, custo 12 — algumas
dezenas a centenas de milissegundos) nunca era chamada. Login com senha errada (usuário
existe) sempre rodava bcrypt. Mensagem e log já eram idênticos nos dois casos (medida
anti-enumeração já presente e correta), mas o **tempo de resposta** não era — um atacante
capaz de medir latência conseguiria distinguir "e-mail cadastrado" de "e-mail não
cadastrado" só cronometrando a chamada a `/auth/login`, contornando a proteção de
mensagem/log.

**Correção:** `autenticar()` agora chama `security.verificar_senha()` incondicionalmente,
comparando contra o hash real do usuário quando ele existe, ou contra um hash bcrypt
"fantasma" fixo (`_HASH_FANTASMA`, de uma senha que não pertence a ninguém) quando não
existe — o custo de CPU do bcrypt é pago nos dois casos. Coberto por
`test_autenticar_com_email_inexistente_ainda_roda_verificacao_de_senha`, que substitui
`security.verificar_senha` por um espião e confirma que ele é chamado mesmo quando o
e-mail não existe.

## Pontos fortes confirmados nesta rodada

- **Revogação em lote não pisa em `revogado_em` já existente**: o `UPDATE` de
  `revogar_todas_do_usuario` filtra `revogado_em.is_(None)`, preservando o timestamp
  original de sessões já encerradas.
- **Logout é idempotente por design**, mas **logout de sessão alheia é rejeitado com
  403** — a diferença entre os dois casos é intencional: "token que não existe" e "token
  que existe mas é de outro usuário" são situações diferentes, e só a segunda é uma
  tentativa de acesso indevido que vale logar como tal.
- **A claim `papel` no JWT nunca é usada para autorizar** — `exigir_papel()` sempre
  confere `usuario.papel` recarregado do banco via `get_current_user()`, nunca a claim do
  token, então um usuário promovido/rebaixado é refletido imediatamente, sem esperar o
  access token antigo expirar.
- **Testes de integração cobrem os casos que mais frequentemente faltam** em
  implementações reais de refresh rotation e de contexto de sessão: reuso de token já
  rotacionado, e agora também o próprio bug corrigido nesta revisão (metadados da sessão
  presos ao login original).

## Não avaliado nesta revisão

Rate limiting e rotação de chave JWT foram propositalmente deixados como preparo
arquitetural (marcadores `# TODO(rate-limit)` e `_chave_assinatura()`), conforme pedido —
não são pendências esquecidas, são escopo definido para uma etapa futura.

## Conclusão

Com os três pontos acima corrigidos e testados, e sem novo problema de arquitetura,
segurança, duplicação ou dívida técnica identificado nesta segunda rodada, a camada de
autenticação está encerrada e pronta para servir de base para os CRUDs de domínio.
