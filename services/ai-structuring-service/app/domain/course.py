"""Dominio do curso estruturado - o produto do nucleo inteligente (RF11, RF12).

Esta e a forma canonica da saida da IA. O schema e fixo e versionado: prompt,
validacao, contrato de API e frontend dependem dele (RNF03 na matriz de
rastreabilidade, citado como RF14.1 no Documento Consolidado de Requisitos
v1.0). Alterar campo aqui e alterar contrato - ver a ADR-0006 e
``packages/contracts/schemas/structured-course.schema.json``.

Campos extraidos da demanda (RF11):
    tema                    assunto central do treinamento
    nicho                   setor ou area de atuacao do cliente
    publico_alvo            perfil dos participantes
    numero_participantes    quantidade estimada (pode ser faixa)
    carga_horaria           duracao total em horas
    formato                 presencial, online ou hibrido

Campos gerados (RF12):
    objetivos_aprendizagem  o que o participante sera capaz de fazer
    ementa                  modulos ordenados, cada um com titulo, topicos e carga

Metadados de confianca:
    campos_ausentes         o que nao foi possivel extrair do texto de entrada
    observacoes             ambiguidades que o operador precisa resolver

O modelo NUNCA inventa valor ausente: campo sem base no texto e reportado como
ausente, para que a revisao humana decida (RF14). Isso e o que torna RNF04
mensuravel.

Forma fixa entre execucoes
--------------------------
Duas execucoes produzem objetos com as mesmas chaves, na mesma ordem e com os
mesmos tipos, qualquer que seja o texto devolvido pelo provedor:

- ``StructuredCourse`` declara os dez campos em ordem canonica; campo que a
  resposta nao traz assume ``None`` ou lista vazia - nunca some da saida;
- ``extra="forbid"`` recusa chave fora do contrato: resposta fora do schema e
  falha, nao e aceita como "quase certa" (ADR-0006);
- ``CHAVES_OBRIGATORIAS`` sao as chaves que a resposta precisa trazer, ainda
  que com valor nulo. Sao exatamente as que o prompt ativo
  ``extract-requirements.v1`` manda devolver: chave que some da resposta e
  violacao de contrato, nao campo ausente. Os tres campos que aquele prompt
  ainda nao pede (``nicho``, ``numero_participantes`` e ``formato``) ficam
  opcionais ate existir prompt que os produza - e a forma da saida nao muda
  por causa disso.

Proveniencia da execucao (modelo, versao de prompt, tokens, latencia) nao vive
aqui: acompanha o artefato gravado, em ``app.schemas.structuring`` (RNF04,
RNF09).

Distinguir "campo ausente" de "campo com valor incerto" e trabalho do proximo
card de RNF03; o espaco ja esta reservado em ``campos_ausentes`` e
``observacoes``.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.exceptions import LLMInvalidResponseError


class CourseFormat(StrEnum):
    """Formato de realizacao do treinamento (RF11)."""

    PRESENCIAL = "presencial"
    ONLINE = "online"
    HIBRIDO = "hibrido"


#: Grafias aceitas para ``formato``. O modelo escreve em portugues corrente, com
#: ou sem acento e em qualquer caixa; o dominio guarda um valor so.
_FORMATOS_ACEITOS: Final[Mapping[str, str]] = {
    "presencial": CourseFormat.PRESENCIAL.value,
    "online": CourseFormat.ONLINE.value,
    "on-line": CourseFormat.ONLINE.value,
    "hibrido": CourseFormat.HIBRIDO.value,
    "híbrido": CourseFormat.HIBRIDO.value,
}


class CanonicalModel(BaseModel):
    """Base dos modelos do curso: forma fechada, congelada e sem espaco a mais.

    ``extra="forbid"`` e o que torna detectavel uma resposta fora do contrato.
    ``frozen=True`` impede edicao no lugar: a revisao humana (RF14) gera nova
    versao do artefato, nunca altera a existente (RNF09).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class SyllabusModule(CanonicalModel):
    """Modulo da ementa: um bloco de conteudo com titulo, topicos e carga.

    Attributes:
        titulo: nome do modulo, nos termos do cliente.
        topicos: assuntos do modulo, na ordem em que aparecem.
        carga_horaria: duracao do modulo em horas; ``None`` quando o texto nao
            permite saber sem supor.
    """

    titulo: str = Field(min_length=1)
    topicos: list[str] = Field(default_factory=list)
    carga_horaria: int | None = Field(default=None, gt=0)


