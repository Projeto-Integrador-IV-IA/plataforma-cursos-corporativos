"""Politica de campo nao inferivel e classificacao da lacuna (RNF03).

RF14.2 e RF15.1 no Documento Consolidado de Requisitos v1.0. O que se verifica
aqui e a regra que separa a plataforma de um gerador de texto - campo sem valor
utilizavel no texto vira ``null`` e e apontado em ``campos_ausentes``, nenhum
valor plausivel e preenchido por suposicao - e o apontamento que fecha o ciclo
com o humano: cada lacuna sai classificada (``ausente``, ``ambigua`` ou
``contraditoria``) e com o motivo que o revisor le (RF14).
"""

from typing import Any

import pytest

from app.core.exceptions import LLMInvalidResponseError
from app.domain.course import (
    CAMPOS_INFERIVEIS,
    GapKind,
    StructuredCourse,
    validar_curso_estruturado,
)

#: Resposta completa de referencia, sem nenhuma lacuna. Dado ficticio (RNF10).
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


def nomes(curso: StructuredCourse) -> list[str]:
    """Nomes dos campos apontados, na ordem em que saem."""

    return list(curso.nomes_dos_campos_ausentes)


def tipos(curso: StructuredCourse) -> dict[str, GapKind]:
    """Tipo da lacuna de cada campo apontado."""

    return {lacuna.campo: lacuna.tipo for lacuna in curso.campos_ausentes}


# ----------------------------------------------------------------------
# Criterio do card #8: entrada incompleta vira campo nulo e campo ausente
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
    assert "carga_horaria" in nomes(curso)
    assert curso.to_canonical_dict()["carga_horaria"] is None


def test_campo_omitido_pelo_modelo_e_declarado_ausente_e_aceito() -> None:
    """A resposta real do modelo traz a chave nula e o campo ja apontado."""

    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            campos_ausentes=[
                {
                    "campo": "carga_horaria",
                    "tipo": "ausente",
                    "motivo": "o texto nao menciona duracao.",
                }
            ],
        )
    )

    assert curso.carga_horaria is None
    assert nomes(curso) == ["carga_horaria"]


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_texto_em_branco_vira_nulo_e_entra_em_campos_ausentes(valor: str | None) -> None:
    curso = validar_curso_estruturado(resposta(publico_alvo=valor))

    assert curso.publico_alvo is None
    assert nomes(curso) == ["publico_alvo"]


@pytest.mark.parametrize("campo", ["objetivos_aprendizagem", "ementa"])
def test_lista_vazia_entra_em_campos_ausentes(campo: str) -> None:
    curso = validar_curso_estruturado(resposta(**{campo: []}))

    assert curso.to_canonical_dict()[campo] == []
    assert nomes(curso) == [campo]


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
    assert nomes(curso) == [
        "tema",
        "publico_alvo",
        "carga_horaria",
        "objetivos_aprendizagem",
        "ementa",
    ]


# ----------------------------------------------------------------------
# Reconciliacao: valor e lacuna nunca se contradizem
# ----------------------------------------------------------------------


def test_campo_preenchido_fica_fora_de_campos_ausentes() -> None:
    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.campos_ausentes == []


def test_valor_devolvido_para_campo_declarado_ausente_e_descartado() -> None:
    """O modelo disse que nao havia base: o valor que ele mesmo escreveu nao vale."""

    curso = validar_curso_estruturado(
        resposta(carga_horaria=8, campos_ausentes=[{"campo": "carga_horaria"}])
    )

    assert curso.carga_horaria is None
    assert nomes(curso) == ["carga_horaria"]


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


def test_descarte_de_valor_com_lacuna_contraditoria_explica_que_a_escolha_e_do_revisor() -> None:
    """Entre dois trechos em conflito quem escolhe e o humano, nao a validacao (RF14)."""

    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=16,
            campos_ausentes=[{"campo": "carga_horaria", "tipo": "contraditoria"}],
        )
    )

    assert curso.carga_horaria is None
    assert curso.observacoes == [
        "carga_horaria: valor descartado na validacao - o modelo declarou a informacao "
        "contraditoria na fonte e escolher entre os trechos em conflito cabe ao revisor."
    ]


def test_zero_nao_e_ausencia_e_continua_sendo_valor_invalido() -> None:
    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(carga_horaria=0))

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["carga_horaria"]


def test_campos_ausentes_sai_sem_repeticao_e_em_ordem_canonica() -> None:
    curso = validar_curso_estruturado(
        resposta(
            tema=None,
            carga_horaria=None,
            campos_ausentes=[
                {"campo": "carga_horaria", "tipo": "contraditoria"},
                {"campo": "tema"},
                {"campo": "carga_horaria", "tipo": "ausente"},
            ],
        )
    )

    assert nomes(curso) == ["tema", "carga_horaria"]
    assert tipos(curso)["carga_horaria"] is GapKind.CONTRADITORIA


