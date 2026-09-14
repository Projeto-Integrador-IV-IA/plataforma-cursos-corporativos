"""Provedor falso, para desenvolvimento e testes.

Devolve saidas fixas e validas segundo o schema, sem chamar API externa.

Serve para: rodar a CI sem chave e sem custo (RNF12), testar o caminho de erro
e de timeout de forma deterministica (RNF05), e permitir que frontend e backend
avancem sem depender do provedor real.

Selecionado por ``LLM_PROVIDER=mock`` - o padrao em desenvolvimento.

A resposta fixa segue a forma canonica do curso estruturado descrita em
``app.domain.course``: campos extraidos (RF11), campos gerados (RF12) e os
metadados de confianca. Enquanto
``packages/contracts/schemas/structured-course.schema.json`` for um esqueleto,
e esta forma que serve de referencia para a fatia vertical da pre-banca.

O provedor nao inventa nada a partir do prompt: a saida e sempre a mesma, para
que qualquer medicao ou teste seja reproduzivel.
"""

import json
import time
from typing import ClassVar, Final

from app.core.exceptions import LLMProviderError
from app.providers.base import (
    CompletionParams,
    CompletionResult,
    CompletionUsage,
    LLMProvider,
)

#: Curso estruturado devolvido pelo mock. Dado ficticio - nenhum cliente real (RNF10).
RESPOSTA_FIXA: Final[dict[str, object]] = {
    "tema": "Seguranca do trabalho em ambiente industrial",
    "nicho": "Industria metalurgica",
    "publico_alvo": "Operadores de chao de fabrica e lideres de turno",
    "numero_participantes": 40,
    "carga_horaria": 16,
    "formato": "presencial",
    "objetivos_aprendizagem": [
        "Identificar riscos ocupacionais tipicos da operacao metalurgica",
        "Aplicar o procedimento de bloqueio e etiquetagem antes da manutencao",
        "Reagir a um incidente seguindo o plano de emergencia da planta",
    ],
    "ementa": [
        {
            "titulo": "Fundamentos de seguranca ocupacional",
            "topicos": ["Normas aplicaveis", "Mapa de riscos", "Equipamentos de protecao"],
            "carga_horaria": 4,
        },
        {
            "titulo": "Riscos da operacao metalurgica",
            "topicos": ["Calor e ruido", "Movimentacao de carga", "Substancias perigosas"],
            "carga_horaria": 6,
        },
        {
            "titulo": "Resposta a incidentes",
            "topicos": ["Plano de emergencia", "Primeiros socorros", "Simulado pratico"],
            "carga_horaria": 6,
        },
    ],
    "campos_ausentes": ["orcamento"],
    "observacoes": [
        "Resposta gerada pelo provedor mock - nao houve chamada a nenhum modelo de linguagem.",
    ],
}


class MockLLMProvider(LLMProvider):
    """Provedor deterministico, sem rede e sem custo.

    Args:
        model: nome reportado nos metadados; util para distinguir execucoes.
        response_text: texto a devolver; por padrao, ``RESPOSTA_FIXA`` em JSON.
        fail_with: quando informado, toda chamada levanta esta falha em vez de
            responder. E assim que o caminho de erro e de timeout (RNF05) e
            exercitado sem depender do fornecedor real.
    """

    name: ClassVar[str] = "mock"

    def __init__(
        self,
        *,
        model: str = "mock",
        response_text: str | None = None,
        fail_with: LLMProviderError | None = None,
    ) -> None:
        self.model = model
        self.response_text = (
            response_text
            if response_text is not None
            else json.dumps(RESPOSTA_FIXA, ensure_ascii=False, indent=2)
        )
        self.fail_with = fail_with

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        """Devolve a resposta fixa com metadados de execucao verossimeis."""

        inicio = time.perf_counter()
        if self.fail_with is not None:
            raise self.fail_with

        text = self.response_text
        return CompletionResult(
            text=text,
            provider=self.name,
            model=(params.model if params else None) or self.model,
            usage=CompletionUsage(
                prompt_tokens=_tokens_aproximados(prompt),
                completion_tokens=_tokens_aproximados(text),
            ),
            latency_ms=(time.perf_counter() - inicio) * 1000,
            finish_reason="stop",
            metadata={"mock": True},
        )


def _tokens_aproximados(texto: str) -> int:
    """Estimativa grosseira de tokens (~4 caracteres por token).

    Nao pretende exatidao: existe para que a instrumentacao de custo (RNF12)
    tenha numero para exercitar mesmo sem provedor real.
    """

    return max(1, len(texto) // 4) if texto else 0
