"""Fluxo completo do MVP contra a stack real (ver tests/README.md).

Nenhum mock aqui: cada chamada atravessa o gateway de verdade. O objetivo e o
mesmo da 4a parcial (17/11) - prova que os quatro servicos se integram, nao
que cada um funciona isolado (isso e responsabilidade de
``services/<servico>/tests``).
"""

import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import ApiClient

TEXTO_ORIGINAL = (
    "Oi! Precisamos de um treinamento de NR-12 para 25 tecnicos da manutencao da "
    "planta 2, em dois dias de 8 horas, no proprio site. Abs, Marina.\n"
    "-- enviado do meu celular"
)


def _aguardar_desfecho(api: ApiClient, job_id: str) -> dict:
    for _ in range(60):
        status, job = api.call("GET", f"/structuring/jobs/{job_id}")
        if job["status"] in {"CONCLUIDA", "ERRO"}:
            return job
        time.sleep(1)
    raise AssertionError(f"job {job_id} nao chegou a um desfecho em 60s")


def test_fluxo_completo_login_ate_historico_de_etapas(authed_api: ApiClient) -> None:
    api = authed_api

    # 1. Autenticar (RF16) - ja feito pela fixture `authed_api`.

    # 2. Cliente (RF01) e demanda (RF02).
    nome_cliente = f"Cliente E2E {uuid.uuid4().hex[:8]}"
    status, cliente = api.call("POST", "/clients", {"name": nome_cliente})
    assert status == 201, cliente
    client_id = cliente["id"]

    status, demanda = api.call(
        "POST", "/demands", {"client_id": client_id, "title": "Treinamento NR-12 — teste E2E"}
    )
    assert status == 201, demanda
    demand_id = demanda["id"]

    # 3/4. Registrar demanda bruta em texto livre (RF09) e confirmar que o bruto
    # foi persistido antes de qualquer chamada ao LLM (RNF05): a captacao
    # devolve 201 sozinha, sem nenhuma dependencia de estruturacao.
    status, captura = api.call(
        "POST", "/ingestion", {"text": TEXTO_ORIGINAL, "source_type": "MENSAGENS", "demand_id": demand_id}
    )
    assert status == 201, captura
    assert captura["status"] == "RECEBIDA"
    raw_input_id = captura["raw_input_id"]

    time.sleep(1)  # normalizacao (RF10) e persistencia de trechos (RF29) sao pos-resposta

    status, raw_input = api.call("GET", f"/raw-inputs/{raw_input_id}")
    assert status == 200
    assert raw_input["original_content"] == TEXTO_ORIGINAL, "o bruto precisa sobreviver intacto"

    # 5. Obter o curso estruturado e conferir que foi anexado a negociacao
    # (RF11, RF12, RF13).
    status, aceite = api.call(
        "POST",
        "/structuring/jobs",
        {"demand_id": demand_id, "text": TEXTO_ORIGINAL, "source_ids": [raw_input_id]},
    )
    assert status == 202, aceite
    job = _aguardar_desfecho(api, aceite["job_id"])
    assert job["status"] == "CONCLUIDA", job
    assert job["result"]["course"]["tema"]

    status, artefatos = api.call("GET", f"/demands/{demand_id}/artifacts")
    assert status == 200
    assert len(artefatos) == 1, "o curso gerado precisa estar anexado a demanda"
    artifact_id = artefatos[0]["id"]

    # 6. Editar a saida da IA como operador (RF14): salva uma nova versao
    # HUMANO sem apagar a versao da IA.
    conteudo_v1 = artefatos[0]["versions"][0]["structured_content"]
    status, v2 = api.call(
        "POST",
        f"/artifacts/{artifact_id}/versions",
        {"base_version_number": 1, "structured_content": {**conteudo_v1, "tema": "NR-12 revisado"}},
    )
    assert status == 201, v2
    assert v2["origin"] == "HUMANO"

    # RF19.2: decisao formal sobre a versao vigente (a 2, editada acima).
    status, decisao = api.call(
        "POST", f"/artifacts/{artifact_id}/review", {"version_number": 2, "decision": "APROVADO"}
    )
    assert status == 201, decisao
    assert decisao["decision"] == "APROVADO"

    # 7. Avancar e retroceder etapas do pipeline (RF05, RF06).
    status, avanco = api.call("POST", f"/demands/{demand_id}/advance")
    assert status == 200 and avanco["current_stage"] == "ESTRUTURACAO", avanco

    status, retrocesso = api.call(
        "POST",
        f"/demands/{demand_id}/rollback",
        {"to_stage": "CAPTACAO", "reason": "Teste E2E validando RF06"},
    )
    assert status == 200 and retrocesso["current_stage"] == "CAPTACAO", retrocesso

    # 8. Historico registra todas as transicoes, sem lacuna (RF07, RNF09).
    status, historico = api.call("GET", f"/demands/{demand_id}/transitions")
    assert status == 200
    transicoes = historico["items"]
    assert [item["to_stage"] for item in transicoes] == ["ESTRUTURACAO", "CAPTACAO"]

    # 9. Recuperar uma versao anterior do artefato (RF08, RF15).
    status, restaurada = api.call("POST", f"/artifacts/{artifact_id}/versions/1/restore")
    assert status == 201, restaurada
    assert restaurada["structured_content"] == conteudo_v1
    assert restaurada["number"] == 3, "restaurar cria versao nova, nunca sobrescreve"


def test_requisicao_sem_token_e_recusada_em_toda_rota_protegida(api: ApiClient) -> None:
    """RNF10: so login e health ficam de fora da exigencia de sessao."""

    status, _ = api.call("GET", "/demands")
    assert status == 401


def test_transicao_invalida_de_etapa_e_recusada_sem_alterar_historico(
    authed_api: ApiClient,
) -> None:
    """Avancar demanda ja na ultima etapa (ACOMPANHAMENTO) e recusado, sem novo evento."""

    api = authed_api
    status, cliente = api.call("POST", "/clients", {"name": f"Cliente E2E {uuid.uuid4().hex[:8]}"})
    assert status == 201
    status, demanda = api.call(
        "POST", "/demands", {"client_id": cliente["id"], "title": "Demanda so para transicao"}
    )
    assert status == 201
    demand_id = demanda["id"]

    for _ in range(4):  # CAPTACAO -> ESTRUTURACAO -> PRODUTO -> PROPOSTA -> ACOMPANHAMENTO
        status, _ = api.call("POST", f"/demands/{demand_id}/advance")
        assert status == 200

    status, historico_antes = api.call("GET", f"/demands/{demand_id}/transitions")
    total_antes = len(historico_antes["items"])

    status, recusado = api.call("POST", f"/demands/{demand_id}/advance")
    assert status == 409, recusado

    status, historico_depois = api.call("GET", f"/demands/{demand_id}/transitions")
    assert len(historico_depois["items"]) == total_antes, "transicao recusada nao pode criar evento"
