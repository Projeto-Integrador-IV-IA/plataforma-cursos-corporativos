"""Politica de campo nao inferivel na saida estruturada (RNF03).

RF14.2 no Documento Consolidado de Requisitos v1.0. O que se verifica aqui e a
regra que separa a plataforma de um gerador de texto: campo sem base no texto
vira ``null`` e e registrado em ``campos_ausentes``, com o motivo em
``observacoes`` - nenhum valor plausivel e preenchido por suposicao.
"""

from typing import Any

import pytest

from app.core.exceptions import LLMInvalidResponseError
from app.domain.course import (
    CAMPOS_INFERIVEIS,
    validar_curso_estruturado,
)

#: Resposta completa de referencia, sem nenhuma ausencia. Dado ficticio (RNF10).
RESPOSTA_COMPLETA: dict[str, Any] = {
    "tema": "NR-12 (seguranca em maquinas e equipamentos)",
    "publico_alvo": "Tecnicos de manutencao da planta 2",
    "carga_horaria": 16,
    "objetivos_aprendizagem": ["Aplicar o procedimento de bloqueio e etiquetagem"],
    "ementa": [
        {
            "titulo": "Fundamentos da NR-12",
            "topicos": ["Dispositivos de seguranca"],
            "carga_horaria": 8,
        }
    ],
    "campos_ausentes": [],
    "observacoes": [],
}


def resposta(**alteracoes: Any) -> dict[str, Any]:
    """Copia a resposta completa aplicando as alteracoes do caso de teste."""

    return {**RESPOSTA_COMPLETA, **alteracoes}


# ----------------------------------------------------------------------
# Criterio do card: entrada incompleta vira campo nulo e campo ausente
# ----------------------------------------------------------------------


def test_demanda_sem_carga_horaria_produz_nulo_e_entrada_em_campos_ausentes() -> None:
    """Criterio do card: a duracao que o cliente nao disse nao e arbitrada."""

    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            observacoes=["carga_horaria: o cliente adiou a definicao da duracao."],
        )
    )

    assert curso.carga_horaria is None
    assert "carga_horaria" in curso.campos_ausentes
    assert curso.to_canonical_dict()["carga_horaria"] is None


def test_campo_omitido_pelo_modelo_e_declarado_ausente_e_aceito() -> None:
    """A resposta real do modelo traz a chave nula e o nome ja na lista."""

    curso = validar_curso_estruturado(
        resposta(carga_horaria=None, campos_ausentes=["carga_horaria"])
    )

    assert curso.carga_horaria is None
    assert curso.campos_ausentes == ["carga_horaria"]


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_texto_em_branco_vira_nulo_e_entra_em_campos_ausentes(valor: str | None) -> None:
    curso = validar_curso_estruturado(resposta(publico_alvo=valor))

    assert curso.publico_alvo is None
    assert curso.campos_ausentes == ["publico_alvo"]


@pytest.mark.parametrize("campo", ["objetivos_aprendizagem", "ementa"])
def test_lista_vazia_entra_em_campos_ausentes(campo: str) -> None:
    curso = validar_curso_estruturado(resposta(**{campo: []}))

    assert curso.to_canonical_dict()[campo] == []
    assert curso.campos_ausentes == [campo]


def test_resposta_sem_informacao_nenhuma_nao_ganha_valor_plausivel() -> None:
    """Criterio do card: nenhum valor e preenchido sem base no texto."""

    vazia = dict.fromkeys(("tema", "publico_alvo", "carga_horaria"))
    curso = validar_curso_estruturado(
        {
            **vazia,
            "objetivos_aprendizagem": [],
            "ementa": [],
            "campos_ausentes": [],
            "observacoes": [],
        }
    )

    canonico = curso.to_canonical_dict()
    assert all(canonico[campo] in (None, []) for campo in CAMPOS_INFERIVEIS)
    assert curso.campos_ausentes == [
        "tema",
        "publico_alvo",
        "carga_horaria",
        "objetivos_aprendizagem",
        "ementa",
    ]


# ----------------------------------------------------------------------
# Reconciliacao: valor e ausencia nunca se contradizem
# ----------------------------------------------------------------------


