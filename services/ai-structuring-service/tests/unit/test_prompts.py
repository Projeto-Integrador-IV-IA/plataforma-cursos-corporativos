"""Testes do catalogo de prompts versionados (RF13, RNF03)."""

import re

import pytest

from app.prompts import PROMPTS_DIR, carregar_prompt, listar_prompts

CINCO_CAMPOS = ("tema", "publico_alvo", "carga_horaria", "ementa", "objetivos_aprendizagem")


def test_prompt_e_carregado_por_nome_e_versao() -> None:
    prompt = carregar_prompt("extract-requirements", "v1")

    assert prompt.nome == "extract-requirements"
    assert prompt.versao == "v1"
    assert prompt.identificador == "extract-requirements.v1"


def test_prompt_vive_em_arquivo_versionado_no_catalogo() -> None:
    assert (PROMPTS_DIR / "extract-requirements.v1.md").is_file()
    assert ("extract-requirements", "v1") in listar_prompts()


def test_metadados_do_arquivo_sao_lidos() -> None:
    metadados = carregar_prompt("extract-requirements", "v1").metadados

    assert metadados["versao"] == "1"
    assert metadados["requisito"] == "RF13"
    assert metadados["status"] == "ativo"


def test_corpo_declara_apenas_a_variavel_do_texto_normalizado() -> None:
    assert carregar_prompt("extract-requirements", "v1").variaveis == {"texto_normalizado"}


def test_render_substitui_a_variavel_e_nao_deixa_marcador() -> None:
    prompt = carregar_prompt("extract-requirements", "v1")

    texto = prompt.render(texto_normalizado="Precisamos de um treinamento de NR-12.")

    assert "Precisamos de um treinamento de NR-12." in texto
    assert "{{texto_normalizado}}" not in texto
    assert "{{" not in texto


def test_render_sem_a_variavel_exigida_falha() -> None:
    prompt = carregar_prompt("extract-requirements", "v1")

    with pytest.raises(ValueError, match="faltam variaveis"):
        prompt.render()


def test_render_com_variavel_desconhecida_falha() -> None:
    prompt = carregar_prompt("extract-requirements", "v1")

    with pytest.raises(ValueError, match="desconhecidas"):
        prompt.render(texto_normalizado="ok", tema="lideranca")


def test_versao_inexistente_falha_listando_o_catalogo() -> None:
    with pytest.raises(ValueError, match=re.escape("extract-requirements.v1")):
        carregar_prompt("extract-requirements", "v99")


def test_prompt_inexistente_falha() -> None:
    with pytest.raises(ValueError, match="nao existe no catalogo"):
        carregar_prompt("prompt-que-nao-existe", "v1")


@pytest.mark.parametrize("versao", ["1", "v", "V1", "v1.2", "../v1"])
def test_versao_fora_do_formato_e_recusada(versao: str) -> None:
    with pytest.raises(ValueError, match="Versao de prompt invalida"):
        carregar_prompt("extract-requirements", versao)


@pytest.mark.parametrize("nome", ["../core/config", "Extract-Requirements", "extract_requirements"])
def test_nome_fora_do_formato_e_recusado(nome: str) -> None:
    with pytest.raises(ValueError, match="Nome de prompt invalido"):
        carregar_prompt(nome, "v1")


def test_catalogo_nao_expoe_arquivo_fora_da_convencao() -> None:
    for nome, versao in listar_prompts():
        assert (PROMPTS_DIR / f"{nome}.{versao}.md").is_file()


# ----------------------------------------------------------------------
# Conteudo do prompt: o que o card exige que esteja escrito nele
# ----------------------------------------------------------------------


@pytest.fixture
def corpo() -> str:
    return carregar_prompt("extract-requirements", "v1").corpo


@pytest.mark.parametrize("campo", CINCO_CAMPOS)
def test_prompt_pede_os_cinco_campos_pedagogicos(corpo: str, campo: str) -> None:
    assert campo in corpo


def test_prompt_proibe_inventar_campo_sem_base_no_texto(corpo: str) -> None:
    """A instrucao de nao inventar precisa estar explicita no texto (RF14)."""

    assert "Nunca invente" in corpo
    assert "campos_ausentes" in corpo
    assert "invenção é erro mais grave do que campo vazio" in corpo


def test_prompt_exige_resposta_exclusivamente_em_json(corpo: str) -> None:
    assert "exclusivamente com um objeto JSON" in corpo
    assert "sem nenhum texto antes ou depois" in corpo


def test_prompt_documenta_quando_cada_campo_fica_ausente(corpo: str) -> None:
    assert "Quando fica ausente" in corpo
    assert "sempre" in corpo
