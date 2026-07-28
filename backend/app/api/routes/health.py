"""Endpoint de healthcheck.

Usado por dois consumidores diferentes: (1) `render.yaml` (`healthCheckPath`),
para o Render decidir se a instância está saudável; (2) um ping externo
periódico (UptimeRobot/cron-job.org, grátis) configurado pelo usuário para
evitar dois problemas de infraestrutura gratuita descobertos em produção
(2026-07-26, ver docs/analise-arquitetural-deploy-prealfa.md, seção
"Lentidão em produção"): o plano free do Render "adormece" o serviço após 15
minutos sem tráfego (próxima requisição paga um cold start de ~30-60s), e o
Postgres gratuito do Supabase PAUSA o projeto inteiro após 7 dias sem
nenhuma atividade (não acorda sozinho - precisa reativação manual no painel).

Por isso este endpoint faz um `SELECT 1` real no banco: um ping "vazio" (sem
tocar o banco) resolveria só o problema do Render, deixando o Supabase
pausar de qualquer forma. Consulta trivial (ver app/db/session.py:get_db),
custo desprezível mesmo chamada a cada poucos minutos.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
