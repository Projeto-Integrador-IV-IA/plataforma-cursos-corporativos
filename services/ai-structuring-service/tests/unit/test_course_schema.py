"""Testes da forma canonica do curso estruturado (RNF03).

O que se verifica aqui: a saida tem sempre as mesmas chaves, na mesma ordem e
com os mesmos tipos, e tudo que foge do contrato e recusado.
"""

import json
from typing import Any

import pytest

from app.core.exceptions import LLMInvalidResponseError
from app.domain.course import (
    CAMPOS_DE_CONFIANCA,
    CAMPOS_EXTRAIDOS,
    CAMPOS_GERADOS,
    CHAVES_CANONICAS,
    CHAVES_OBRIGATORIAS,
    CourseFormat,
    StructuredCourse,
    schema_do_curso_estruturado,
    validar_curso_estruturado,
)

#: Resposta minima valida: so as chaves obrigatorias, todas sem conteudo.
RESPOSTA_VAZIA: dict[str, Any] = {
    "tema": None,
    "publico_alvo": None,
    "carga_horaria": None,
    "ementa": [],
    "objetivos_aprendizagem": [],
    "campos_ausentes": ["tema", "publico_alvo", "carga_horaria"],
    "observacoes": [],
}

#: Resposta completa, com os dez campos preenchidos. Dado ficticio (RNF10).
RESPOSTA_COMPLETA: dict[str, Any] = {
    "tema": "NR-12 (seguranca em maquinas e equipamentos)",
    "nicho": "Industria metalurgica",
    "publico_alvo": "Tecnicos de manutencao da planta 2",
    "numero_participantes": 25,
    "carga_horaria": 16,
    "formato": "presencial",
    "objetivos_aprendizagem": ["Aplicar o procedimento de bloqueio e etiquetagem"],
    "ementa": [
        {
            "titulo": "Fundamentos da NR-12",
            "topicos": ["Dispositivos de seguranca", "Analise de risco"],
            "carga_horaria": 8,
        }
    ],
    "campos_ausentes": [],
    "observacoes": [],
}


def resposta(**alteracoes: Any) -> dict[str, Any]:
    """Copia a resposta completa aplicando as alteracoes do caso de teste."""

    return {**RESPOSTA_COMPLETA, **alteracoes}


def test_chaves_canonicas_cobrem_extraidos_gerados_e_confianca() -> None:
    assert set(CHAVES_CANONICAS) == set(CAMPOS_EXTRAIDOS + CAMPOS_GERADOS + CAMPOS_DE_CONFIANCA)
    assert len(CHAVES_CANONICAS) == 10


def test_chaves_obrigatorias_sao_as_que_o_prompt_ativo_manda_devolver() -> None:
    assert set(CHAVES_OBRIGATORIAS) == {
        "tema",
        "publico_alvo",
        "carga_horaria",
        "ementa",
        "objetivos_aprendizagem",
        "campos_ausentes",
        "observacoes",
    }


def test_resposta_minima_ganha_a_forma_completa() -> None:
    curso = validar_curso_estruturado(RESPOSTA_VAZIA)

    canonico = curso.to_canonical_dict()

    assert tuple(canonico) == CHAVES_CANONICAS
    assert canonico["nicho"] is None
    assert canonico["numero_participantes"] is None
    assert canonico["formato"] is None


def test_duas_execucoes_com_conteudos_diferentes_tem_a_mesma_forma() -> None:
    """Criterio do card: mesma entrada, mesma forma - e mesma forma sempre."""

    primeira = validar_curso_estruturado(json.dumps(RESPOSTA_VAZIA)).to_canonical_dict()
    segunda = validar_curso_estruturado(json.dumps(RESPOSTA_COMPLETA)).to_canonical_dict()

    assert tuple(primeira) == tuple(segunda) == CHAVES_CANONICAS
    for chave in CHAVES_CANONICAS:
        esperado = type(RESPOSTA_COMPLETA[chave])
        assert isinstance(segunda[chave], esperado), chave
        assert primeira[chave] is None or isinstance(primeira[chave], esperado), chave


def test_serializacao_e_estavel_entre_chamadas() -> None:
    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.to_canonical_json() == curso.to_canonical_json()
    assert tuple(json.loads(curso.to_canonical_json())) == CHAVES_CANONICAS


def test_ordem_das_chaves_na_entrada_nao_muda_a_ordem_da_saida() -> None:
    invertida = dict(reversed(list(RESPOSTA_COMPLETA.items())))

    curso = validar_curso_estruturado(invertida)

    assert tuple(curso.to_canonical_dict()) == CHAVES_CANONICAS