def test_nome_que_nao_e_campo_do_contrato_nao_chega_ao_revisor() -> None:
    """``orcamento`` esta fora do MVP: nome sem campo correspondente e descartado."""

    curso = validar_curso_estruturado(resposta(campos_ausentes=[{"campo": "orcamento"}]))

    assert curso.campos_ausentes == []


def test_campo_opcional_que_o_prompt_ativo_nao_pede_nao_vira_campo_ausente() -> None:
    """Chave nao devolvida nao foi perguntada - nao e ausencia de informacao."""

    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.nicho is None
    assert "nicho" not in nomes(curso)


def test_campo_opcional_devolvido_vazio_vira_campo_ausente() -> None:
    curso = validar_curso_estruturado(resposta(nicho="   "))

    assert curso.nicho is None
    assert nomes(curso) == ["nicho"]


def test_campos_ausentes_fora_do_tipo_continua_sendo_recusado() -> None:
    """A reconciliacao nao pode mascarar resposta fora do contrato (ADR-0006)."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(campos_ausentes="carga_horaria"))

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["campos_ausentes"]


def test_campo_extra_continua_recusado_com_a_reconciliacao_ativa() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(orcamento="R$ 12.000", campos_ausentes=["tema"]))


# ----------------------------------------------------------------------
# Criterio do card #12: a lacuna sai classificada, com motivo
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("declarado", "esperado"),
    [
        ("ausente", GapKind.AUSENTE),
        ("ambigua", GapKind.AMBIGUA),
        ("ambígua", GapKind.AMBIGUA),
        ("contraditoria", GapKind.CONTRADITORIA),
        ("Contraditória", GapKind.CONTRADITORIA),
        ("  AMBIGUA  ", GapKind.AMBIGUA),
    ],
)
def test_tipo_da_lacuna_e_normalizado_para_o_valor_canonico(
    declarado: str,
    esperado: GapKind,
) -> None:
    """O modelo escreve em portugues corrente; o dominio guarda um valor so."""

    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            campos_ausentes=[{"campo": "carga_horaria", "tipo": declarado}],
        )
    )

    assert tipos(curso) == {"carga_horaria": esperado}


def test_os_tres_tipos_de_lacuna_chegam_classificados_com_motivo() -> None:
    """Criterio do card: ausente, ambigua e contraditoria, cada uma com observacao."""

    curso = validar_curso_estruturado(
        resposta(
            tema=None,
            publico_alvo=None,
            carga_horaria=None,
            campos_ausentes=[
                {
                    "campo": "tema",
                    "tipo": "ausente",
                    "motivo": "a mensagem nao diz sobre o que e o treinamento.",
                },
                {
                    "campo": "publico_alvo",
                    "tipo": "ambigua",
                    "motivo": "'treinar a lideranca' nao diz se inclui coordenadores.",
                },
                {
                    "campo": "carga_horaria",
                    "tipo": "contraditoria",
                    "motivo": "um trecho diz 8 horas e outro diz 16 horas.",
                },
            ],
        )
    )

    assert tipos(curso) == {
        "tema": GapKind.AUSENTE,
        "publico_alvo": GapKind.AMBIGUA,
        "carga_horaria": GapKind.CONTRADITORIA,
    }
    assert all(lacuna.motivo for lacuna in curso.campos_ausentes)


def test_fonte_contraditoria_produz_apontamento_do_tipo_correspondente() -> None:
    """Criterio do card: trechos em conflito viram lacuna contraditoria, nao um palpite."""

    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            campos_ausentes=[
                {
                    "campo": "carga_horaria",
                    "tipo": "contraditoria",
                    "motivo": (
                        "a manutencao diz '8 horas, num sabado so' e a seguranca do trabalho "
                        "diz '16 horas, dois dias'."
                    ),
                }
            ],
        )
    )

    (lacuna,) = curso.lacunas_por_tipo(GapKind.CONTRADITORIA)
    assert lacuna.campo == "carga_horaria"
    assert curso.carga_horaria is None
    assert "8 horas" in (lacuna.motivo or "") and "16 horas" in (lacuna.motivo or "")


def test_lacunas_por_tipo_separa_o_que_perguntar_do_que_confrontar() -> None:
    curso = validar_curso_estruturado(
        resposta(
            tema=None,
            publico_alvo=None,
            carga_horaria=None,
            campos_ausentes=[
                {"campo": "publico_alvo", "tipo": "ambigua"},
                {"campo": "carga_horaria", "tipo": "contraditoria"},
            ],
        )
    )

    assert [lacuna.campo for lacuna in curso.lacunas_por_tipo(GapKind.AUSENTE)] == ["tema"]
    assert [lacuna.campo for lacuna in curso.lacunas_por_tipo(GapKind.AMBIGUA)] == ["publico_alvo"]
    assert [lacuna.campo for lacuna in curso.lacunas_por_tipo(GapKind.CONTRADITORIA)] == [
        "carga_horaria"
    ]


def test_lacuna_sem_tipo_declarado_vale_como_ausencia() -> None:
    """Ausencia e o caso comum: o modelo so precisa se manifestar quando e outro."""

    curso = validar_curso_estruturado(
        resposta(carga_horaria=None, campos_ausentes=[{"campo": "carga_horaria"}])
    )

    assert tipos(curso) == {"carga_horaria": GapKind.AUSENTE}


def test_campo_vazio_que_o_modelo_nem_declarou_vira_lacuna_ausente() -> None:
    curso = validar_curso_estruturado(resposta(tema=None, campos_ausentes=[]))

    assert tipos(curso) == {"tema": GapKind.AUSENTE}


def test_tipo_de_lacuna_desconhecido_e_recusado() -> None:
    """Classificacao fora das tres e resposta fora do contrato (ADR-0006)."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(
                carga_horaria=None,
                campos_ausentes=[{"campo": "carga_horaria", "tipo": "duvidosa"}],
            )
        )

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["campos_ausentes.0.tipo"]


