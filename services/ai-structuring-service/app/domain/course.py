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
    campos_ausentes         lacunas apontadas campo a campo, cada uma com tipo
                            (ausente, ambigua ou contraditoria) e motivo
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
  ``extract-requirements.v3`` manda devolver: chave que some da resposta e
  violacao de contrato, nao campo ausente. Os tres campos que aquele prompt
  ainda nao pede (``nicho``, ``numero_participantes`` e ``formato``) ficam
  opcionais ate existir prompt que os produza - e a forma da saida nao muda
  por causa disso.

Proveniencia da execucao (modelo, versao de prompt, tokens, latencia) nao vive
aqui: acompanha o artefato gravado, em ``app.schemas.structuring`` (RNF04,
RNF09).

Campo nao inferivel e lacuna classificada
-----------------------------------------
Regra que separa a plataforma de um gerador de texto: o que nao esta na fonte
nao e inventado (RNF03 na matriz, citado como RF14.2 e RF15.1 no Documento
Consolidado de Requisitos v1.0). A validacao nao confia na disciplina do
modelo - ela reconcilia o que foi devolvido, em quatro passos:

1. campo devolvido vazio (``null``, texto em branco ou lista vazia) vira o
   vazio canonico do seu tipo - ``None`` para escalar, ``[]`` para lista - e
   entra em ``campos_ausentes``;
2. campo declarado em ``campos_ausentes`` mas devolvido com valor tem o valor
   descartado: ou o modelo disse que nao havia base no texto, ou disse que a
   fonte e ambigua ou contraditoria - em qualquer dos casos, escolher o valor
   e decisao do revisor, nao da validacao. O descarte fica registrado em
   ``observacoes``, sem repetir o valor recusado (RNF10);
3. campo preenchido e nao declarado nunca aparece em ``campos_ausentes``;
4. ``campos_ausentes`` sai deduplicado, em ordem canonica de campo, e so com
   nome de campo do contrato - nome que nao corresponde a campo nenhum nao
   chega ao revisor.

Chave que a resposta nem traz nao e reconciliada: ausencia de chave
obrigatoria continua sendo violacao de contrato, e os campos opcionais que o
prompt ativo ainda nao pede nao viram "campo ausente" por nunca terem sido
perguntados.

Cada item de ``campos_ausentes`` e um ``FieldGap`` - ``campo``, ``tipo`` e
``motivo``. O ``tipo`` diz por que o campo ficou sem valor utilizavel
(``ausente``, ``ambigua`` ou ``contraditoria``), e e isso que orienta o
operador sobre o que perguntar ao cliente: informacao que falta se pede,
informacao ambigua se esclarece, informacao contraditoria se confronta. O
``motivo`` e a frase curta que a tela de revisao mostra (RF14).

Entrada tolerante, saida canonica: a reconciliacao aceita tanto o item rico
quanto o nome solto que a ``extract-requirements.v2`` produz, e nesse caso
procura o motivo nas ``observacoes``, no formato ``<campo>: <motivo>`` que
aquela versao exige. Assim a v2 continua reproduzivel (RNF04) sem que a saida
tenha duas formas. ``motivos_dos_campos_ausentes()`` segue devolvendo o par
campo -> motivo, e ``nomes_dos_campos_ausentes`` da a lista de nomes que a tela
usa para destacar o que falta.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Final

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

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


class GapKind(StrEnum):
    """Por que um campo ficou sem valor utilizavel (RNF03).

    A distincao existe para o operador, nao para a maquina: cada tipo pede uma
    conversa diferente com o cliente (RF14).

    Attributes:
        AUSENTE: a fonte nao traz a informacao.
        AMBIGUA: a fonte traz a informacao de forma que admite mais de uma
            leitura, e escolher uma delas seria supor.
        CONTRADITORIA: dois trechos da mesma fonte afirmam coisas
            incompativeis sobre o campo.
    """

    AUSENTE = "ausente"
    AMBIGUA = "ambigua"
    CONTRADITORIA = "contraditoria"


#: Grafias aceitas para ``tipo``, com e sem acento, em qualquer caixa - mesma
#: tolerancia dada a ``formato``, e pelo mesmo motivo: o modelo escreve em
#: portugues corrente e o dominio guarda um valor so.
_TIPOS_DE_LACUNA_ACEITOS: Final[Mapping[str, str]] = {
    "ausente": GapKind.AUSENTE.value,
    "ambigua": GapKind.AMBIGUA.value,
    "ambígua": GapKind.AMBIGUA.value,
    "contraditoria": GapKind.CONTRADITORIA.value,
    "contraditória": GapKind.CONTRADITORIA.value,
}

