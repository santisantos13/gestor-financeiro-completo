"""Service de Transferencia.

Regra de negócio central: mover dinheiro entre duas Contas do MESMO
usuário, sem nunca passar por Transacao - decisão arquitetural
deliberada e reafirmada explicitamente nesta etapa (ver docstring do
model `Transferencia` e `docs/revisao-tecnica-transferencia.md`): uma
transferência não é receita nem despesa, e gerar Transacao para
representá-la inflaria relatórios de gasto/receita, categorias e metas
com dinheiro que nunca saiu do patrimônio do usuário.

Como não há duas Transacoes para criar, não existe o risco de "só um lado
foi criado" que existiria se essa fosse a estratégia escolhida - um único
INSERT (`TransferenciaRepository.create`) é, por construção, atômico
dentro da Unit of Work do request (`app/db/session.py`): ou a linha inteira
é confirmada, ou nada é (rollback em qualquer exceção). Nenhum tratamento
especial de atomicidade é necessário aqui além do que a sessão do request
já garante para qualquer Service do projeto.
"""
from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Transferencia
from app.repositories.conta_repository import ContaRepository
from app.repositories.transferencia_repository import TransferenciaRepository
from app.schemas.transferencia import TransferenciaCreate


class TransferenciaService:
    def __init__(self, transferencia_repo: TransferenciaRepository, conta_repo: ContaRepository) -> None:
        self.transferencia_repo = transferencia_repo
        self.conta_repo = conta_repo

    def criar(self, dados: TransferenciaCreate, usuario_id: int) -> Transferencia:
        self._validar_estrutura(dados.conta_origem_id, dados.conta_destino_id)
        self._validar_conta_do_usuario_ativa(dados.conta_origem_id, usuario_id)
        self._validar_conta_do_usuario_ativa(dados.conta_destino_id, usuario_id)

        transferencia = Transferencia(
            usuario_id=usuario_id,
            conta_origem_id=dados.conta_origem_id,
            conta_destino_id=dados.conta_destino_id,
            valor=dados.valor,
            data=dados.data,
            descricao=dados.descricao,
            ativo=True,
        )
        return self.transferencia_repo.create(transferencia)

    def obter(self, transferencia_id: int, usuario_id: int) -> Transferencia:
        return self._buscar_da_propriedade_do_usuario(transferencia_id, usuario_id)

    def listar(
        self,
        usuario_id: int,
        *,
        apenas_ativas: bool = True,
        conta_id: int | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Transferencia]:
        return list(
            self.transferencia_repo.listar_do_usuario(
                usuario_id,
                apenas_ativas=apenas_ativas,
                conta_id=conta_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                skip=skip,
                limit=limit,
            )
        )

    def excluir(self, transferencia_id: int, usuario_id: int) -> None:
        """Exclusão DEFINITIVA (hard delete) - diferente de `cancelar()`
        acima (soft delete, preserva a linha): apaga a linha de verdade.
        Não existia nenhum caminho de hard delete para Transferencia até
        agora - método novo, criado especificamente para a cascata de
        exclusão de Conta (`ContaService.excluir(..., apagar_vinculos=True)`,
        ver docs/analise-arquitetural-exclusao-conta-com-historico.md):
        `conta_origem_id`/`conta_destino_id` são NOT NULL, então não existe
        "desvincular" uma Transferencia de uma Conta que está sendo apagada
        - só apagar a linha inteira. Sempre permitida (nenhuma regra de
        negócio bloqueia excluir uma Transferencia, ativa ou já cancelada)."""
        transferencia = self._buscar_da_propriedade_do_usuario(transferencia_id, usuario_id)
        self.transferencia_repo.delete(transferencia)

    def cancelar(self, transferencia_id: int, usuario_id: int) -> Transferencia:
        """Desfaz o efeito financeiro preservando o histórico: a linha
        nunca é apagada (mesmo padrão de soft delete de Conta/Categoria/
        Tag/Cartão) - só marca `ativo=False`, o que já é o suficiente para
        `ContaRepository.somar_transferencias` parar de contá-la no saldo
        das duas contas envolvidas na próxima leitura. Nenhum ajuste
        manual de saldo é necessário porque saldo nunca é armazenado,
        sempre recalculado a partir das transferências ATIVAS (ver
        `ContaService._com_saldo`)."""
        transferencia = self._buscar_da_propriedade_do_usuario(transferencia_id, usuario_id)
        if not transferencia.ativo:
            raise BusinessRuleError("Esta transferência já está cancelada.")
        transferencia.ativo = False
        return self.transferencia_repo.update(transferencia)

    # --- validações estruturais (mesma família do CheckConstraint do banco) ---

    @staticmethod
    def _validar_estrutura(conta_origem_id: int, conta_destino_id: int) -> None:
        """Mesma família do `ck_transferencia_contas_distintas` do banco -
        validado aqui antes para devolver um erro de negócio claro em vez
        de um IntegrityError cru, mesmo raciocínio já usado em
        `TransacaoService._validar_estrutura`/`ParcelamentoService._validar_estrutura`."""
        if conta_origem_id == conta_destino_id:
            raise BusinessRuleError("A conta de origem e a conta de destino não podem ser a mesma.")

    # --- posse cruzada -------------------------------------------------------

    def _validar_conta_do_usuario_ativa(self, conta_id: int, usuario_id: int) -> None:
        """Garante que a conta existe, pertence ao MESMO usuário da
        transferência e está ativa - aplicada duas vezes (origem e
        destino). Mesmo tratamento (404) para "não existe" e "é de outro
        usuário" - mesmo raciocínio anti-enumeração já usado em
        `CartaoService._validar_conta_do_usuario`/
        `TransacaoService._validar_conta_ativa`."""
        conta = self.conta_repo.get(conta_id)
        if conta is None or conta.usuario_id != usuario_id:
            raise NotFoundError("Conta não encontrada.")
        if not conta.ativo:
            raise BusinessRuleError("Não é possível transferir de/para uma conta inativa.")

    def _buscar_da_propriedade_do_usuario(self, transferencia_id: int, usuario_id: int) -> Transferencia:
        transferencia = self.transferencia_repo.get(transferencia_id)
        if transferencia is None or transferencia.usuario_id != usuario_id:
            raise NotFoundError("Transferência não encontrada.")
        return transferencia
