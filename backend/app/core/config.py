"""Configurações centralizadas da aplicação.

Usa pydantic-settings para carregar variáveis de ambiente de forma tipada,
evitando `os.getenv` espalhado pelo código (evita duplicação e erros).

Todo tempo de expiração de token, algoritmo e nível de log vive AQUI, nunca
espalhado pelo código - qualquer lugar que precisar de um desses valores
importa `settings`, nunca declara o próprio número/string.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Finanças Pessoais API"
    DATABASE_URL: str = "sqlite:///./financas.db"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # --- Autenticação / JWT ---
    # SECRET_KEY NAO tem valor padrao de proposito: pydantic-settings levanta
    # erro de validacao (a aplicacao nem sobe) se a variavel de ambiente nao
    # estiver definida. Isso e deliberado - nunca deve existir um segredo
    # hardcoded ou um default inseguro "so pra funcionar" em producao.
    SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    # JWT_KEY_ID identifica QUAL chave assinou o token (claim "kid" no
    # header do JWT). Hoje so existe uma chave (SECRET_KEY) e um id fixo,
    # mas ja preparar esse campo e o que torna simples, no futuro, ter mais
    # de uma chave valida ao mesmo tempo (rotacao: aceitar tokens antigos
    # assinados com a chave anterior enquanto tokens novos usam a nova) sem
    # redesenhar nada - so passar a resolver o "kid" para uma chave
    # especifica em vez de sempre usar SECRET_KEY. Ver app/core/security.py.
    JWT_KEY_ID: str = "v1"

    # access token: vida curta, usado a cada requisicao autenticada.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # refresh token: vida longa, usado só para obter um novo access token.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
