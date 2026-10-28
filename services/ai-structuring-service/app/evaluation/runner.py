"""Execucao do conjunto de avaliacao contra varios modelos (RNF04, card #217).

Roda as mesmas entradas por todos os modelos do catalogo e guarda a saida bruta
de cada chamada. Duas decisoes sustentam o resto:

**Mede o pipeline real, nao uma copia dele.** O executor chama
``StructuringService.structure_course``, o mesmo caso de uso que a rota
``POST /api/v1/structuring`` expoe. Prompt versionado, politica de retentativa
e barreira de schema entram na medicao porque entram em producao. Reimplementar
o fluxo aqui mediria outra coisa.

**Persiste a saida bruta antes de calcular qualquer metrica.** Chamada de LLM
custa dinheiro e tempo; reanalise nao pode exigir nova rodada. O arquivo de
resultados e a fonte das metricas, e a execucao e retomavel: caso que ja tem
resultado gravado nao e chamado de novo, salvo pedido explicito.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.domain.course import SCHEMA_VERSION
from app.evaluation.catalog import ModeloCandidato
from app.evaluation.dataset import CasoDeAvaliacao
from app.evaluation.metrics import Execucao
from app.providers.base import LLMProvider
from app.services.structuring_service import RawDemand, StructuringService

#: Assinatura da fabrica de provedor. Recebe o slug do modelo e devolve algo que
#: cumpre ``LLMProvider`` - e o ponto onde o OpenRouter entra, sem o executor
#: conhecer fornecedor.
FabricaDeProvedor = Callable[[str, Settings], LLMProvider]


@dataclass(frozen=True, slots=True)
class Rodada:
    """Uma rodada de avaliacao, identificada pelo que a torna comparavel.

    Conjunto, versao de prompt, versao de schema e lista de modelos sao o que
    precisa estar igual entre duas rodadas para os numeros poderem ser
    comparados (RNF29).
    """

    iniciada_em: datetime
    prompt_version: str
    schema_version: str
    modelos: Sequence[str]
    casos: Sequence[str]
    execucoes: Sequence[Execucao]

    @property
    def total(self) -> int:
        return len(self.execucoes)


def _para_registro(execucao: Execucao) -> dict[str, Any]:
    """Converte a execucao em linha serializavel do arquivo de resultados."""

    curso = execucao.curso
    return {
        "caso": execucao.caso,
        "modelo": execucao.modelo,
        "modelo_reportado": execucao.modelo_reportado,
        "valida_de_primeira": execucao.valida_de_primeira,
        "tentativas": execucao.tentativas,
        "latencia_ms": execucao.latencia_ms,
        "tokens_entrada": execucao.tokens_entrada,
        "tokens_saida": execucao.tokens_saida,
        "erro": execucao.erro,
        "curso": curso.model_dump(mode="json") if curso is not None else None,
    }


def salvar(rodada: Rodada, destino: Path) -> Path:
    """Grava a rodada em JSON, criando o diretorio se preciso.

    O arquivo e a fonte das metricas: o notebook le daqui, nao da API.
    """

    destino.parent.mkdir(parents=True, exist_ok=True)
    corpo = {
        "iniciada_em": rodada.iniciada_em.isoformat(),
        "prompt_version": rodada.prompt_version,
        "schema_version": rodada.schema_version,
        "modelos": list(rodada.modelos),
        "casos": list(rodada.casos),
        "execucoes": [_para_registro(e) for e in rodada.execucoes],
    }
    destino.write_text(json.dumps(corpo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


def carregar(origem: Path) -> Rodada:
    """Le uma rodada gravada, sem reconstruir o curso validado.

    As metricas de qualidade precisam do ``StructuredCourse``; para recalcula-las
    a partir do arquivo, revalide ``registro["curso"]`` com
    ``validar_curso_estruturado``. O que volta aqui e o suficiente para custo,
    latencia, conformidade de schema e taxa de falha.
    """

    bruto = json.loads(origem.read_text(encoding="utf-8"))
    execucoes = [
        Execucao(
            caso=r["caso"],
            modelo=r["modelo"],
            modelo_reportado=r.get("modelo_reportado"),
            valida_de_primeira=r.get("valida_de_primeira", False),
            tentativas=r.get("tentativas", 1),
            latencia_ms=r.get("latencia_ms"),
            tokens_entrada=r.get("tokens_entrada"),
            tokens_saida=r.get("tokens_saida"),
            erro=r.get("erro"),
        )
        for r in bruto.get("execucoes", [])
    ]
    return Rodada(
        iniciada_em=datetime.fromisoformat(bruto["iniciada_em"]),
        prompt_version=bruto["prompt_version"],
        schema_version=bruto.get("schema_version", "desconhecida"),
        modelos=tuple(bruto.get("modelos", ())),
        casos=tuple(bruto.get("casos", ())),
        execucoes=tuple(execucoes),
    )


async def executar(
    *,
    casos: Sequence[CasoDeAvaliacao],
    modelos: Sequence[ModeloCandidato],
    fabrica_de_provedor: FabricaDeProvedor,
    prompt_version: str | None = None,
    settings: Settings | None = None,
    repeticoes: int = 1,
    ja_feitas: Iterable[tuple[str, str]] = (),
    ao_terminar_caso: Callable[[Execucao], None] | None = None,
) -> Rodada:
    """Roda o conjunto contra cada modelo e devolve as execucoes.

    Args:
        casos: conjunto de avaliacao.
        modelos: modelos candidatos, do catalogo.
        fabrica_de_provedor: cria o provedor para um slug de modelo.
        prompt_version: versao do prompt de extracao; por padrao, a ativa.
        settings: configuracao do ambiente.
        repeticoes: execucoes por caso. Acima de 1 alimenta a metrica de
            estabilidade (RNF03), que exige a mesma entrada mais de uma vez.
        ja_feitas: pares ``(modelo, caso)`` com resultado gravado, que nao sao
            chamados de novo - e o que torna a rodada retomavel.
        ao_terminar_caso: chamado apos cada execucao, para acompanhar o
            progresso de uma rodada longa.

    Returns:
        Rodada com uma execucao por (modelo, caso, repeticao).
    """

    config = settings or get_settings()
    versao = prompt_version or _versao_padrao()
    feitas = set(ja_feitas)
    execucoes: list[Execucao] = []

    for modelo in modelos:
        provedor = fabrica_de_provedor(modelo.slug, config)
        servico = StructuringService(provedor, config)
        for caso in casos:
            if (modelo.slug, caso.identificador) in feitas:
                continue
            for _ in range(max(1, repeticoes)):
                execucao = await _executar_um(
                    servico=servico,
                    caso=caso,
                    slug=modelo.slug,
                    prompt_version=versao,
                )
                execucoes.append(execucao)
                if ao_terminar_caso is not None:
                    ao_terminar_caso(execucao)

    return Rodada(
        iniciada_em=datetime.now(UTC),
        prompt_version=versao,
        schema_version=SCHEMA_VERSION,
        modelos=tuple(m.slug for m in modelos),
        casos=tuple(c.identificador for c in casos),
        execucoes=tuple(execucoes),
    )


async def _executar_um(
    *,
    servico: StructuringService,
    caso: CasoDeAvaliacao,
    slug: str,
    prompt_version: str,
) -> Execucao:
    """Uma chamada, convertida no registro que as metricas consomem.

    Nao deixa excecao escapar: o caso de uso nao levanta erro de provedor, e o
    que sobrar vira ``erro`` no registro, para a rodada nao morrer no meio por
    causa de um caso.
    """

    demanda = RawDemand(demand_id=caso.identificador, text=caso.texto)
    try:
        desfecho = await servico.structure_course(demanda, prompt_version=prompt_version)
    except Exception as erro:
        return Execucao(
            caso=caso.identificador,
            modelo=slug,
            erro=f"{type(erro).__name__}: {erro}",
        )

    completion = desfecho.completion
    uso = completion.usage if completion is not None else None
    base = Execucao(
        caso=caso.identificador,
        modelo=slug,
        modelo_reportado=completion.model if completion is not None else None,
        curso=desfecho.course,
        valida_de_primeira=desfecho.course is not None and desfecho.attempts == 1,
        tentativas=desfecho.attempts,
        latencia_ms=desfecho.elapsed_ms or None,
        tokens_entrada=uso.prompt_tokens if uso is not None else None,
        tokens_saida=uso.completion_tokens if uso is not None else None,
    )
    if desfecho.error is not None:
        return replace(base, erro=f"{type(desfecho.error).__name__}: {desfecho.error}")
    return base


def _versao_padrao() -> str:
    """Versao de prompt ativa, lida do proprio servico."""

    from app.services.structuring_service import DEFAULT_PROMPT_VERSION

    return DEFAULT_PROMPT_VERSION
