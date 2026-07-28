"""Rate limiting de endpoints sensíveis a força bruta (`/auth/login`,
`/auth/refresh`) - ver docs/analise-arquitetural-rate-limiting.md.

Instância única de `Limiter` (biblioteca `slowapi`, sobre `limits`),
importada tanto por `app/main.py` (registro do handler de exceção +
`app.state.limiter`) quanto por `app/api/routes/auth.py` (decorator
`@limiter.limit(...)` nas duas rotas). Precisa ser um módulo próprio (em
vez de instanciada direto em `main.py`) porque o router de auth também
precisa importá-la, e `app/api/routes/auth.py` não pode importar de
`app/main.py` sem criar um ciclo (main.py já importa o router).

Chave de limite = endereço IP do cliente (`get_remote_address`, padrão do
slowapi) - NÃO por e-mail/usuário. Limitar por IP é a primeira linha de
defesa padrão contra força bruta de credenciais a partir de uma única
origem; limitar por e-mail exigiria ler o corpo da requisição dentro da
`key_func` (que só recebe `Request`, não o payload já validado pelo
Pydantic) - viável, mas mais frágil (ordem de leitura do body) e um
problema diferente (ataque distribuído contra UMA conta, de vários IPs)
que não foi pedido - YAGNI.

Armazenamento em memória do próprio processo (default do `Limiter`, sem
`storage_uri`): suficiente porque o backend roda como uma ÚNICA instância
no Render free tier (ver docs/analise-arquitetural-deploy-prealfa.md) -
um storage compartilhado (Redis) só faria diferença com múltiplas
instâncias atrás de um load balancer, o que não é o caso aqui. Se o app
algum dia escalar horizontalmente, trocar para `storage_uri="redis://..."`
é a única mudança necessária neste arquivo.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