def test_campo_preenchido_fica_fora_de_campos_ausentes() -> None:
    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.campos_ausentes == []


def test_valor_devolvido_para_campo_declarado_ausente_e_descartado() -> None:
    """O modelo disse que nao havia base: o valor que ele mesmo escreveu nao vale."""

    curso = validar_curso_estruturado(resposta(carga_horaria=8, campos_ausentes=["carga_horaria"]))

    assert curso.carga_horaria is None
    assert curso.campos_ausentes == ["carga_horaria"]


def test_descarte_de_valor_sem_base_fica_registrado_sem_repetir_o_valor() -> None:
    """A observacao explica o descarte; o valor recusado nao e repetido (RNF10)."""

    curso = validar_curso_estruturado(
        resposta(tema="Tema provavel do setor", campos_ausentes=["tema"])
    )

    assert curso.observacoes == [
        "tema: valor descartado na validacao - o modelo declarou o campo ausente "
        "e valor sem base no texto nao e aproveitado."
    ]
    assert all("Tema provavel do setor" not in nota for nota in curso.observacoes)


def test_zero_nao_e_ausencia_e_continua_sendo_valor_invalido() -> None:
    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(carga_horaria=0))

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["carga_horaria"]


def test_campos_ausentes_sai_sem_repeticao_e_em_ordem_canonica() -> None:
    curso = validar_curso_estruturado(
        resposta(
            tema=None,
            carga_horaria=None,
            campos_ausentes=["carga_horaria", "tema", "carga_horaria"],
        )
    )

    assert curso.campos_ausentes == ["tema", "carga_horaria"]


def test_nome_que_nao_e_campo_do_contrato_nao_chega_ao_revisor() -> None:
    """``orcamento`` esta fora do MVP: nome sem campo correspondente e descartado."""

    curso = validar_curso_estruturado(resposta(campos_ausentes=["orcamento"]))

    assert curso.campos_ausentes == []


def test_campo_opcional_que_o_prompt_ativo_nao_pede_nao_vira_campo_ausente() -> None:
    """Chave nao devolvida nao foi perguntada - nao e ausencia de informacao."""

    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.nicho is None
    assert "nicho" not in curso.campos_ausentes


def test_campo_opcional_devolvido_vazio_vira_campo_ausente() -> None:
    curso = validar_curso_estruturado(resposta(nicho="   "))

    assert curso.nicho is None
    assert curso.campos_ausentes == ["nicho"]


def test_campos_ausentes_fora_do_tipo_continua_sendo_recusado() -> None:
    """A reconciliacao nao pode mascarar resposta fora do contrato (ADR-0006)."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(campos_ausentes="carga_horaria"))

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["campos_ausentes"]


def test_campo_extra_continua_recusado_com_a_reconciliacao_ativa() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(orcamento="R$ 12.000", campos_ausentes=["tema"]))


# ----------------------------------------------------------------------
# Motivo da ausencia: o par campo -> motivo que a revisao humana mostra
# ----------------------------------------------------------------------


def test_motivos_dos_campos_ausentes_pareia_campo_e_motivo() -> None:
    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            objetivos_aprendizagem=[],
            observacoes=[
                "carga_horaria: o cliente adiou a definicao ('depende do orcamento').",
                "objetivos_aprendizagem: o cliente nao declarou o que o participante deve saber.",
                "Observacao geral que nao nomeia campo nenhum.",
            ],
        )
    )

    assert curso.motivos_dos_campos_ausentes() == {
        "carga_horaria": "o cliente adiou a definicao ('depende do orcamento').",
        "objetivos_aprendizagem": ("o cliente nao declarou o que o participante deve saber."),
    }


def test_campo_ausente_sem_motivo_registrado_continua_visivel() -> None:
    """Ausencia sem explicacao aparece com motivo nulo, nao some da revisao."""

    curso = validar_curso_estruturado(resposta(carga_horaria=None, observacoes=[]))

    assert curso.motivos_dos_campos_ausentes() == {"carga_horaria": None}


def test_curso_sem_ausencia_nao_tem_motivo_a_mostrar() -> None:
    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.motivos_dos_campos_ausentes() == {}
