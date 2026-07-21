"""Camada de Service.

Responsabilidade única: regra de negócio. Tudo que é "logica da aplicacao"
mora aqui - validacoes que dependem de estado (ex: "essa conta pertence a
esse usuario?"), calculos (ex: saldo de uma conta, progresso de uma meta),
orquestracao de mais de um Repository numa unica operacao (ex: Transferencia
mexendo em duas Contas), e decisao de QUANDO levantar uma excecao de
dominio (NotFoundError, BusinessRuleError, ConflictError - ver
app/core/exceptions.py).

Um Service:
  - recebe um ou mais Repository (ou IRepository) injetados no construtor;
  - NUNCA importa nada de FastAPI (Request, HTTPException, Depends...) -
    ele não sabe que está sendo chamado via HTTP, isso é responsabilidade
    do Router;
  - NUNCA monta uma query SQL diretamente - isso é responsabilidade do
    Repository. Se um Service precisa de uma busca nova, o metodo entra
    no Repository, nao aqui.

Diferente de Repository, NÃO existe uma classe `BaseService` genérica.
Decisão deliberada: regra de negócio não se repete de forma genérica entre
entidades do jeito que get/list/create/delete se repetem - um
TransferenciaService depende de duas Contas e de regras que não existem em
nenhuma outra entidade, por exemplo. Forçar todo Service a herdar de uma
base comum obrigaria essa base a saber sobre casos que não são dela
(violaria o Interface Segregation Principle). Em vez disso, cada Service
declara explicitamente do que precisa no `__init__` (constructor injection):

    class ContaService:
        def __init__(self, conta_repo: IRepository[Conta]) -> None:
            self.conta_repo = conta_repo

        def criar_conta(self, dados: ContaCreate, usuario_id: int) -> Conta:
            conta = Conta(**dados.model_dump(), usuario_id=usuario_id)
            return self.conta_repo.create(conta)

Os Services concretos (ContaService, TransacaoService, etc.) serão criados
na etapa de implementação dos CRUDs.
"""
