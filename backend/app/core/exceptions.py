"""Exceções de domínio.

Services levantam essas exceções quando uma regra de negócio e violada -
NUNCA um HTTPException do FastAPI. Isso mantem a camada de Service livre de
qualquer conhecimento de HTTP: uma regra de negocio ("nao pode transferir
para a mesma conta", "conta nao encontrada"...) nao deveria saber que esta
sendo servida via REST - amanha poderia ser chamada por um worker, um CLI,
outro Service, etc, sem nenhuma mudanca.

Um exception handler global (registrado em app/main.py) traduz cada uma
dessas excecoes para o status HTTP correspondente. Assim, o Router nunca
precisa de try/except: ele so chama o Service e deixa a excecao subir.
"""


class DomainError(Exception):
    """Classe-base de toda exceção de domínio do sistema."""


class NotFoundError(DomainError):
    """A entidade solicitada não existe (Router traduz para HTTP 404)."""


class BusinessRuleError(DomainError):
    """Uma regra de negócio foi violada, ex: valor negativo, conta inativa
    usada numa transação (Router traduz para HTTP 422)."""


class ConflictError(DomainError):
    """A operação conflita com o estado atual dos dados, ex: e-mail
    duplicado, fatura já paga sendo paga de novo (Router traduz para HTTP 409)."""


class NaoAutenticadoError(DomainError):
    """Credenciais ausentes, invalidas, ou token expirado/revogado (Router
    traduz para HTTP 401). Usada tanto por login invalido quanto por
    get_current_user() quando o access token nao passa na validacao."""


class AcessoNegadoError(DomainError):
    """O usuario esta autenticado, mas nao tem permissao para a acao (ex:
    papel insuficiente, ou tentando encerrar a sessao de outro usuario).
    Router traduz para HTTP 403 - diferente de NaoAutenticadoError (401),
    que significa "nao sei quem voce e"."""
