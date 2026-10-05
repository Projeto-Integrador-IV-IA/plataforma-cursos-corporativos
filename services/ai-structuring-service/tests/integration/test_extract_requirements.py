"""Prompt de extracao executado ponta a ponta sobre dois textos de exemplo (RF13).

O provedor e o selecionado por ``LLM_PROVIDER``; nos testes, o mock - sem chave,
sem rede e sem custo (RNF12). O que se verifica aqui e o caminho completo
"prompt versionado -> provedor -> objeto JSON com os cinco campos".

A qualidade da extracao feita por um modelo real e outro assunto: e medida
sobre o conjunto de avaliacao anotado (RNF04), na PoC da Fase 2.
"""

import json

import pytest

from app.prompts import carregar_prompt
from app.providers import MockLLMProvider
from app.providers.base import CompletionParams

CINCO_CAMPOS = ("tema", "publico_alvo", "carga_horaria", "ementa", "objetivos_aprendizagem")

EMAIL_COLADO = """
De: [contato do cliente]
Assunto: ENC: treinamento pra equipe de manutencao

Boa tarde, tudo bem?

Conforme conversamos, precisamos de um treinamento de NR-12 para o pessoal da manutencao da
planta 2, uns 25 tecnicos. A ideia e fazer em dois dias de 8 horas, no proprio site.

Fico no aguardo da proposta.
"""

TRANSCRICAO_WHATSAPP = """
[10:02] oi! seguinte, a diretoria pediu um treinamento de lideranca pros coordenadores novos
[10:02] sao 12 pessoas que foram promovidas esse ano
[10:03] eles querem falar de feedback, gestao de conflito e como conduzir reuniao de equipe
[10:05] a gente ainda nao fechou quantas horas, depende do orcamento
"""

TEXTOS_DE_EXEMPLO = pytest.mark.parametrize(
    ("rotulo", "texto"),
    [("e-mail colado", EMAIL_COLADO), ("transcricao de whatsapp", TRANSCRICAO_WHATSAPP)],
)


@TEXTOS_DE_EXEMPLO
async def test_execucao_devolve_os_cinco_campos(rotulo: str, texto: str) -> None:
    prompt = carregar_prompt("extract-requirements", "v1")

    resultado = await MockLLMProvider().complete(
        prompt.render(texto_normalizado=texto),
        CompletionParams(temperature=0.0),
    )
    curso = json.loads(resultado.text)

    for campo in CINCO_CAMPOS:
        assert campo in curso, f"{rotulo}: campo {campo} ausente na saida"
    assert curso["campos_ausentes"] is not None
    assert curso["observacoes"] is not None


@TEXTOS_DE_EXEMPLO
async def test_texto_da_demanda_chega_integro_ao_provedor(rotulo: str, texto: str) -> None:
    prompt = carregar_prompt("extract-requirements", "v1")
    provider = MockLLMProvider()

    enviado = prompt.render(texto_normalizado=texto)
    await provider.complete(enviado)

    assert texto.strip() in enviado, rotulo
    assert "Nunca invente" in enviado


@TEXTOS_DE_EXEMPLO
async def test_execucao_registra_proveniencia_do_prompt_e_do_modelo(
    rotulo: str,
    texto: str,
) -> None:
    """Modelo, versao de prompt, tokens e latencia acompanham o artefato (RNF04, RNF09)."""

    prompt = carregar_prompt("extract-requirements", "v1")

    resultado = await MockLLMProvider().complete(prompt.render(texto_normalizado=texto))

    assert prompt.identificador == "extract-requirements.v1"
    assert resultado.model
    assert resultado.usage.total_tokens > 0
    assert resultado.latency_ms >= 0
