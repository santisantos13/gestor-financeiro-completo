"""Camada de Schemas (Pydantic).

Responsabilidade única: validar o formato dos dados que entram e saem pela
API HTTP - nada além disso. Um schema define "o que e um payload valido de
criar uma Conta" (ContaCreate), "o que volta pro cliente quando pedimos uma
Conta" (ContaRead), etc.

Schemas NÃO são os models do SQLAlchemy (app/models/): um Model descreve
uma TABELA do banco; um Schema descreve um FORMATO de entrada/saida da API.
Eles costumam ter campos parecidos, mas por propósitos diferentes - por
exemplo, `ContaCreate` não tem `id` (quem cria não escolhe o id) nem
`usuario_id` (vem do usuário autenticado, não do corpo da requisição),
enquanto o Model `Conta` tem os dois.

Convenção de nomes que será usada quando os schemas de cada entidade forem
criados (etapa dos CRUDs):
  - `<Entidade>Create` - payload de entrada para criar
  - `<Entidade>Update` - payload de entrada para atualizar (campos opcionais)
  - `<Entidade>Read`   - payload de saída (o que a API devolve)

Todos herdam de OrmBaseModel (ver base.py) para poderem ser construídos
diretamente a partir de um objeto do SQLAlchemy.
"""
