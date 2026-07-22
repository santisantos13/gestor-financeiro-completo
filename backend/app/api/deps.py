"""Funções de dependency injection (usadas com `Depends()` nos Routers).

Centralizado aqui em vez de espalhado por cada router para: 1) todo router
importar da mesma fonte (consistência), 2) trocar como a sessão de banco é
obtida em um único ponto, se um dia precisar.

`DbSession` é um atalho de tipo: em vez de escrever
`db: Session = Depends(get_db)` em toda função de rota, basta
`db: DbSession`. O mesmo padrão vale para `CurrentUser` abaixo. Repository/
Service de cada entidade de domínio seguem o mesmo padrão já usado por
`get_auth_service`/`get_conta_service`/`get_categoria_service`/`get_tag_service`/
`get_cartao_service`/`get_fatura_service`/`get_transacao_service`/
`get_parcelamento_service`/`get_transferencia_service`/
`get_conta_recorrente_service`/`get_financiamento_service`/
`get_emprestimo_service`/`get_meta_service`/`get_anexo_service`.
"""
import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AcessoNegadoError, NaoAutenticadoError
from app.core.security import TokenInvalidoError, decodificar_access_token
from app.db.session import get_db
from app.models import Usuario
from app.models.enums import TipoPapel
from app.repositories.anexo_repository import AnexoRepository
from app.repositories.cartao_repository import CartaoRepository
from app.repositories.categoria_repository import CategoriaRepository
from app.repositories.conta_recorrente_repository import ContaRecorrenteRepository
from app.repositories.conta_repository import ContaRepository
from app.repositories.emprestimo_repository import EmprestimoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.repositories.financiamento_repository import FinanciamentoRepository
from app.repositories.meta_repository import MetaRepository
from app.repositories.parcelamento_repository import ParcelamentoRepository
from app.repositories.sessao_usuario_repository import SessaoUsuarioRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.transacao_repository import TransacaoRepository
from app.repositories.transferencia_repository import TransferenciaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.anexo_service import AnexoService
from app.services.auth_service import AuthService
from app.services.cartao_service import CartaoService
from app.services.categoria_service import CategoriaService
from app.services.central_financeira_service import CentralFinanceiraService
from app.services.conta_recorrente_service import ContaRecorrenteService
from app.services.conta_service import ContaService
from app.services.emprestimo_service import EmprestimoService
from app.services.fatura_service import FaturaService
from app.services.financiamento_service import FinanciamentoService
from app.services.meta_service import MetaService
from app.services.parcelamento_service import ParcelamentoService
from app.services.tag_service import TagService
from app.services.transacao_service import TransacaoService
from app.services.transferencia_service import TransferenciaService

logger = logging.getLogger(__name__)

DbSession = Annotated[Session, Depends(get_db)]


# --- Repositories e Services (injeção padrão do projeto) -------------------

def get_usuario_repository(db: DbSession) -> UsuarioRepository:
    return UsuarioRepository(db)


def get_sessao_usuario_repository(db: DbSession) -> SessaoUsuarioRepository:
    return SessaoUsuarioRepository(db)


def get_auth_service(
    usuario_repo: Annotated[UsuarioRepository, Depends(get_usuario_repository)],
    sessao_repo: Annotated[SessaoUsuarioRepository, Depends(get_sessao_usuario_repository)],
) -> AuthService:
    return AuthService(usuario_repo, sessao_repo)


def get_conta_repository(db: DbSession) -> ContaRepository:
    return ContaRepository(db)


def get_categoria_repository(db: DbSession) -> CategoriaRepository:
    return CategoriaRepository(db)


def get_categoria_service(
    categoria_repo: Annotated[CategoriaRepository, Depends(get_categoria_repository)],
) -> CategoriaService:
    return CategoriaService(categoria_repo)


def get_tag_repository(db: DbSession) -> TagRepository:
    return TagRepository(db)


def get_tag_service(
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
) -> TagService:
    return TagService(tag_repo)


def get_cartao_repository(db: DbSession) -> CartaoRepository:
    return CartaoRepository(db)


def get_fatura_repository(db: DbSession) -> FaturaRepository:
    return FaturaRepository(db)


