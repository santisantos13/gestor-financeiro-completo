"""Configuração de logging da aplicação.

Centralizado aqui para nao espalhar `logging.basicConfig` (ou configuracoes
divergentes) pelos modulos. Cada modulo que precisar logar so faz
`logger = logging.getLogger(__name__)` e usa - a configuracao de FORMATO e
NIVEL e feita uma unica vez, na inicializacao da aplicacao (app/main.py
chama `configurar_logging()` antes de qualquer coisa).

Regra de ouro seguida em todo log de autenticacao (app/services/auth_
service.py, app/api/deps.py): NUNCA logar senha, token completo (nem
access nem refresh/opaco) ou qualquer segredo. Identificadores seguros de
logar: usuario_id, email (nao e segredo), jti (id do token, nao o token em
si), ip, user_agent.
"""
import logging

from app.core.config import settings


def configurar_logging() -> None:
    """Configura o logging raiz da aplicação. Chamada uma única vez, no
    startup (ver app/main.py).
    """
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    )
