"""Base declarativa do SQLAlchemy.

Todos os modelos (a serem criados em etapas futuras) herdarão desta Base.
Mantida separada de session.py para evitar import circular quando os models
precisarem ser registrados aqui.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