def get_transacao_repository(db: DbSession) -> TransacaoRepository:
    return TransacaoRepository(db)


def get_parcelamento_repository(db: DbSession) -> ParcelamentoRepository:
    return ParcelamentoRepository(db)


def get_financiamento_repository(db: DbSession) -> FinanciamentoRepository:
    return FinanciamentoRepository(db)


def get_emprestimo_repository(db: DbSession) -> EmprestimoRepository:
    return EmprestimoRepository(db)


def get_transferencia_repository(db: DbSession) -> TransferenciaRepository:
    return TransferenciaRepository(db)


def get_conta_recorrente_repository(db: DbSession) -> ContaRecorrenteRepository:
    return ContaRecorrenteRepository(db)


def get_meta_repository(db: DbSession) -> MetaRepository:
    return MetaRepository(db)


def get_fatura_service(
    fatura_repo: Annotated[FaturaRepository, Depends(get_fatura_repository)],
    cartao_repo: Annotated[CartaoRepository, Depends(get_cartao_repository)],
    transacao_repo: Annotated[TransacaoRepository, Depends(get_transacao_repository)],
) -> FaturaService:
    # FaturaService recebe CartaoRepository (posse transitiva - Fatura nao
    # tem usuario_id proprio) e TransacaoRepository (persistir a transacao
    # de pagamento em registrar_pagamento(), e resolver_fatura_aberta() nao
    # precisa de mais nada alem do que ja tinha).
    return FaturaService(fatura_repo, cartao_repo, transacao_repo)


def get_transacao_service(
    transacao_repo: Annotated[TransacaoRepository, Depends(get_transacao_repository)],
    conta_repo: Annotated[ContaRepository, Depends(get_conta_repository)],
    cartao_repo: Annotated[CartaoRepository, Depends(get_cartao_repository)],
    categoria_repo: Annotated[CategoriaRepository, Depends(get_categoria_repository)],
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
    parcelamento_repo: Annotated[ParcelamentoRepository, Depends(get_parcelamento_repository)],
    financiamento_repo: Annotated[FinanciamentoRepository, Depends(get_financiamento_repository)],
    emprestimo_repo: Annotated[EmprestimoRepository, Depends(get_emprestimo_repository)],
    conta_recorrente_repo: Annotated[ContaRecorrenteRepository, Depends(get_conta_recorrente_repository)],
    meta_repo: Annotated[MetaRepository, Depends(get_meta_repository)],
    fatura_repo: Annotated[FaturaRepository, Depends(get_fatura_repository)],
    fatura_service: Annotated[FaturaService, Depends(get_fatura_service)],
) -> TransacaoService:
    return TransacaoService(
        transacao_repo,
        conta_repo,
        cartao_repo,
        categoria_repo,
        tag_repo,
        parcelamento_repo,
        financiamento_repo,
        emprestimo_repo,
        conta_recorrente_repo,
        meta_repo,
        fatura_repo,
        fatura_service,
    )


