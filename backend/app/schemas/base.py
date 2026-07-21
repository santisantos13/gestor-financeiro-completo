"""Base compartilhada entre todos os schemas Pydantic do projeto.
"""
from pydantic import BaseModel, ConfigDict


class OrmBaseModel(BaseModel):
    """Todo schema de LEITURA (`<Entidade>Read`) deve herdar desta classe.

    `from_attributes=True` permite fazer `ContaRead.model_validate(conta)`
    passando direto um objeto Model do SQLAlchemy (que tem atributos, não
    um dict) - sem isso, o Pydantic exigiria um dicionário.
    """

    model_config = ConfigDict(from_attributes=True)
