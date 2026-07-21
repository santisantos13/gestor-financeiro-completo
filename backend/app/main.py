"""Ponto de entrada da aplicação FastAPI.

Responsabilidade única: montar a aplicação, registrar routers e traduzir
exceções de domínio em respostas HTTP. Nenhuma regra de negócio deve viver
aqui (Single Responsibility Principle).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    AcessoNegadoError,
    BusinessRuleError,
    ConflictError,
    NaoAutenticadoError,
    NotFoundError,
)
from app.core.logging_config import configurar_logging
from app.api.routes.anexo import router as anexo_router
from app.api.routes.auth import router as auth_router
from app.api.routes.cartao import router as cartao_router
from app.api.routes.categoria import router as categoria_router
from app.api.routes.central_financeira import router as central_financeira_router
from app.api.routes.conta import router as conta_router
from app.api.routes.conta_recorrente import router as conta_recorrente_router
from app.api.routes.emprestimo import router as emprestimo_router
from app.api.routes.fatura import router as fatura_router
from app.api.routes.financiamento import router as financiamento_router
from app.api.routes.health import router as health_router
from app.api.routes.meta import router as meta_router
from app.api.routes.parcelamento import router as parcelamento_router
from app.api.routes.tag import router as tag_router
from app.api.routes.transacao import router as transacao_router
from app.api.routes.transferencia import router as transferencia_router

# configura o logging antes de qualquer outra coisa - se algo falhar logo
# na inicializacao, queremos que ja saia formatado corretamente.
configurar_logging()

# instancia unica do app - o titulo aparece na documentacao automatica (/docs)
app = FastAPI(title=settings.PROJECT_NAME)

# CORS: permite que o frontend (rodando em outra porta/origem, ex: localhost:5173)
# chame esta API do navegador. allow_origins vem de settings.CORS_ORIGINS para nao
# ficar hardcoded aqui - em producao, seria a URL real do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- traducao de excecoes de dominio para HTTP -----------------------------
# Os Services (e as dependencies de autenticacao) levantam as excecoes de
# app/core/exceptions.py sem saber nada de HTTP. E aqui, num unico lugar,
# que cada uma vira o status code correto. Isso e o que permite os Routers
# ficarem sem nenhum try/except: a excecao sobe e cai direto num desses
# handlers.
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(NaoAutenticadoError)
async def nao_autenticado_handler(request: Request, exc: NaoAutenticadoError) -> JSONResponse:
    # header WWW-Authenticate e o que o RFC 7235 espera numa resposta 401
    # pra deixar explicito que o esquema de autenticacao e Bearer.
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(AcessoNegadoError)
async def acesso_negado_handler(request: Request, exc: AcessoNegadoError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


# --- rede de seguranca contra excecao nao mapeada --------------------------
# Achado real durante a varredura de bugs de 2026-07: quando uma excecao NAO
# prevista sobe (ex.: OperationalError do SQLAlchemy por uma coluna que nao
# existe no banco real, um bug de codigo, etc.), ela nao cai em nenhum dos
# handlers acima - sobe crua ate o ServerErrorMiddleware que o proprio
# Starlette injeta por fora de QUALQUER middleware de usuario, inclusive o
# CORSMiddleware registrado acima. Resultado pratico: a resposta 500 sai
# SEM os headers de CORS, o navegador bloqueia a resposta como violacao de
# CORS, `fetch()` (ver frontend/src/api/httpClient.ts) lanca um erro de
# rede em vez de receber um 500 normal, e o usuario ve "Falha de conexao
# com o servidor" mesmo com o backend rodando perfeitamente - uma mensagem
# enganosa que apontava pro lugar errado (rede) quando o problema real era
# outro (nesse caso, uma migration nao aplicada no banco real).
#
# Registrar um handler para `Exception` resolve isso de forma definitiva e
# generica: o ExceptionMiddleware do Starlette fica DENTRO do
# CORSMiddleware, entao um handler registrado aqui intercepta a excecao
# ANTES dela escapar da camada de CORS, garantindo que toda resposta de
# erro - prevista ou nao - sempre carrega os headers corretos. Isso nao
# troca o tratamento de nenhuma regra de negocio (as excecoes de dominio
# continuam caindo nos handlers especificos acima, que sao mais
# especificos e tem prioridade); e so a rede de seguranca pro que sobrar.
@app.exception_handler(Exception)
async def excecao_nao_mapeada_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception(
        "Excecao nao mapeada em %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. Tente novamente em instantes."},
    )


# cada nova area do dominio ganha seu proprio router em app/api/routes/ e e
# registrada aqui com uma linha, sem tocar no resto do arquivo.
app.include_router(auth_router)
app.include_router(conta_router)
app.include_router(categoria_router)
app.include_router(tag_router)
app.include_router(cartao_router)
app.include_router(fatura_router)
app.include_router(transacao_router)
app.include_router(parcelamento_router)
app.include_router(transferencia_router)
app.include_router(conta_recorrente_router)
app.include_router(financiamento_router)
app.include_router(emprestimo_router)
app.include_router(meta_router)
app.include_router(anexo_router)
app.include_router(central_financeira_router)
app.include_router(health_router)
