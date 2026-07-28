# Análise arquitetural — rate limiting de /auth/login e /auth/refresh

## 0. Pedido do usuário

Fechar o item "Segurança" do roadmap (dashboard de acompanhamento) - o backlog já apontava a
lacuna concreta: `/auth/login` e `/auth/refresh` não tinham nenhum limite de tentativas, deixados
como `TODO(rate-limit)` explícito em `app/api/routes/auth.py` desde a etapa de autenticação
original. Um invasor podia testar senhas (força bruta contra `/auth/login`) ou refresh tokens
vazados (`/auth/refresh`) em loop, sem nenhuma fricção.

## 1. Escolha da biblioteca: `slowapi`, armazenamento em memória

`slowapi` (camada fina sobre `limits`) foi escolhida em vez de escrever um limitador do zero
porque é a biblioteca de referência do próprio ecossistema FastAPI para este problema - mesma
API de decorator (`@limiter.limit("N/minute")`) que Flask-Limiter usa, bem documentada, sem
dependência nativa (compila só Python puro).

**Por que armazenamento em memória (default, sem Redis)**: o backend roda como uma ÚNICA
instância no Render free tier (`render.yaml` - `plan: free`, sem `numInstances`/autoscaling -
ver docs/analise-arquitetural-deploy-prealfa.md). Um storage compartilhado (Redis) só faria
diferença com múltiplas instâncias atrás de um load balancer, dividindo o mesmo contador -
não é o caso aqui, e adicionar Redis só para isso seria uma dependência paga (ou mais um serviço
gratuito de terceiro para gerenciar) sem nenhum ganho real. Custo aceito, documentado em
`app/core/rate_limit.py`: se o app algum dia escalar horizontalmente, o contador por instância
deixaria de ser exato (cada instância teria seu próprio balde) - o único ajuste necessário
nesse dia é trocar `Limiter(key_func=...)` por `Limiter(key_func=..., storage_uri="redis://...")`,
sem tocar nas rotas.

## 2. Chave do limite: IP do cliente, não e-mail

`get_remote_address` (utilitário pronto do `slowapi`) usa `request.client.host`. Considerada e
descartada a alternativa de limitar por e-mail (`chave=dados.email`, como o `TODO` original
sugeria): a `key_func` do `slowapi` só recebe o `Request`, não o payload já validado pelo
Pydantic - leria o corpo da requisição uma segunda vez, correndo risco de conflitar com a ordem
em que o FastAPI já consumiu esse mesmo corpo para popular `dados: LoginRequest`. Limitar por
e-mail também resolveria um problema diferente do pedido (um único e-mail sendo atacado a partir
de VÁRIOS IPs) - fora de escopo (YAGNI). Por IP é a primeira linha de defesa padrão contra força
bruta de credenciais a partir de uma única origem, e o `Request` já era um parâmetro obrigatório
de ambas as rotas (contexto de sessão) - nenhuma mudança de assinatura foi necessária.

## 3. Limites escolhidos

- `/auth/login`: **10/minuto** por IP.
- `/auth/refresh`: **20/minuto** por IP - mais permissivo porque uso legítimo é mais frequente:
  cada expiração de access token (a cada `ACCESS_TOKEN_EXPIRE_MINUTES` = 15min) dispara um
  refresh automático por dispositivo/aba aberta; várias abas do mesmo usuário atrás do mesmo IP
  (ex: rede doméstica/corporativa com NAT) somam tentativas legítimas mais rápido que em login.

Ambos generosos o suficiente para não incomodar um usuário real errando a senha algumas vezes ou
com várias abas abertas, mas baixos o bastante para tornar um ataque de força bruta clássico
(milhares de tentativas) impraticável.

## 4. Onde a decisão foi tomada

`app/core/rate_limit.py` (novo módulo) - só a instância de `Limiter`, para poder ser importada
tanto por `app/main.py` (registro do handler de exceção + `app.state.limiter`) quanto por
`app/api/routes/auth.py` (os dois decorators) sem criar um ciclo de import.

`app/main.py` ganhou:
- `app.state.limiter = limiter` (exigência do `slowapi` - é aqui que ele procura a instância).
- `@app.exception_handler(RateLimitExceeded)` PRÓPRIO (em vez do `_rate_limit_exceeded_handler`
  padrão do `slowapi`) - só para manter o mesmo envelope `{"detail": "..."}` que todo outro
  handler de exceção deste arquivo já usa (o padrão do `slowapi` devolve `{"error": "..."}`, uma
  segunda convenção que o frontend, `ApiError.detail` em `httpClient.ts`, não entenderia sem
  tratamento especial). Retorna 429.