def test_campo_extra_e_recusado() -> None:
    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(orcamento="R$ 12.000"))

    violacoes = excinfo.value.details["violacoes"]
    assert any(v["campo"] == "orcamento" for v in violacoes)
    assert excinfo.value.code == "LLM_INVALID_RESPONSE"


def test_campo_extra_dentro_de_um_modulo_da_ementa_e_recusado() -> None:
    modulo = {**RESPOSTA_COMPLETA["ementa"][0], "instrutor": "a definir"}

    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(ementa=[modulo]))


def test_chave_obrigatoria_ausente_e_recusada() -> None:
    incompleta = {chave: valor for chave, valor in RESPOSTA_VAZIA.items() if chave != "tema"}

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(incompleta)

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["tema"]


def test_texto_que_nao_e_json_e_recusado() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado("Claro! Aqui esta o curso estruturado:")


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("carga_horaria", "dezesseis horas"),
        ("carga_horaria", 0),
        ("numero_participantes", -3),
        ("objetivos_aprendizagem", "Aplicar o procedimento"),
        ("ementa", {"titulo": "Fundamentos"}),
        ("tema", ["NR-12"]),
    ],
)
def test_valor_fora_do_tipo_declarado_e_recusado(campo: str, valor: Any) -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(**{campo: valor}))


def test_modulo_da_ementa_sem_titulo_e_recusado() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(ementa=[{"titulo": "", "topicos": []}]))


def test_numero_escrito_como_texto_chega_ao_dominio_como_numero() -> None:
    """O prompt pede numero; texto numerico ainda assim vira ``int`` na saida."""

    curso = validar_curso_estruturado(resposta(carga_horaria="16"))

    assert curso.carga_horaria == 16
    assert curso.to_canonical_dict()["carga_horaria"] == 16


@pytest.mark.parametrize(
    ("grafia", "esperado"),
    [
        ("presencial", CourseFormat.PRESENCIAL),
        ("Presencial", CourseFormat.PRESENCIAL),
        (" ONLINE ", CourseFormat.ONLINE),
        ("on-line", CourseFormat.ONLINE),
        ("Hibrido", CourseFormat.HIBRIDO),
        ("híbrido", CourseFormat.HIBRIDO),
    ],
)
def test_formato_aceita_a_grafia_corrente_do_portugues(
    grafia: str,
    esperado: CourseFormat,
) -> None:
    curso = validar_curso_estruturado(resposta(formato=grafia))

    assert curso.formato is esperado
    assert curso.to_canonical_dict()["formato"] == esperado.value


def test_formato_desconhecido_e_recusado() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(formato="semipresencial"))


def test_curso_validado_nao_pode_ser_editado_no_lugar() -> None:
    """Revisao humana gera nova versao do artefato, nao altera a existente (RF14, RNF09)."""

    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    with pytest.raises(ValueError):
        curso.tema = "outro tema"  # type: ignore[misc]


def test_schema_json_declara_campos_obrigatoriedades_e_forma_fechada() -> None:
    schema = schema_do_curso_estruturado()

    assert schema["additionalProperties"] is False
    assert tuple(schema["properties"]) == CHAVES_CANONICAS
    assert set(schema["required"]) == set(CHAVES_OBRIGATORIAS)
    assert schema["$defs"]["SyllabusModule"]["additionalProperties"] is False
    assert schema["$defs"]["FieldGap"]["additionalProperties"] is False


def test_schema_json_declara_a_lacuna_classificada_de_campos_ausentes() -> None:
    """A classificacao faz parte do contrato de saida (RNF03, RF15.1)."""

    schema = schema_do_curso_estruturado()

    assert schema["properties"]["campos_ausentes"]["items"] == {"$ref": "#/$defs/FieldGap"}
    assert tuple(schema["$defs"]["FieldGap"]["properties"]) == ("campo", "tipo", "motivo")
    assert schema["$defs"]["GapKind"]["enum"] == ["ausente", "ambigua", "contraditoria"]


def test_curso_pode_ser_construido_em_codigo_com_a_mesma_forma() -> None:
    curso = StructuredCourse(
        tema="Lideranca para coordenadores",
        publico_alvo="Coordenadores promovidos no ano corrente",
        carga_horaria=None,
        objetivos_aprendizagem=[],
        ementa=[],
        campos_ausentes=["carga_horaria", "objetivos_aprendizagem"],
        observacoes=[],
    )

    assert tuple(curso.to_canonical_dict()) == CHAVES_CANONICAS
    assert curso.nomes_dos_campos_ausentes == ("carga_horaria", "objetivos_aprendizagem", "ementa")
