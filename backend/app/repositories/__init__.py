"""Camada de Repository.

Responsabilidade única: traduzir operações de persistência (buscar, listar,
salvar, remover) em queries ao banco. Um Repository NUNCA contém regra de
negócio - ele sabe "como" buscar/salvar um dado, nunca "quando" ou "se
deveria" (isso é responsabilidade do Service, uma camada acima).

Cada entidade do domínio ganha seu próprio Repository (ex: ContaRepository,
TransacaoRepository) herdando de SQLAlchemyRepository (ver base.py) e
adicionando métodos de busca específicos daquela entidade quando precisar
(ex: "listar transações de uma conta num período"). Isso será feito na
etapa de implementação dos CRUDs - por enquanto só a base genérica existe.
"""