def test_lacuna_com_chave_fora_do_contrato_e_recusada() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(
            resposta(
                carga_horaria=None,
                campos_ausentes=[{"campo": "carga_horaria", "gravidade": "alta"}],
            )
        )


def test_lacuna_sem_nome_de_campo_e_recusada() -> None:
    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(
            resposta(carga_horaria=None, campos_ausentes=[{"tipo": "ausente"}])
        )


# ----------------------------------------------------------------------
# Motivo da lacuna: o par campo -> motivo que a revisao humana mostra
# ----------------------------------------------------------------------


def test_motivos_dos_campos_ausentes_pareia_campo_e_motivo() -> None:
    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            objetivos_aprendizagem=[],
            campos_ausentes=[
                {
                    "campo": "carga_horaria",
                    "tipo": "ausente",
                    "motivo": "o cliente adiou a definicao ('depende do orcamento').",
                },
                {
                    "campo": "objetivos_aprendizagem",
                    "tipo": "ausente",
                    "motivo": "o cliente nao declarou o que o participante deve saber.",
                },
            ],
            observacoes=["Observacao geral que nao nomeia campo nenhum."],
        )
    )

    assert curso.motivos_dos_campos_ausentes() == {
        "carga_horaria": "o cliente adiou a definicao ('depende do orcamento').",
        "objetivos_aprendizagem": "o cliente nao declarou o que o participante deve saber.",
    }


def test_campo_ausente_sem_motivo_registrado_continua_visivel() -> None:
    """Lacuna sem explicacao aparece com motivo nulo, nao some da revisao."""

    curso = validar_curso_estruturado(resposta(carga_horaria=None, observacoes=[]))

    assert curso.motivos_dos_campos_ausentes() == {"carga_horaria": None}


def test_motivo_em_branco_vale_como_motivo_nao_registrado() -> None:
    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            campos_ausentes=[{"campo": "carga_horaria", "motivo": "   "}],
        )
    )

    assert curso.motivos_dos_campos_ausentes() == {"carga_horaria": None}


def test_curso_sem_ausencia_nao_tem_motivo_a_mostrar() -> None:
    curso = validar_curso_estruturado(RESPOSTA_COMPLETA)

    assert curso.motivos_dos_campos_ausentes() == {}


# ----------------------------------------------------------------------
# Compatibilidade com a extract-requirements.v2, que ainda vale medicao (RNF04)
# ----------------------------------------------------------------------


def test_nome_solto_da_versao_anterior_vira_lacuna_ausente() -> None:
    """A v2 devolve so o nome do campo; a saida canonica continua sendo a rica."""

    curso = validar_curso_estruturado(
        resposta(carga_horaria=None, campos_ausentes=["carga_horaria"])
    )

    assert curso.to_canonical_dict()["campos_ausentes"] == [
        {"campo": "carga_horaria", "tipo": "ausente", "motivo": None}
    ]


def test_motivo_da_versao_anterior_e_lido_das_observacoes() -> None:
    """Na v2 o motivo vem em ``observacoes``, no formato ``campo: motivo``."""

    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            campos_ausentes=["carga_horaria"],
            observacoes=["carga_horaria: o cliente adiou a definicao da duracao."],
        )
    )

    assert curso.motivos_dos_campos_ausentes() == {
        "carga_horaria": "o cliente adiou a definicao da duracao."
    }


def test_motivo_declarado_na_lacuna_vence_o_das_observacoes() -> None:
    curso = validar_curso_estruturado(
        resposta(
            carga_horaria=None,
            campos_ausentes=[{"campo": "carga_horaria", "motivo": "motivo do apontamento."}],
            observacoes=["carga_horaria: linha antiga da versao anterior."],
        )
    )

    assert curso.motivos_dos_campos_ausentes() == {"carga_horaria": "motivo do apontamento."}


def test_observacao_de_descarte_nao_vira_motivo_da_lacuna() -> None:
    """O motivo e o que o modelo explicou, nao o registro que a validacao acrescentou."""

    curso = validar_curso_estruturado(resposta(tema="Tema provavel", campos_ausentes=["tema"]))

    assert curso.motivos_dos_campos_ausentes() == {"tema": None}