class StructuredCourse(CanonicalModel):
    """Curso estruturado: a saida canonica da estruturacao por IA (RNF03).

    A ordem de declaracao dos campos e a ordem canonica da serializacao -
    extraidos (RF11), gerados (RF12) e metadados de confianca.

    Valor nulo ou lista vazia significa "nao estava no texto de entrada", e o
    nome do campo correspondente e esperado em ``campos_ausentes``. Zero nao e
    ausencia: carga horaria e numero de participantes sao positivos ou nulos.
    """

    tema: str | None
    nicho: str | None = None
    publico_alvo: str | None
    numero_participantes: int | None = Field(default=None, gt=0)
    carga_horaria: int | None = Field(gt=0)
    formato: CourseFormat | None = None
    objetivos_aprendizagem: list[str]
    ementa: list[SyllabusModule]
    campos_ausentes: list[str]
    observacoes: list[str]

    @field_validator("formato", mode="before")
    @classmethod
    def normalizar_formato(cls, valor: object) -> object:
        """Aceita variacao de caixa e de acento; grafia desconhecida e recusada."""

        if isinstance(valor, str):
            return _FORMATOS_ACEITOS.get(valor.strip().casefold(), valor)
        return valor

    def to_canonical_dict(self) -> dict[str, Any]:
        """Devolve o curso como dicionario de tipos JSON, em ordem canonica.

        E esta a forma que vai para o artefato gravado e para a API: mesmas
        chaves, mesma ordem e mesmos tipos em toda execucao (RNF03).
        """

        return self.model_dump(mode="json")

    def to_canonical_json(self) -> str:
        """Serializa o curso em JSON, na mesma ordem canonica de campos."""

        return self.model_dump_json()


#: Campos extraidos do texto da demanda (RF11).
CAMPOS_EXTRAIDOS: Final[tuple[str, ...]] = (
    "tema",
    "nicho",
    "publico_alvo",
    "numero_participantes",
    "carga_horaria",
    "formato",
)

#: Campos gerados a partir dos requisitos extraidos (RF12).
CAMPOS_GERADOS: Final[tuple[str, ...]] = ("objetivos_aprendizagem", "ementa")

#: Metadados de confianca que sustentam a revisao humana (RF14) e as metricas (RNF04).
CAMPOS_DE_CONFIANCA: Final[tuple[str, ...]] = ("campos_ausentes", "observacoes")

#: Chaves da saida canonica, na ordem em que sao serializadas.
CHAVES_CANONICAS: Final[tuple[str, ...]] = tuple(StructuredCourse.model_fields)

#: Chaves que a resposta do modelo precisa trazer, ainda que com valor nulo.
CHAVES_OBRIGATORIAS: Final[tuple[str, ...]] = tuple(
    nome for nome, campo in StructuredCourse.model_fields.items() if campo.is_required()
)


def validar_curso_estruturado(bruto: str | bytes | Mapping[str, Any]) -> StructuredCourse:
    """Valida a resposta do modelo contra a forma canonica do curso (RNF03).

    Args:
        bruto: texto JSON devolvido pelo provedor de LLM, ou o objeto ja
            desserializado.

    Returns:
        O ``StructuredCourse`` correspondente, com todos os campos presentes.

    Raises:
        LLMInvalidResponseError: o texto nao e JSON, falta chave obrigatoria,
            sobra chave fora do contrato ou algum valor tem tipo incompativel.
            Resposta invalida e falha: a demanda bruta continua registrada e a
            operacao pode ser repetida (ADR-0006, RNF05).
    """

    try:
        if isinstance(bruto, str | bytes):
            return StructuredCourse.model_validate_json(bruto)
        return StructuredCourse.model_validate(bruto)
    except ValidationError as erro:
        raise LLMInvalidResponseError(
            "Resposta do modelo nao corresponde ao schema do curso estruturado.",
            details={"violacoes": _resumo_das_violacoes(erro)},
        ) from erro


def schema_do_curso_estruturado() -> dict[str, Any]:
    """Devolve o JSON Schema derivado do modelo canonico.

    Alimenta ``CompletionParams.response_schema`` quando o fornecedor aceita
    saida estruturada e serve de referencia para
    ``packages/contracts/schemas/structured-course.schema.json`` - schema
    derivado do modelo nao sai de sincronia com ele.
    """

    return StructuredCourse.model_json_schema()


def _resumo_das_violacoes(erro: ValidationError) -> list[dict[str, str]]:
    """Resume os erros de validacao para o contexto da excecao.

    So caminho, tipo e mensagem: o valor recusado fica de fora porque carrega
    texto da demanda do cliente, que nao entra em log nem em corpo de erro
    (RNF10).
    """

    return [
        {
            "campo": ".".join(str(parte) for parte in violacao["loc"]) or "(raiz)",
            "erro": violacao["type"],
            "mensagem": violacao["msg"],
        }
        for violacao in erro.errors()
    ]
