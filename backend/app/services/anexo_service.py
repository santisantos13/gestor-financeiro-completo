"""Service de Anexo.

Regra de negócio central desta entidade: posse é SEMPRE transitiva via
Transacao - Anexo não tem `usuario_id` próprio (decisão explícita do
usuário, ver docs/analise-arquitetural-anexo.md). Toda validação de posse
reaproveita `TransacaoService.obter()` (que já levanta `NotFoundError`
uniforme tanto para "transação não existe" quanto para "transação é de
outro usuário" - mesmo padrão anti-BOLA de sempre), nunca reimplementa essa
checagem por conta própria.

AnexoService NUNCA cria/edita/exclui uma Transacao - só a lê, através de
TransacaoService.obter(), para confirmar posse. É um terceiro padrão de
composição com TransacaoService neste projeto: diferente de
Parcelamento/ContaRecorrente/Financiamento/Empréstimo (que ESCREVEM
Transacao através dele) e diferente de MetaService (que nunca fala com
TransacaoService, só agrega via seu próprio Repository).
"""
from app.core.exceptions import NotFoundError
from app.models import Anexo
from app.repositories.anexo_repository import AnexoRepository
from app.schemas.anexo import AnexoCreate
from app.services.transacao_service import TransacaoService


class AnexoService:
    def __init__(self, anexo_repo: AnexoRepository, transacao_service: TransacaoService) -> None:
        self.anexo_repo = anexo_repo
        self.transacao_service = transacao_service

    def criar(self, dados: AnexoCreate, usuario_id: int) -> Anexo:
        """Cria o anexo, vinculado a uma Transacao que precisa existir e
        pertencer ao usuário autenticado - nunca é permitido anexar um
        arquivo a uma transação de outro usuário."""
        self.transacao_service.obter(dados.transacao_id, usuario_id)

        anexo = Anexo(**dados.model_dump(), ativo=True)
        return self.anexo_repo.create(anexo)

    def obter(self, anexo_id: int, usuario_id: int) -> Anexo:
        anexo = self._buscar_da_propriedade_do_usuario(anexo_id, usuario_id)
        return anexo

    def listar_por_transacao(
        self, transacao_id: int, usuario_id: int, *, apenas_ativos: bool = True, skip: int = 0, limit: int = 100
    ) -> list[Anexo]:
        # Confirma posse da transação ANTES de listar - sem isso, um
        # usuário poderia descobrir se um transacao_id de outro usuário
        # existe pela diferença entre "lista vazia" e "404" (mesmo
        # raciocínio anti-enumeração de sempre).
        self.transacao_service.obter(transacao_id, usuario_id)
        return list(
            self.anexo_repo.listar_por_transacao(
                transacao_id, apenas_ativos=apenas_ativos, skip=skip, limit=limit
            )
        )

    def desativar(self, anexo_id: int, usuario_id: int) -> None:
        """"Exclui" um anexo sem apagar a linha - só marca ativo=False,
        mesmo padrão de soft delete já usado no resto do domínio. O arquivo
        físico (fora do escopo desta etapa) não é tocado - só o metadado
        para de aparecer nas listagens."""
        anexo = self._buscar_da_propriedade_do_usuario(anexo_id, usuario_id)
        anexo.ativo = False
        self.anexo_repo.update(anexo)

    def _buscar_da_propriedade_do_usuario(self, anexo_id: int, usuario_id: int) -> Anexo:
        """Busca o Anexo e confirma posse TRANSITIVA: o anexo precisa
        existir E a Transacao que ele referencia precisa pertencer ao
        usuário. Mesmo tratamento (404) para "anexo não existe" e "a
        transação dele é de outro usuário" - mesmo raciocínio
        anti-enumeração (BOLA) de sempre."""
        anexo = self.anexo_repo.get(anexo_id)
        if anexo is None:
            raise NotFoundError("Anexo não encontrado.")
        # Reaproveita TransacaoService.obter() para a checagem de posse -
        # nunca duplica "transacao.usuario_id == usuario_id" aqui.
        self.transacao_service.obter(anexo.transacao_id, usuario_id)
        return anexo
