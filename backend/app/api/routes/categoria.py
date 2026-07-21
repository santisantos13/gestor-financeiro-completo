"""Router de Categoria: CRUD protegido.

Nenhuma rota aceita `usuario_id` no payload - vem sempre de `usuario_atual`
(CurrentUser). Categorias do sistema (usuario_id nulo) nunca são criadas
por aqui - só via seed/migration futura -, então CategoriaCreate nem
expõe esse campo.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_categoria_service
from app.schemas.categoria import CategoriaCreate, CategoriaRead, CategoriaUpdate
from app.services.categoria_service import CategoriaService

router = APIRouter(prefix="/categorias", tags=["categorias"])

CategoriaServiceDep = Annotated[CategoriaService, Depends(get_categoria_service)]


@router.post("", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    dados: CategoriaCreate, usuario_atual: CurrentUser, categoria_service: CategoriaServiceDep
) -> CategoriaRead:
    categoria = categoria_service.criar(dados, usuario_atual.id)
    return CategoriaRead.model_validate(categoria)


@router.get("", response_model=list[CategoriaRead])
def listar_categorias(
    usuario_atual: CurrentUser,
    categoria_service: CategoriaServiceDep,
    apenas_ativas: bool = True,
    incluir_ocultas: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[CategoriaRead]:
    categorias = categoria_service.listar(
        usuario_atual.id,
        apenas_ativas=apenas_ativas,
        incluir_ocultas=incluir_ocultas,
        skip=skip,
        limit=limit,
    )
    return [CategoriaRead.model_validate(categoria) for categoria in categorias]


@router.get("/{categoria_id}", response_model=CategoriaRead)
def obter_categoria(
    categoria_id: int, usuario_atual: CurrentUser, categoria_service: CategoriaServiceDep
) -> CategoriaRead:
    categoria = categoria_service.obter(categoria_id, usuario_atual.id)
    return CategoriaRead.model_validate(categoria)


@router.patch("/{categoria_id}", response_model=CategoriaRead)
def atualizar_categoria(
    categoria_id: int,
    dados: CategoriaUpdate,
    usuario_atual: CurrentUser,
    categoria_service: CategoriaServiceDep,
) -> CategoriaRead:
    categoria = categoria_service.atualizar(categoria_id, dados, usuario_atual.id)
    return CategoriaRead.model_validate(categoria)


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_categoria(
    categoria_id: int, usuario_atual: CurrentUser, categoria_service: CategoriaServiceDep
) -> None:
    categoria_service.desativar(categoria_id, usuario_atual.id)


@router.delete("/{categoria_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_categoria_permanente(
    categoria_id: int, usuario_atual: CurrentUser, categoria_service: CategoriaServiceDep
) -> None:
    """Exclusão definitiva (hard delete) - Etapa F10,
    `docs/analise-arquitetural-exclusao.md`, seção 1."""
    categoria_service.excluir(categoria_id, usuario_atual.id)


@router.delete("/{categoria_id}/ocultar", status_code=status.HTTP_204_NO_CONTENT)
def ocultar_categoria_para_usuario(
    categoria_id: int, usuario_atual: CurrentUser, categoria_service: CategoriaServiceDep
) -> None:
    """"Excluir" uma categoria de sistema DO PONTO DE VISTA DO USUÁRIO
    ATUAL (Sprint de Refinamento Premium, item 4,
    `docs/analise-arquitetural-sprint-refinamento-premium.md`, seção 4) -
    nunca apaga nem desativa a linha de `Categoria`, que continua existindo
    normalmente para todos os outros usuários."""
    categoria_service.ocultar_para_usuario(categoria_id, usuario_atual.id)


@router.post("/{categoria_id}/reexibir", status_code=status.HTTP_204_NO_CONTENT)
def reexibir_categoria_para_usuario(
    categoria_id: int, usuario_atual: CurrentUser, categoria_service: CategoriaServiceDep
) -> None:
    """Reverte `ocultar_categoria_para_usuario` acima."""
    categoria_service.reexibir_para_usuario(categoria_id, usuario_atual.id)