def get_parcelamento_service(
    parcelamento_repo: Annotated[ParcelamentoRepository, Depends(get_parcelamento_repository)],
    transacao_repo: Annotated[TransacaoRepository, Depends(get_transacao_repository)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
) -> ParcelamentoService:
    return ParcelamentoService(parcelamento_repo, transacao_repo, transacao_service)


def get_financiamento_service(
    financiamento_repo: Annotated[FinanciamentoRepository, Depends(get_financiamento_repository)],
    transacao_repo: Annotated[TransacaoRepository, Depends(get_transacao_repository)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
) -> FinanciamentoService:
    return FinanciamentoService(financiamento_repo, transacao_repo, transacao_service)


def get_emprestimo_service(
    emprestimo_repo: Annotated[EmprestimoRepository, Depends(get_emprestimo_repository)],
    transacao_repo: Annotated[TransacaoRepository, Depends(get_transacao_repository)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
) -> EmprestimoService:
    return EmprestimoService(emprestimo_repo, transacao_repo, transacao_service)


def get_conta_recorrente_service(
    conta_recorrente_repo: Annotated[ContaRecorrenteRepository, Depends(get_conta_recorrente_repository)],
    transacao_repo: Annotated[TransacaoRepository, Depends(get_transacao_repository)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
) -> ContaRecorrenteService:
    return ContaRecorrenteService(conta_recorrente_repo, transacao_repo, transacao_service)


def get_cartao_service(
    cartao_repo: Annotated[CartaoRepository, Depends(get_cartao_repository)],
    conta_repo: Annotated[ContaRepository, Depends(get_conta_repository)],
    fatura_service: Annotated[FaturaService, Depends(get_fatura_service)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
    parcelamento_service: Annotated[ParcelamentoService, Depends(get_parcelamento_service)],
    conta_recorrente_service: Annotated[ContaRecorrenteService, Depends(get_conta_recorrente_service)],
) -> CartaoService:
    # CartaoService recebe ContaRepository (valida posse de
    # conta_pagamento_id), FaturaService - correcao do bug "limite
    # disponivel nao volta ao pagar fatura" (2026-07):
    # FaturaService.ids_faturas_pagas() e a UNICA fonte de verdade sobre
    # "o que conta como pago" (mesma derivacao de status_calculado usada em
    # toda a tela de Fatura), entao CartaoService reusa esse calculo em vez
    # de duplicar a regra comparando com a coluna Fatura.status (que nunca
    # chega a valer PAGA de verdade - ver docstring de StatusFatura) - e
    # agora tambem TransacaoService, usado só quando `excluir()` é chamado
    # com `apagar_transacoes=True` (ver
    # docs/analise-arquitetural-exclusao-cartao-com-historico.md). Definida
    # só depois de `get_parcelamento_service`/`get_conta_recorrente_service`
    # (ordem importa: `Depends(...)` como valor default é avaliado de cima
    # pra baixo) - correção do bug "excluir cartão falha com Falha de
    # conexão com o servidor" (2026-07-21, ver
    # `CartaoService._apagar_faturas_e_transacoes`).
    return CartaoService(
        cartao_repo, conta_repo, fatura_service, transacao_service, parcelamento_service, conta_recorrente_service
    )


def get_meta_service(
    meta_repo: Annotated[MetaRepository, Depends(get_meta_repository)],
    conta_repo: Annotated[ContaRepository, Depends(get_conta_repository)],
) -> MetaService:
    return MetaService(meta_repo, conta_repo)


def get_transferencia_service(
    transferencia_repo: Annotated[TransferenciaRepository, Depends(get_transferencia_repository)],
    conta_repo: Annotated[ContaRepository, Depends(get_conta_repository)],
) -> TransferenciaService:
    return TransferenciaService(transferencia_repo, conta_repo)


def get_conta_service(
    conta_repo: Annotated[ContaRepository, Depends(get_conta_repository)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
    transferencia_service: Annotated[TransferenciaService, Depends(get_transferencia_service)],
    cartao_service: Annotated[CartaoService, Depends(get_cartao_service)],
    financiamento_service: Annotated[FinanciamentoService, Depends(get_financiamento_service)],
    emprestimo_service: Annotated[EmprestimoService, Depends(get_emprestimo_service)],
    conta_recorrente_service: Annotated[ContaRecorrenteService, Depends(get_conta_recorrente_service)],
    parcelamento_service: Annotated[ParcelamentoService, Depends(get_parcelamento_service)],
) -> ContaService:
    # Definida só depois de todos os Services acima (ordem importa aqui:
    # `Depends(...)` como valor default é avaliado na hora que o `def`
    # executa, de cima pra baixo) - ContaService agora depende de todos
    # eles para a exclusão em cascata (`excluir(..., apagar_vinculos=True)`,
    # ver docs/analise-arquitetural-exclusao-conta-com-historico.md), mesmo
    # raciocínio já usado ao mover `get_cartao_service` para depois de
    # `get_transacao_service`. `parcelamento_service` adicionado na correção
    # do bug "excluir cartão falha com Falha de conexão com o servidor"
    # (2026-07-21) - a mesma cascata de Parcelamento também se aplica a
    # Conta (`ck_parcelamento_cartao_xor_conta`).
    return ContaService(
        conta_repo,
        transacao_service,
        transferencia_service,
        cartao_service,
        financiamento_service,
        emprestimo_service,
        conta_recorrente_service,
        parcelamento_service,
    )


def get_anexo_repository(db: DbSession) -> AnexoRepository:
    return AnexoRepository(db)


def get_anexo_service(
    anexo_repo: Annotated[AnexoRepository, Depends(get_anexo_repository)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
) -> AnexoService:
    # AnexoService recebe TransacaoService (nao TransacaoRepository
    # diretamente) - posse de Anexo e SEMPRE transitiva via Transacao (Anexo
    # nao tem usuario_id proprio), e toda checagem de posse reaproveita
    # TransacaoService.obter() (ja levanta NotFoundError uniforme), nunca
    # duplica essa logica aqui - decisao explicita do usuario, ver
    # docs/analise-arquitetural-anexo.md.
    return AnexoService(anexo_repo, transacao_service)


def get_central_financeira_service(
    conta_service: Annotated[ContaService, Depends(get_conta_service)],
    cartao_service: Annotated[CartaoService, Depends(get_cartao_service)],
    fatura_service: Annotated[FaturaService, Depends(get_fatura_service)],
    transacao_service: Annotated[TransacaoService, Depends(get_transacao_service)],
    financiamento_service: Annotated[FinanciamentoService, Depends(get_financiamento_service)],
    emprestimo_service: Annotated[EmprestimoService, Depends(get_emprestimo_service)],
    parcelamento_service: Annotated[ParcelamentoService, Depends(get_parcelamento_service)],
    meta_service: Annotated[MetaService, Depends(get_meta_service)],
    transferencia_service: Annotated[TransferenciaService, Depends(get_transferencia_service)],
    conta_recorrente_service: Annotated[ContaRecorrenteService, Depends(get_conta_recorrente_service)],
    categoria_service: Annotated[CategoriaService, Depends(get_categoria_service)],
) -> CentralFinanceiraService:
    # CentralFinanceiraService NAO recebe nenhum Repository - so os Services
    # de dominio ja existentes, injetados por construtor. Ver
    # docs/analise-arquitetural-central-financeira.md, secao 5.
    # `transferencia_service` (Etapa de Transferências/Calendário Financeiro)
    # só é usado por `calendario_financeiro` - nenhum outro método lê
    # Transferencia. `conta_recorrente_service` (expansão de Contas
    # Recorrentes, 2026-07-20): idem, só para a projeção virtual de
    # ocorrências futuras no calendário (`previsto=True`). `categoria_service`
    # (Etapa de Gráficos, docs/analise-arquitetural-graficos.md): só usado por
    # `graficos_periodo`, para resolver nome/cor/ícone de cada categoria.
    return CentralFinanceiraService(
        conta_service,
        cartao_service,
        fatura_service,
        transacao_service,
        financiamento_service,
        emprestimo_service,
        parcelamento_service,
        meta_service,
        transferencia_service,
        conta_recorrente_service,
        categoria_service,
    )


# --- Autenticação ------------------------------------------------------------
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    usuario_repo: Annotated[UsuarioRepository, Depends(get_usuario_repository)],
) -> Usuario:
    if credenciais is None:
        logger.warning("tentativa_acesso_nao_autorizada motivo=sem_token")
        raise NaoAutenticadoError("Não autenticado.")

    try:
        payload = decodificar_access_token(credenciais.credentials)
    except TokenInvalidoError:
        logger.warning("tentativa_acesso_nao_autorizada motivo=token_invalido_ou_expirado")
        raise NaoAutenticadoError("Token inválido ou expirado.")

    usuario_id = int(payload["sub"])
    usuario = usuario_repo.get(usuario_id)
    if usuario is None or not usuario.ativo:
        logger.warning(
            "tentativa_acesso_nao_autorizada usuario_id=%s motivo=usuario_inativo_ou_removido", usuario_id
        )
        raise NaoAutenticadoError("Token inválido ou expirado.")

    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def exigir_papel(*papeis_permitidos: TipoPapel):
    def verificar(usuario: CurrentUser) -> Usuario:
        if usuario.papel not in papeis_permitidos:
            logger.warning(
                "tentativa_acesso_nao_autorizada usuario_id=%s papel=%s motivo=papel_insuficiente",
                usuario.id,
                usuario.papel.value,
            )
            raise AcessoNegadoError("Você não tem permissão para executar esta ação.")
        return usuario

    return verificar
