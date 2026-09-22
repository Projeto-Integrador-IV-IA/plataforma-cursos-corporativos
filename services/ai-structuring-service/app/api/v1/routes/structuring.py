"""Rotas de estruturacao (RF11, RF12, RF17).

    POST /api/v1/structuring                estrutura o curso e espera o resultado
    POST /api/v1/structuring/jobs           aceita o pedido e devolve identificador
    GET  /api/v1/structuring/jobs/{id}      estado da execucao (RF17, RNF06)
    GET  /api/v1/structuring/metrics        metricas agregadas de qualidade (RNF04)

As tres primeiras estao implementadas; as metricas entram com o card de RNF04.

O caminho sincrono continua existindo de proposito: e por ele que a avaliacao
de qualidade (RNF04) exercita o mesmo codigo sem precisar esperar em fila, e e
o mais simples de depurar. O assincrono e o que a interface usa, porque uma
chamada de dezenas de segundos prenderia a tela (RF17, RNF06).

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
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.config import Settings, get_settings
from app.providers.factory import get_llm_provider
from app.schemas.jobs import StructuringJobAccepted, StructuringJobRead
from app.schemas.structuring import StructuringRequest, StructuringResponse
from app.services.job_service import StructuringJobService
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


def get_job_service(
    request: Request,
    service: Annotated[StructuringService, Depends(get_structuring_service)],
) -> StructuringJobService:
    """Devolve o registro de execucoes da aplicacao, criando-o na primeira vez.

    O registro vive no ``state`` da aplicacao, e nao por requisicao: cada
    requisicao com o seu proprio registro perderia o identificador assim que a
    resposta do aceite fosse enviada, e toda consulta responderia 404. Pela
    mesma razao ele nao pode ser recriado a cada chamada aqui.
    """

    existente = getattr(request.app.state, "structuring_jobs", None)
    if existente is None:
        existente = StructuringJobService(service)
        request.app.state.structuring_jobs = existente
    return existente


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


@router.post(
    "/structuring/jobs",
    response_model=StructuringJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Aceitar a estruturacao e devolver o identificador da execucao",
    response_description="Pedido aceito; o resultado e consultado pelo identificador.",
)
async def submit_structuring_job(
    payload: StructuringRequest,
    jobs: Annotated[StructuringJobService, Depends(get_job_service)],
) -> StructuringJobAccepted:
    """Aceita o pedido sem esperar o modelo responder (RF17, RNF06).

    202 e nao 200: o recurso devolvido e a **execucao**, nao o curso, que ainda
    nao existe. A entrada passa pela mesma validacao do caminho sincrono, entao
    texto vazio ou versao de prompt inexistente continua sendo recusado aqui,
    antes de ocupar lugar na fila.
    """

    job = jobs.submit(
        RawDemand(demand_id=payload.demand_id, text=payload.text),
        prompt_version=payload.prompt_version,
    )
    return StructuringJobAccepted.from_job(job)


@router.get(
    "/structuring/jobs/{job_id}",
    response_model=StructuringJobRead,
    summary="Consultar o estado de uma execucao de estruturacao",
    response_description="Estado corrente e, quando concluida, o curso produzido.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Identificador desconhecido (STRUCTURING_JOB_NOT_FOUND). "
            "Execucoes nao sobrevivem ao reinicio do servico; a demanda bruta, sim.",
        },
    },
)
async def get_structuring_job(
    job_id: UUID,
    jobs: Annotated[StructuringJobService, Depends(get_job_service)],
) -> StructuringJobRead:
    """Informa em que pe esta a execucao, sem bloquear quem pergunta.

    Enquanto nao concluiu, ``result`` vem nulo: nao existe curso parcial, e
    devolver um esqueleto vazio faria a tela exibir campos que ninguem
    preencheu (RNF03).
    """

    return StructuringJobRead.from_job(jobs.get(job_id))
