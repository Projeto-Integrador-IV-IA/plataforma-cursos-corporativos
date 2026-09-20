"""Rotas de estruturacao (RF11, RF12, RF17).

    POST /api/v1/structuring                estrutura o curso a partir de texto normalizado
    GET  /api/v1/structuring/jobs/{id}      estado da execucao (RF17, RNF06)
    GET  /api/v1/structuring/metrics        metricas agregadas de qualidade (RNF04)

Implementada hoje apenas a primeira: e o caso de uso de ponta a ponta do
servico (RF11; **RF13.1** no Documento Consolidado de Requisitos v1.0). As
outras duas entram com os cards de RF17 e RNF04.

A rota e fina de proposito - valida a entrada, delega ao caso de uso e traduz o
desfecho. Regra de negocio nenhuma mora aqui: politica de retentativa e
validacao de schema ficam em ``app.services.structuring_service``, de modo que
a avaliacao de qualidade (RNF04) exercite o mesmo caminho que o operador, sem
passar por HTTP.

Falha do provedor nao e tratada aqui: ``raise_for_course`` levanta o erro
tipado e o handler registrado em ``app.main`` o traduz no corpo unico de erro
da plataforma, com o codigo que diz se vale reprocessar (RNF02, RNF05).
"""

from typing import Annotated, Any, Final

from fastapi import APIRouter, Depends, status

from app.core.config import Settings, get_settings
from app.providers.factory import get_llm_provider
from app.schemas.structuring import StructuringRequest, StructuringResponse
from app.services.structuring_service import RawDemand, StructuringService

router = APIRouter(tags=["structuring"])

#: Falhas previsiveis da estruturacao, declaradas para que aparecam no Swagger
#: com o codigo que o frontend trata (RNF02). O corpo segue
#: ``packages/contracts/schemas/error.schema.json``.
RESPOSTAS_DE_ERRO: Final[dict[int | str, dict[str, Any]]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "description": "Limite de uso do provedor de LLM atingido (LLM_RATE_LIMITED). "
        "A demanda bruta continua intacta e pode ser reprocessada.",
    },
    status.HTTP_502_BAD_GATEWAY: {
        "description": "Resposta do provedor fora do schema do curso estruturado "
        "(LLM_INVALID_RESPONSE). Resposta invalida e falha, nao resultado aproveitavel.",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Provedor de LLM indisponivel (LLM_UNAVAILABLE) depois de "
        "esgotadas as retentativas. A demanda bruta continua intacta.",
    },
    status.HTTP_504_GATEWAY_TIMEOUT: {
        "description": "Provedor de LLM excedeu o tempo maximo de resposta (LLM_TIMEOUT).",
    },
}


def get_structuring_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StructuringService:
    """Monta o caso de uso com o provedor indicado por ``LLM_PROVIDER`` (RNF03).

    Injetado como dependencia para que o teste troque provedor e configuracao
    sem variavel de ambiente e sem tocar a rota.
    """

    return StructuringService(get_llm_provider(settings), settings)


@router.post(
    "/structuring",
    response_model=StructuringResponse,
    status_code=status.HTTP_200_OK,
    summary="Estruturar o curso a partir do texto normalizado da demanda",
    response_description="Curso estruturado na forma canonica, com a proveniencia da execucao.",
    responses=RESPOSTAS_DE_ERRO,
)
async def structure_course(
    payload: StructuringRequest,
    service: Annotated[StructuringService, Depends(get_structuring_service)],
) -> StructuringResponse:
    """Devolve tema, publico, carga horaria, ementa e objetivos do texto recebido.

    O texto chega ja normalizado pelo ingestion-service (RF10) e ja persistido
    la (RNF05): esta rota nao grava nada e nao fala com o banco de outro
    servico. Nao ha recurso criado, por isso 200 e nao 201 - anexar o resultado
    a negociacao e trabalho do pipeline-service (RF13).

    O que volta nunca e "quase certo": ou o curso passou na validacao contra o
    schema canonico (RNF03), ou a resposta e um erro identificado. E saida de
    modelo, entao passa por revisao humana antes de virar proposta (RF14).
    """

    outcome = await service.structure_course(
        RawDemand(demand_id=payload.demand_id, text=payload.text),
        prompt_version=payload.prompt_version,
    )
    return StructuringResponse.from_outcome(outcome)