`app/api/routes/auth.py`: `@limiter.limit("10/minute")`/`@limiter.limit("20/minute")` nas duas
rotas, substituindo os comentários `TODO(rate-limit)` que já esboçavam exatamente essa forma.
Nenhuma outra rota do projeto precisa disso hoje - `/auth/registrar` não é um alvo de força
bruta do mesmo jeito (criar conta em loop não vaza segredo de outra pessoa) e não foi pedido.

## 5. Problema encontrado durante a implementação: Render sempre fica na frente como proxy

Achado importante ao revisar como o IP do cliente chega até o `Limiter`: o Render (como todo
PaaS) termina a conexão HTTPS e repassa a requisição para o `uvicorn` através de um proxy reverso
- sem nenhuma configuração adicional, `request.client.host` (o que `get_remote_address` lê) seria
sempre o IP INTERNO do proxy do Render, nunca o IP real de quem está usando o site. Isso
inverteria completamente o propósito do rate limiting: TODOS os usuários apareceriam como uma
única origem para o `Limiter`, e um usuário legítimo errando a senha algumas vezes bloquearia
`/auth/login` para QUALQUER outra pessoa usando o app ao mesmo tempo.

**Corrigido em `render.yaml`**: o `startCommand` do backend ganhou `--proxy-headers
--forwarded-allow-ips='*'` - flags nativas do `uvicorn` que fazem ele ler o cabeçalho
`X-Forwarded-For` (que o proxy do Render já preenche corretamente) e expor o IP real do visitante
em `request.client.host`. `forwarded-allow-ips='*'` é seguro neste caso porque o Render controla o
único caminho de entrada (o plano free não expõe a instância diretamente à internet, só através
do proxy do próprio Render) - confiar em QUALQUER proxy à frente do app só seria um risco real se
o tráfego pudesse chegar por outra rota além dele.

Esse ajuste não é testável via `TestClient` (que chama o `app` FastAPI diretamente, sem passar
pelo processo `uvicorn` nem pelas flags de linha de comando) - validado por leitura/raciocínio
sobre a arquitetura de deploy, não por teste automatizado.

## 6. Testes e o cuidado de isolamento entre eles

`Limiter` guarda contagem em memória do PRÓPRIO PROCESSO - e `app` (importado de `app.main`) é o
MESMO objeto Python reusado por toda a suíte de testes de integração (não é recriado por teste).
Sem cuidado extra, os contadores se acumulariam entre testes: o `TestClient` sempre reporta o
mesmo IP (`"testclient"`), então um teste no meio da suíte poderia ser bloqueado por logins de
testes ANTERIORES, não pelos seus próprios - um falso positivo intermitente e dependente da ordem
de execução dos testes.

Corrigido em `tests/integration/conftest.py`: a fixture `client` (usada por TODOS os testes de
integração) chama `limiter.reset()` antes de cada teste, garantindo que cada teste começa com o
balde de tentativas vazio, independente do que rodou antes.

## 7. Validação

3 testes de integração novos em `test_auth_flow.py`:
- `test_login_bloqueia_apos_exceder_o_limite_por_minuto` - 10 tentativas passam (mesmo com senha
  errada, o limite conta a REQUISIÇÃO, não só falha de autenticação), a 11ª retorna 429; mesmo com
  a senha CERTA depois de estourado, continua 429 (o limite é por IP, não por credencial).
- `test_refresh_bloqueia_apos_exceder_o_limite_por_minuto` - mesmo padrão, limite de 20.
- (implícito, via toda a suíte) nenhum teste existente que faz login/refresh múltiplas vezes
  quebrou - confirma que `limiter.reset()` por teste funciona e que os limites escolhidos (10/20)
  têm folga suficiente para o maior número de logins/refreshes feitos DENTRO de um único teste
  hoje (no máximo 3, em `test_trocar_senha_com_senha_atual_correta`).

Suíte completa (1157 testes originais + 4 novos: 3 de escopo de exclusão de parcela do trabalho
anterior desta mesma sessão + estes) revalidada em lotes (limite de tempo do sandbox não permite
rodar tudo numa única chamada) - todos passando.
