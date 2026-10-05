"""Catalogo de prompts versionados (RF13, RNF03).

Prompt e artefato versionado em arquivo, nao string embutida no codigo: sem
versao fixa, uma medicao de qualidade nao pode ser comparada com a anterior
(RNF04) e uma alteracao vira cacada de string pelo codigo. Ver
``app/prompts/README.md`` e a ADR-0006.

Uso::

    prompt = carregar_prompt("extract-requirements", "v1")
    texto = prompt.render(texto_normalizado=demanda)

Convencao de nome de arquivo: ``<funcao>.v<N>.md``. Cada arquivo comeca com um
bloco de metadados entre ``---`` (versao, status, requisito, modelo alvo, autor,
data, mudancas, variaveis) seguido do corpo em Markdown - e o corpo, com as
variaveis substituidas, que vai para o provedor de LLM.

As variaveis aparecem no corpo como ``{{nome}}``. A marcacao usa chaves duplas
de proposito: o corpo tem exemplos em JSON, e chave simples colidiria com eles.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

PROMPTS_DIR: Final[Path] = Path(__file__).parent

#: Nome de funcao aceito: minusculas, digitos e hifen. Barra a leitura de
#: arquivo fora do catalogo.
_NOME_VALIDO: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSAO_VALIDA: Final[re.Pattern[str]] = re.compile(r"^v[0-9]+$")
_PLACEHOLDER: Final[re.Pattern[str]] = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")
_METADADOS: Final[re.Pattern[str]] = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


@dataclass(frozen=True, slots=True)
class Prompt:
    """Um prompt carregado do catalogo.

    Attributes:
        nome: funcao do prompt, ex.: ``extract-requirements``.
        versao: versao pedida, ex.: ``v1``.
        metadados: bloco declarado no topo do arquivo.
        corpo: texto em Markdown, ainda com os marcadores ``{{variavel}}``.
    """

    nome: str
    versao: str
    metadados: dict[str, str]
    corpo: str

    @property
    def identificador(self) -> str:
        """Identificacao gravada na proveniencia do artefato (RNF04, RNF09)."""

        return f"{self.nome}.{self.versao}"

    @property
    def variaveis(self) -> frozenset[str]:
        """Variaveis que o corpo espera receber."""

        return frozenset(_PLACEHOLDER.findall(self.corpo))

    def render(self, **valores: str) -> str:
        """Substitui as variaveis do corpo e devolve o texto final.

        Args:
            **valores: valor de cada variavel declarada no corpo.

        Returns:
            O prompt pronto para ser enviado ao provedor de LLM.

        Raises:
            ValueError: falta variavel exigida pelo corpo ou foi passada
                variavel que ele nao usa. As duas situacoes indicam prompt e
                chamador fora de sincronia - falhar e melhor do que enviar ao
                modelo um texto com marcador cru ou com dado ignorado.
        """

        exigidas = self.variaveis
        recebidas = frozenset(valores)
        if faltando := exigidas - recebidas:
            raise ValueError(
                f"{self.identificador}: faltam variaveis {sorted(faltando)}",
            )
        if sobrando := recebidas - exigidas:
            raise ValueError(
                f"{self.identificador}: variaveis desconhecidas {sorted(sobrando)}",
            )
        return _PLACEHOLDER.sub(lambda m: valores[m.group(1)], self.corpo)


@lru_cache
def carregar_prompt(nome: str, versao: str = "v1") -> Prompt:
    """Carrega o prompt ``<nome>.<versao>.md`` do catalogo.

    O resultado e cacheado por processo: o arquivo nao muda em execucao, e
    versao nova significa arquivo novo, nunca edicao no lugar.

    Args:
        nome: funcao do prompt, ex.: ``extract-requirements``.
        versao: versao a carregar, no formato ``v<N>``.

    Returns:
        O ``Prompt`` correspondente.

    Raises:
        ValueError: nome ou versao fora do formato, ou prompt inexistente no
            catalogo - com a lista do que existe.
    """

    if not _NOME_VALIDO.match(nome):
        raise ValueError(f"Nome de prompt invalido: {nome!r}")
    if not _VERSAO_VALIDA.match(versao):
        raise ValueError(f"Versao de prompt invalida: {versao!r} - use o formato 'v1'")

    arquivo = PROMPTS_DIR / f"{nome}.{versao}.md"
    if not arquivo.is_file():
        disponiveis = ", ".join(f"{n}.{v}" for n, v in listar_prompts()) or "nenhum"
        raise ValueError(
            f"Prompt {nome}.{versao} nao existe no catalogo. Disponiveis: {disponiveis}."
        )

    metadados, corpo = _separar_metadados(arquivo.read_text(encoding="utf-8"))
    return Prompt(nome=nome, versao=versao, metadados=metadados, corpo=corpo)


def listar_prompts() -> tuple[tuple[str, str], ...]:
    """Lista os pares ``(nome, versao)`` presentes no catalogo, ordenados."""

    encontrados = []
    for arquivo in sorted(PROMPTS_DIR.glob("*.v*.md")):
        nome, _, versao = arquivo.name.removesuffix(".md").rpartition(".")
        if _NOME_VALIDO.match(nome) and _VERSAO_VALIDA.match(versao):
            encontrados.append((nome, versao))
    return tuple(encontrados)


def _separar_metadados(conteudo: str) -> tuple[dict[str, str], str]:
    """Separa o bloco de metadados do corpo do prompt.

    O bloco e um ``chave: valor`` por linha entre marcas ``---``. Nao e YAML
    completo de proposito: o catalogo nao precisa disso e o servico nao carrega
    dependencia so para ler cinco linhas.
    """

    casamento = _METADADOS.match(conteudo)
    if casamento is None:
        return {}, conteudo.strip()

    metadados: dict[str, str] = {}
    for linha in casamento.group(1).splitlines():
        chave, separador, valor = linha.partition(":")
        if separador and (chave := chave.strip()):
            metadados[chave] = valor.strip()
    return metadados, conteudo[casamento.end() :].strip()
