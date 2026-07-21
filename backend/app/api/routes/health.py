"""Endpoint de healthcheck.

Único endpoint desta etapa: serve apenas para confirmar que a API está no ar.
Endpoints de domínio (contas, transações, etc.) virão em etapas seguintes.
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
