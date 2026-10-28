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
    FieldOrigin,
    GapKind,
    StructuredCourse,
    _justificativa_do_descarte,
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
    "procedencia": {
        "tema": "extraido",
        "publico_alvo": "extraido",
        "carga_horaria": "inferido",
        "objetivos_aprendizagem": "extraido",
        "ementa": "inferido",
    },
    "evidencias": {
        "tema": [1],
        "publico_alvo": [1],
        "carga_horaria": [2],
        "objetivos_aprendizagem": [3],
        "ementa": [3],
    },
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


def test_tipo_da_lacuna_que_nem_e_texto_e_recusado() -> None:
    """Tipo fora de texto nao vira ``ausente`` por conveniencia: a resposta e recusada."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(carga_horaria=None, campos_ausentes=[{"campo": "carga_horaria", "tipo": 3}])
        )

    assert [v["campo"] for v in excinfo.value.details["violacoes"]] == ["campos_ausentes.0.tipo"]


def test_motivo_da_lacuna_que_nem_e_texto_e_recusado() -> None:
    """O motivo e a frase que o revisor le; estrutura no lugar dela e fora do contrato."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(
                carga_horaria=None,
                campos_ausentes=[{"campo": "carga_horaria", "motivo": ["adiado"]}],
            )
        )

    violacoes = [v["campo"] for v in excinfo.value.details["violacoes"]]
    assert any(campo.startswith("campos_ausentes.0.motivo") for campo in violacoes)


@pytest.mark.parametrize("registradas", ["carga_horaria: o cliente adiou.", [12]])
def test_observacoes_fora_do_tipo_declarado_e_recusado(registradas: Any) -> None:
    """Texto solto, ou item que nao e texto, nao serve de registro para o revisor.

    A reconciliacao segue classificando a lacuna, mas nao escreve em observacoes
    que nao tem a forma do contrato - e a validacao normal recusa a resposta.
    """

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(
                carga_horaria=None,
                campos_ausentes=["carga_horaria"],
                observacoes=registradas,
            )
        )

    violacoes = [v["campo"] for v in excinfo.value.details["violacoes"]]
    assert any(campo.startswith("observacoes") for campo in violacoes)


def test_descarte_sem_tipo_utilizavel_cai_na_explicacao_da_ausencia() -> None:
    """Caminho defensivo da justificativa, chamado direto porque a validacao o barra antes.

    Tipo que nem e texto faz a reconciliacao se afastar, entao a observacao de
    descarte nunca e escrita com ele. Mesmo assim nenhum descarte pode ficar sem
    explicacao para o revisor (RF14).
    """

    assert _justificativa_do_descarte(None) == _justificativa_do_descarte(GapKind.AUSENTE.value)


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


# ----------------------------------------------------------------------
# Card #11 (RNF06): procedencia do campo - extraido, inferido ou ausente
# ----------------------------------------------------------------------


def test_campo_extraido_e_distinguivel_de_campo_inferido_sem_consultar_a_fonte() -> None:
    """Criterio de aceite: a distincao e visivel so pelo resultado."""

    curso = validar_curso_estruturado(
        resposta(procedencia={**RESPOSTA_COMPLETA["procedencia"], "tema": "extraido"})
    )
    assert curso.procedencia["tema"] is FieldOrigin.EXTRAIDO

    curso = validar_curso_estruturado(
        resposta(procedencia={**RESPOSTA_COMPLETA["procedencia"], "tema": "inferido"})
    )
    assert curso.procedencia["tema"] is FieldOrigin.INFERIDO


def test_campo_preenchido_sem_procedencia_declarada_e_recusado() -> None:
    """Criterio de aceite: campo preenchido sem procedencia e falha de schema."""

    sem_tema = {k: v for k, v in RESPOSTA_COMPLETA["procedencia"].items() if k != "tema"}

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(procedencia=sem_tema))

    assert "tema" in str(excinfo.value.__cause__)


def test_resposta_sem_procedencia_alguma_e_recusada() -> None:
    """A chave toda pode faltar, nao so uma entrada dela."""

    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(procedencia={}))


def test_campo_preenchido_com_procedencia_mas_sem_evidencia_e_recusado() -> None:
    """Criterio de aceite (RF28): campo preenchido sem evidencia e falha de schema."""

    sem_tema = {k: v for k, v in RESPOSTA_COMPLETA["evidencias"].items() if k != "tema"}

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(resposta(evidencias=sem_tema))

    assert "tema" in str(excinfo.value.__cause__)


