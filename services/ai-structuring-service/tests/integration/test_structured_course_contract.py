"""Contrato da saida estruturada, do provedor ate o dominio (RNF03).

Fecha o caminho "prompt versionado -> provedor -> curso validado": o texto que
sai do provedor e validado contra a forma canonica de ``app.domain.course``, e
o que nao cabe nela e falha, nao resultado aproveitavel (ADR-0006).

O provedor usado e o mock - sem chave, sem rede e sem custo (RNF12).
"""

import json

import pytest

from app.core.exceptions import LLMInvalidResponseError
from app.domain.course import (
    CAMPOS_INFERIVEIS,
    CHAVES_CANONICAS,
    CHAVES_OBRIGATORIAS,
    schema_do_curso_estruturado,
    validar_curso_estruturado,
)
from app.prompts import carregar_prompt
from app.providers import MockLLMProvider
from app.providers.base import CompletionParams

DEMANDA = """
Boa tarde! Precisamos de um treinamento de NR-12 para o pessoal da manutencao
da planta 2, uns 25 tecnicos, em dois dias de 8 horas.
"""


async def test_resposta_do_provedor_e_validada_na_forma_canonica() -> None:
    prompt = carregar_prompt("extract-requirements", "v2")

    resultado = await MockLLMProvider().complete(
        prompt.render(texto_normalizado=DEMANDA),
        CompletionParams(
            temperature=0.0,
            response_schema=schema_do_curso_estruturado(),
        ),
    )
    curso = validar_curso_estruturado(resultado.text)

    assert tuple(curso.to_canonical_dict()) == CHAVES_CANONICAS
    assert curso.tema
    assert curso.ementa


async def test_duas_execucoes_produzem_curso_de_mesma_forma() -> None:
    """Criterio do card: a forma da saida nao depende da execucao."""

    provider = MockLLMProvider()
    prompt = carregar_prompt("extract-requirements", "v2")

    primeira = validar_curso_estruturado(
        (await provider.complete(prompt.render(texto_normalizado=DEMANDA))).text
    )
    segunda = validar_curso_estruturado(
        (await provider.complete(prompt.render(texto_normalizado="Outra demanda qualquer."))).text
    )

    assert tuple(primeira.to_canonical_dict()) == tuple(segunda.to_canonical_dict())
    assert primeira.to_canonical_json() == segunda.to_canonical_json()


async def test_resposta_com_campo_fora_do_contrato_e_falha() -> None:
    fora_do_contrato = json.dumps(
        {
            "tema": "NR-12",
            "publico_alvo": "Tecnicos de manutencao",
            "carga_horaria": 16,
            "ementa": [],
            "objetivos_aprendizagem": [],
            "campos_ausentes": ["ementa", "objetivos_aprendizagem"],
            "observacoes": [],
            "orcamento_estimado": 12000,
        }
    )
    provider = MockLLMProvider(response_text=fora_do_contrato)

    resultado = await provider.complete("prompt de extracao")

    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resultado.text)


async def test_resposta_em_texto_livre_e_falha() -> None:
    provider = MockLLMProvider(response_text="Nao consegui estruturar essa demanda.")

    resultado = await provider.complete("prompt de extracao")

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resultado.text)

    assert excinfo.value.http_status == 502


def test_prompt_ativo_declara_as_chaves_obrigatorias_do_contrato() -> None:
    """Prompt e schema andam juntos: divergir aqui quebra a extracao (RF13, RNF03)."""

    corpo = carregar_prompt("extract-requirements", "v2").corpo

    for chave in CHAVES_OBRIGATORIAS:
        assert f'"{chave}"' in corpo, chave


async def test_resposta_sem_carga_horaria_chega_ao_dominio_como_ausencia() -> None:
    """Criterio do card: o que o provedor nao trouxe vira nulo e campo ausente (RNF03).

    RF14.2 no Documento Consolidado de Requisitos v1.0. O caminho e o mesmo da
    execucao real - provedor, texto JSON, validacao -, so que com a resposta
    incompleta que o mock devolve sob encomenda.
    """

    incompleta = json.dumps(
        {
            "tema": "Lideranca para coordenadores recem-promovidos",
            "publico_alvo": "Coordenadores promovidos no ano corrente",
            "carga_horaria": None,
            "ementa": [],
            "objetivos_aprendizagem": [],
            "campos_ausentes": [],
            "observacoes": [
                "carga_horaria: o cliente adiou a definicao da duracao "
                "('ainda nao fechou quantas horas')."
            ],
        }
    )
    provider = MockLLMProvider(response_text=incompleta)

    resultado = await provider.complete("prompt de extracao")
    curso = validar_curso_estruturado(resultado.text)

    assert curso.carga_horaria is None
    assert curso.campos_ausentes == ["carga_horaria", "objetivos_aprendizagem", "ementa"]
    assert curso.motivos_dos_campos_ausentes()["carga_horaria"]


async def test_nenhum_campo_ganha_valor_plausivel_ao_passar_pela_validacao() -> None:
    """Demanda sem informacao produz curso vazio - e vazio declarado, nao preenchido."""

    sem_informacao = json.dumps(
        {
            "tema": None,
            "publico_alvo": "",
            "carga_horaria": None,
            "ementa": [],
            "objetivos_aprendizagem": [],
            "campos_ausentes": ["tema"],
            "observacoes": [],
        }
    )
    provider = MockLLMProvider(response_text=sem_informacao)

    resultado = await provider.complete("prompt de extracao")
    canonico = validar_curso_estruturado(resultado.text).to_canonical_dict()

    assert all(canonico[campo] in (None, []) for campo in CAMPOS_INFERIVEIS)
    assert canonico["campos_ausentes"] == [
        "tema",
        "publico_alvo",
        "carga_horaria",
        "objetivos_aprendizagem",
        "ementa",
    ]
