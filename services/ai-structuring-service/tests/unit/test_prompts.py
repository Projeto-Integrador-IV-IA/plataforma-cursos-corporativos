"""Testes do catalogo de prompts versionados (RF13, RNF03)."""

import re

import pytest

from app.prompts import PROMPTS_DIR, carregar_prompt, listar_prompts
from app.services.structuring_service import (
    DEFAULT_PROMPT_VERSION,
    EXTRACTION_PROMPT_NAME,
)

CINCO_CAMPOS = ("tema", "publico_alvo", "carga_horaria", "ementa", "objetivos_aprendizagem")


def test_prompt_e_carregado_por_nome_e_versao() -> None:
    prompt = carregar_prompt("extract-requirements", "v1")

    assert prompt.nome == "extract-requirements"
    assert prompt.versao == "v1"
    assert prompt.identificador == "extract-requirements.v1"


def test_prompt_vive_em_arquivo_versionado_no_catalogo() -> None:
    for versao in ("v1", "v2", "v3"):
        assert (PROMPTS_DIR / f"extract-requirements.{versao}.md").is_file()
        assert ("extract-requirements", versao) in listar_prompts()


def test_metadados_do_arquivo_sao_lidos() -> None:
    metadados = carregar_prompt("extract-requirements", "v3").metadados

    assert metadados["versao"] == "3"
    assert metadados["requisito"] == "RF13"
    assert metadados["status"] == "ativo"


@pytest.mark.parametrize(
    ("versao", "sucessora"),
    [("v1", "extract-requirements.v2"), ("v2", "extract-requirements.v3")],
)
def test_versao_anterior_fica_no_catalogo_marcada_como_substituida(
    versao: str,
    sucessora: str,
) -> None:
    """Prompt nao e editado no lugar: a versao antiga continua legivel (RNF04)."""

    metadados = carregar_prompt("extract-requirements", versao).metadados

    assert metadados["status"] == "substituido"
    assert metadados["substituido_por"] == sucessora


def test_so_uma_versao_do_prompt_de_extracao_esta_ativa() -> None:
    """Duas versoes ativas deixariam ambiguo o que a medicao reproduz (RNF04)."""

    ativas = [
        versao
        for nome, versao in listar_prompts()
        if nome == "extract-requirements"
        and carregar_prompt(nome, versao).metadados.get("status") == "ativo"
    ]

    assert ativas == [DEFAULT_PROMPT_VERSION]


def test_corpo_declara_apenas_a_variavel_do_texto_normalizado() -> None:
    assert carregar_prompt("extract-requirements", "v3").variaveis == {"texto_normalizado"}


def test_render_substitui_a_variavel_e_nao_deixa_marcador() -> None:
    prompt = carregar_prompt("extract-requirements", "v3")

    texto = prompt.render(texto_normalizado="Precisamos de um treinamento de NR-12.")

    assert "Precisamos de um treinamento de NR-12." in texto
    assert "{{texto_normalizado}}" not in texto
    assert "{{" not in texto


def test_render_sem_a_variavel_exigida_falha() -> None:
    prompt = carregar_prompt("extract-requirements", "v3")

    with pytest.raises(ValueError, match="faltam variaveis"):
        prompt.render()


def test_render_com_variavel_desconhecida_falha() -> None:
    prompt = carregar_prompt("extract-requirements", "v3")

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
    return carregar_prompt("extract-requirements", "v3").corpo


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


def test_prompt_proibe_o_valor_plausivel_em_vez_da_ausencia(corpo: str) -> None:
    """RF14.2 no Documento Consolidado v1.0: suposicao razoavel tambem e invencao."""

    assert "Política de campo não inferível" in corpo
    assert 'Não existe "chute razoável"' in corpo
    assert '`0`, `"não informado"`, `"a definir"`' in corpo


def test_prompt_exige_motivo_para_cada_campo_ausente(corpo: str) -> None:
    assert "Toda lacuna tem tipo e motivo" in corpo
    assert '"motivo": "string"' in corpo


@pytest.mark.parametrize("tipo", ["ausente", "ambigua", "contraditoria"])
def test_prompt_declara_os_tres_tipos_de_lacuna(corpo: str, tipo: str) -> None:
    """RF15.1 no Documento Consolidado v1.0: a lacuna sai classificada."""

    assert "Classificação da lacuna" in corpo
    assert f"`{tipo}`" in corpo


def test_prompt_instrui_a_deteccao_de_contradicao_entre_trechos_da_mesma_fonte(
    corpo: str,
) -> None:
    assert "Como detectar contradição" in corpo
    assert "compare o que" in corpo
    assert "trechos diferentes dizem sobre o mesmo campo" in corpo


def test_prompt_proibe_resolver_a_contradicao_escolhendo_um_dos_trechos(corpo: str) -> None:
    """Escolher entre dois trechos em conflito e decisao do revisor (RF14)."""

    assert 'não** "a informação mais recente"' in corpo
    assert "a contradição **não** foi resolvida" in corpo


def test_prompt_traz_exemplo_de_fonte_contraditoria(corpo: str) -> None:
    assert "com a fonte se contradizendo" in corpo
    assert '"tipo": "contraditoria"' in corpo


def test_prompt_proibe_preencher_e_declarar_ausente_o_mesmo_campo(corpo: str) -> None:
    assert "Nunca preencha e declare ausente o mesmo campo" in corpo


def test_prompt_traz_exemplo_em_que_quase_nada_e_inferivel(corpo: str) -> None:
    """O exemplo e o que ensina o modelo a devolver objeto vazio sem constrangimento."""

    assert "quase nada é inferível" in corpo
    assert '"tema": null' in corpo


def test_o_caso_de_uso_carrega_a_versao_ativa_do_catalogo() -> None:
    """Prompt marcado ativo que ninguem carrega nao vale nada.

    Publicar uma versao nova sem mover ``DEFAULT_PROMPT_VERSION`` deixaria a
    politica nova escrita no catalogo e ausente da API. Este teste transforma
    esse descompasso em falha, em vez de bug silencioso em producao.
    """

    padrao = carregar_prompt(EXTRACTION_PROMPT_NAME, DEFAULT_PROMPT_VERSION)

    assert padrao.metadados["status"] == "ativo"