def test_campo_preenchido_com_lista_de_evidencia_vazia_e_recusado() -> None:
    """Lista vazia nao conta como citacao - precisa de ao menos um numero."""

    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(
            resposta(evidencias={**RESPOSTA_COMPLETA["evidencias"], "tema": []})
        )


def test_resposta_sem_evidencia_alguma_e_recusada() -> None:
    """A chave toda pode faltar, nao so uma entrada dela."""

    with pytest.raises(LLMInvalidResponseError):
        validar_curso_estruturado(resposta(evidencias={}))


def test_campo_ausente_ganha_procedencia_ausente_mesmo_sem_o_modelo_declarar() -> None:
    """Toda lacuna reconciliada tem procedencia ``ausente`` - a validacao completa, nao o modelo."""

    curso = validar_curso_estruturado(
        resposta(carga_horaria=None, observacoes=["carga_horaria: adiado pelo cliente."])
    )

    assert curso.procedencia["carga_horaria"] is FieldOrigin.AUSENTE
    assert curso.evidencias["carga_horaria"] == []


def test_procedencia_e_sobrescrita_quando_o_valor_e_descartado_por_lacuna_declarada() -> None:
    """Procedencia e evidencia de campo descartado nao podem sobreviver - mesma regra do valor."""

    curso = validar_curso_estruturado(
        resposta(
            campos_ausentes=[{"campo": "tema", "tipo": "ambigua", "motivo": "duas leituras"}],
            procedencia={**RESPOSTA_COMPLETA["procedencia"], "tema": "extraido"},
            evidencias={**RESPOSTA_COMPLETA["evidencias"], "tema": [1]},
        )
    )

    assert curso.tema is None
    assert curso.procedencia["tema"] is FieldOrigin.AUSENTE
    assert curso.evidencias["tema"] == []


def test_procedencia_vazia_quando_nenhum_campo_e_preenchido() -> None:
    curso = validar_curso_estruturado(
        resposta(
            tema=None,
            publico_alvo=None,
            carga_horaria=None,
            objetivos_aprendizagem=[],
            ementa=[],
            campos_ausentes=["tema", "publico_alvo", "carga_horaria"],
            procedencia={},
            evidencias={},
        )
    )

    campos_da_resposta = (
        "tema",
        "publico_alvo",
        "carga_horaria",
        "objetivos_aprendizagem",
        "ementa",
    )
    assert curso.procedencia == dict.fromkeys(campos_da_resposta, FieldOrigin.AUSENTE)
    assert curso.evidencias == {campo: [] for campo in campos_da_resposta}


@pytest.mark.parametrize(
    ("grafia", "esperado"),
    [
        ("extraido", FieldOrigin.EXTRAIDO),
        ("extraído", FieldOrigin.EXTRAIDO),
        ("EXTRAIDO", FieldOrigin.EXTRAIDO),
        (" Inferido ", FieldOrigin.INFERIDO),
    ],
)
def test_procedencia_e_normalizada_para_o_valor_canonico(
    grafia: str,
    esperado: FieldOrigin,
) -> None:
    curso = validar_curso_estruturado(
        resposta(procedencia={**RESPOSTA_COMPLETA["procedencia"], "tema": grafia})
    )

    assert curso.procedencia["tema"] is esperado


def test_procedencia_com_valor_fora_do_vocabulario_e_recusada() -> None:
    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(procedencia={**RESPOSTA_COMPLETA["procedencia"], "tema": "copiado"})
        )

    assert any(v["campo"] == "procedencia.tema" for v in excinfo.value.details["violacoes"])


def test_procedencia_com_valor_que_nem_e_texto_e_recusada() -> None:
    """Valor fora de texto nao vira grafia desconhecida por conveniencia: a resposta e recusada."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(procedencia={**RESPOSTA_COMPLETA["procedencia"], "tema": 3})
        )

    assert any(v["campo"] == "procedencia.tema" for v in excinfo.value.details["violacoes"])


def test_evidencia_com_numero_de_trecho_que_nao_e_inteiro_e_recusada() -> None:
    """Criterio de aceite (RF28): numero de trecho fora do tipo e falha de schema."""

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        validar_curso_estruturado(
            resposta(evidencias={**RESPOSTA_COMPLETA["evidencias"], "tema": ["um"]})
        )

    assert any(v["campo"].startswith("evidencias.tema") for v in excinfo.value.details["violacoes"])