#: Por que o valor entregue para um campo com lacuna declarada e descartado.
#: A frase muda com o tipo: ausencia e falta de base, ambiguidade e contradicao
#: sao escolhas que cabem ao revisor (RF14).
_JUSTIFICATIVA_DO_DESCARTE: Final[Mapping[str, str]] = {
    GapKind.AUSENTE.value: (
        "valor descartado na validacao - o modelo declarou o campo ausente e valor sem "
        "base no texto nao e aproveitado."
    ),
    GapKind.AMBIGUA.value: (
        "valor descartado na validacao - o modelo declarou a informacao ambigua na fonte "
        "e escolher uma das leituras cabe ao revisor."
    ),
    GapKind.CONTRADITORIA.value: (
        "valor descartado na validacao - o modelo declarou a informacao contraditoria na "
        "fonte e escolher entre os trechos em conflito cabe ao revisor."
    ),
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


class FieldGap(CanonicalModel):
    """Lacuna apontada para um campo do curso (RNF03).

    RF15.1 no Documento Consolidado de Requisitos v1.0. E o apontamento que a
    tela de revisao destaca (RF14): o campo ficou sem valor utilizavel, este e o
    tipo da lacuna e este e o motivo, na linguagem do operador.

    Attributes:
        campo: nome do campo do contrato, exatamente como no schema.
        tipo: por que o campo ficou sem valor - ``ausente`` por padrao, que e o
            caso mais comum e o unico que a ``extract-requirements.v2`` sabia
            produzir.
        motivo: frase curta explicando o apontamento; ``None`` quando o modelo
            nao registrou nenhuma - lacuna sem explicacao continua visivel, em
            vez de sumir da revisao.
    """

    campo: str = Field(min_length=1)
    tipo: GapKind = GapKind.AUSENTE
    motivo: str | None = None

    @field_validator("tipo", mode="before")
    @classmethod
    def normalizar_tipo(cls, valor: object) -> object:
        """Aceita variacao de caixa e de acento; grafia desconhecida e recusada."""

        return _tipo_normalizado(valor)

    @field_validator("motivo", mode="before")
    @classmethod
    def motivo_em_branco_e_ausencia_de_motivo(cls, valor: object) -> object:
        """Texto em branco nao explica nada: vale como motivo nao registrado."""

        if isinstance(valor, str) and not valor.strip():
            return None
        return valor


class StructuredCourse(CanonicalModel):
    """Curso estruturado: a saida canonica da estruturacao por IA (RNF03).

    A ordem de declaracao dos campos e a ordem canonica da serializacao -
    extraidos (RF11), gerados (RF12) e metadados de confianca.

    Valor nulo ou lista vazia significa "nao ha valor utilizavel no texto de
    entrada", e o campo correspondente aparece em ``campos_ausentes``, com o
    tipo da lacuna e o motivo - a validacao reconcilia os dois, entao as duas
    leituras nunca se contradizem. Zero nao e ausencia: carga horaria e numero
    de participantes sao positivos ou nulos.
    """

    tema: str | None
    nicho: str | None = None
    publico_alvo: str | None
    numero_participantes: int | None = Field(default=None, gt=0)
    carga_horaria: int | None = Field(gt=0)
    formato: CourseFormat | None = None
    objetivos_aprendizagem: list[str]
    ementa: list[SyllabusModule]
    campos_ausentes: list[FieldGap]
    observacoes: list[str]

    @model_validator(mode="before")
    @classmethod
    def marcar_campos_nao_inferiveis(cls, dados: Any) -> Any:
        """Reconcilia valor e lacuna antes de montar o curso (RNF03).

        Campo vazio vira o vazio canonico do seu tipo e entra em
        ``campos_ausentes``, classificado; valor devolvido para campo com
        lacuna declarada e descartado, com registro em ``observacoes``. O que
        esta preenchido e nao foi declarado fica fora da lista.

        A lacuna declarada e aceita tanto no item rico (``campo``, ``tipo``,
        ``motivo``) quanto no nome solto da ``extract-requirements.v2`` - nesse
        caso o tipo e ``ausente`` e o motivo vem da linha ``<campo>: <motivo>``
        das ``observacoes``. A saida e sempre a forma rica.

        Resposta que nao e mapeamento, ou que traz ``campos_ausentes`` fora do
        tipo declarado, passa intacta: recusar isso e trabalho da validacao
        normal, e mascarar a violacao aqui esconderia o defeito.
        """

        if not isinstance(dados, Mapping):
            return dados
        declaradas = _lacunas_declaradas(dados.get("campos_ausentes"))
        if declaradas is None:
            return dados

        valores = dict(dados)
        registradas = valores.get("observacoes")
        originais = list(registradas) if _e_lista_de_texto(registradas) else None
        observacoes = list(originais) if originais is not None else None

        lacunas: list[dict[str, Any]] = []
        for campo in CAMPOS_INFERIVEIS:
            if campo not in valores:
                continue
            declarada = declaradas.get(campo)
            vazio = _sem_base_no_texto(valores[campo])
            if not vazio and declarada is None:
                continue
            tipo = declarada["tipo"] if declarada is not None else GapKind.AUSENTE.value
            if not vazio and observacoes is not None:
                observacoes.append(f"{campo}: {_justificativa_do_descarte(tipo)}")
            valores[campo] = _vazio_canonico_de(campo)
            motivo = declarada["motivo"] if declarada is not None else None
            lacunas.append(
                {
                    "campo": campo,
                    "tipo": tipo,
                    "motivo": motivo or _motivo_registrado(campo, originais or []),
                }
            )

        valores["campos_ausentes"] = lacunas
        if observacoes is not None:
            valores["observacoes"] = observacoes
        return valores

    @field_validator("formato", mode="before")
    @classmethod
    def normalizar_formato(cls, valor: object) -> object:
        """Aceita variacao de caixa e de acento; grafia desconhecida e recusada."""

        if isinstance(valor, str):
            return _FORMATOS_ACEITOS.get(valor.strip().casefold(), valor)
        return valor

    @property
    def nomes_dos_campos_ausentes(self) -> tuple[str, ...]:
        """Nomes dos campos com lacuna, na ordem canonica.

        E o que a tela de revisao usa para destacar o que falta (RF14), sem
        precisar saber a forma do apontamento.
        """

        return tuple(lacuna.campo for lacuna in self.campos_ausentes)

    def motivos_dos_campos_ausentes(self) -> dict[str, str | None]:
        """Pareia cada campo com lacuna e o motivo do apontamento.

        O prompt ativo exige um motivo por lacuna. Lacuna sem motivo vem com
        ``None``: a tela de revisao mostra o apontamento mesmo sem explicacao,
        em vez de esconder o que falta (RF14).

        Returns:
            Dicionario na ordem de ``campos_ausentes``, do nome do campo para o
            motivo declarado, ou ``None`` quando nenhum foi registrado.
        """

        return {lacuna.campo: lacuna.motivo for lacuna in self.campos_ausentes}

    def lacunas_por_tipo(self, tipo: GapKind) -> tuple[FieldGap, ...]:
        """Filtra os apontamentos de um tipo, na ordem canonica de campo.

        Cada tipo pede uma conversa diferente com o cliente: o operador pergunta
        o que esta ausente, esclarece o que esta ambiguo e confronta o que esta
        contraditorio (RF14).

        Args:
            tipo: tipo de lacuna a filtrar.

        Returns:
            Os apontamentos daquele tipo, possivelmente nenhum.
        """

        return tuple(lacuna for lacuna in self.campos_ausentes if lacuna.tipo is tipo)

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

#: Campos que dependem do texto da demanda e, por isso, podem faltar. Sao estes
#: que ``campos_ausentes`` pode nomear, na ordem canonica em que sao listados.
CAMPOS_INFERIVEIS: Final[tuple[str, ...]] = CAMPOS_EXTRAIDOS + CAMPOS_GERADOS

#: Campos inferiveis cujo vazio canonico e lista, e nao ``None``.
_CAMPOS_DE_LISTA: Final[frozenset[str]] = frozenset(CAMPOS_GERADOS)

#: Metadados de confianca que sustentam a revisao humana (RF14) e as metricas (RNF04).
CAMPOS_DE_CONFIANCA: Final[tuple[str, ...]] = ("campos_ausentes", "observacoes")

#: Chaves da saida canonica, na ordem em que sao serializadas.
CHAVES_CANONICAS: Final[tuple[str, ...]] = tuple(StructuredCourse.model_fields)

#: Chaves aceitas em cada item de ``campos_ausentes``. Item com chave a mais e
#: resposta fora do contrato, recusada pela validacao como qualquer outra.
_CHAVES_DA_LACUNA: Final[frozenset[str]] = frozenset(FieldGap.model_fields)

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


def _e_lista_de_texto(valor: object) -> bool:
    """Diz se o valor ja chega como lista de strings, como o contrato exige."""

    return isinstance(valor, list) and all(isinstance(item, str) for item in valor)


def _tipo_normalizado(valor: object) -> object:
    """Reduz a grafia do tipo de lacuna ao valor canonico, se for reconhecida."""

    if isinstance(valor, str):
        return _TIPOS_DE_LACUNA_ACEITOS.get(valor.strip().casefold(), valor)
    return valor


def _justificativa_do_descarte(tipo: object) -> str:
    """Explica, conforme o tipo de lacuna, por que o valor entregue nao vale.

    Tipo em grafia desconhecida nunca chega a aparecer em observacao: a
    validacao recusa a resposta logo em seguida. Ainda assim a mensagem cai no
    texto da ausencia, para que nao exista caminho sem explicacao.
    """

    canonico = _tipo_normalizado(tipo)
    if not isinstance(canonico, str):
        canonico = GapKind.AUSENTE.value
    return _JUSTIFICATIVA_DO_DESCARTE.get(
        canonico, _JUSTIFICATIVA_DO_DESCARTE[GapKind.AUSENTE.value]
    )


def _lacunas_declaradas(valor: object) -> dict[str, dict[str, Any]] | None:
    """Le ``campos_ausentes`` como foi devolvido e indexa as lacunas por campo.

    Aceita as duas formas que o catalogo de prompts ja produziu: o item rico da
    ``extract-requirements.v3`` (``campo``, ``tipo`` e ``motivo``) e o nome
    solto da ``v2``, que vale como lacuna do tipo ``ausente``. Repeticao do
    mesmo campo fica com a primeira declaracao.

    Returns:
        O indice campo -> ``{"tipo", "motivo"}``, ou ``None`` quando o valor nao
        tem forma reconhecivel - ai a reconciliacao se afasta e deixa a
        validacao normal recusar a resposta (ADR-0006).
    """

    if not isinstance(valor, list):
        return None

    declaradas: dict[str, dict[str, Any]] = {}
    for item in valor:
        if isinstance(item, str):
            declaradas.setdefault(item.strip(), {"tipo": GapKind.AUSENTE.value, "motivo": None})
            continue
        if not isinstance(item, Mapping) or set(item) - _CHAVES_DA_LACUNA:
            return None
        campo = item.get("campo")
        tipo = item.get("tipo", GapKind.AUSENTE.value)
        motivo = item.get("motivo")
        if not isinstance(campo, str) or not isinstance(tipo, str):
            return None
        if motivo is not None and not isinstance(motivo, str):
            return None
        declaradas.setdefault(campo.strip(), {"tipo": tipo, "motivo": motivo})
    return declaradas


def _sem_base_no_texto(valor: object) -> bool:
    """Diz se o valor devolvido significa "nao estava no texto de entrada".

    Sao vazios: ``None``, texto em branco e colecao sem item. Zero nao e vazio -
    carga horaria e numero de participantes zerados sao valor invalido, recusado
    pela validacao de tipo, e nao ausencia de informacao.
    """

    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, list | tuple | dict):
        return not valor
    return False


def _vazio_canonico_de(campo: str) -> Any:
    """Devolve o vazio do campo: lista nova para campo de lista, ``None`` senao."""

    return [] if campo in _CAMPOS_DE_LISTA else None


def _motivo_registrado(campo: str, observacoes: list[str]) -> str | None:
    """Procura nas observacoes a linha ``<campo>: <motivo>`` do campo ausente.

    Vale a primeira linha encontrada. Sem linha correspondente, o motivo e
    ``None``: ausencia sem explicacao continua visivel para o revisor.
    """

    prefixo = f"{campo}:"
    for observacao in observacoes:
        if observacao.startswith(prefixo):
            return observacao[len(prefixo) :].strip() or None
    return None


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
