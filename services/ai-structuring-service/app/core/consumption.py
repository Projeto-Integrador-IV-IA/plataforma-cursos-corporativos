"""Agregacao e limite de consumo da API de LLM (RNF22 do Documento Consolidado;
RNF12 na matriz legada: "operacao em camada gratuita/estudantil").

O MVP roda em camada gratuita ou estudantil do provedor de LLM (RNF12/RNF23) e
nao pode ser derrubado por consumo inesperado. Este modulo agrega, por dia, os
tokens e chamadas ja registrados por chamada individual em
``structuring_service.py`` (RNF08.1) e alerta no log quando um teto
configuravel e ultrapassado.

Periodo escolhido: dia civil em UTC. "Por periodo" no card nao fixa a janela;
dia e o menor periodo que ainda faz sentido para um alerta de estouro de
camada gratuita (a maioria dos provedores, incluindo o OpenRouter, tambem
aplica limite de taxa por dia) e e trivial de agregar em mes, se um dia a
equipe precisar do total mensal - ver ``custos-operacao.md`` para a projecao
mensal a partir de uma amostra.

Mesma limitacao de ``ExecutionLogHandler`` e ``job_service.py``: o acumulado
vive em memoria, por processo. Reiniciar o servico zera o consumo do dia, e
com mais de uma replica cada uma so sabe o que ela mesma atendeu - o numero
exposto por este modulo e um piso do consumo real nesse caso, nunca o total.
Nenhuma das duas limitacoes e resolvida aqui.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.core.logging import get_logger

_logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ConsumoDoDia:
    """Consumo acumulado de um dia civil (UTC).

    Attributes:
        dia: dia civil (UTC) a que o consumo se refere.
        chamadas: quantas chamadas ao provedor contribuiram para o total.
        tokens_entrada: soma dos tokens de entrada das chamadas do dia.
        tokens_saida: soma dos tokens de saida das chamadas do dia.
    """

    dia: date
    chamadas: int
    tokens_entrada: int
    tokens_saida: int

    @property
    def tokens_totais(self) -> int:
        """Tokens de entrada e saida somados - o numero que o limite vigia."""

        return self.tokens_entrada + self.tokens_saida


class ConsumoDeLLM:
    """Acumula tokens e chamadas por dia civil (UTC), em memoria, por processo.

    Instanciavel de proposito, em vez de so funcoes de modulo: o teste
    constroi a sua propria instancia e nao compete pelo mesmo estado global
    que a aplicacao usa em producao (ver o singleton de modulo abaixo).
    """

    def __init__(self) -> None:
        self._por_dia: dict[date, tuple[int, int, int]] = {}

    def registrar(
        self,
        *,
        tokens_entrada: int,
        tokens_saida: int,
        quando: datetime | None = None,
    ) -> ConsumoDoDia:
        """Soma uma chamada ao total do dia e devolve o acumulado resultante."""

        momento = quando or datetime.now(UTC)
        dia = momento.date()
        chamadas_atual, entrada_atual, saida_atual = self._por_dia.get(dia, (0, 0, 0))
        acumulado = (
            chamadas_atual + 1,
            entrada_atual + tokens_entrada,
            saida_atual + tokens_saida,
        )
        self._por_dia[dia] = acumulado
        chamadas, entrada, saida = acumulado
        return ConsumoDoDia(dia=dia, chamadas=chamadas, tokens_entrada=entrada, tokens_saida=saida)

    def do_dia(self, dia: date | None = None) -> ConsumoDoDia:
        """Consumo acumulado do dia pedido (hoje em UTC, por padrao).

        Dia sem chamada registrada devolve consumo zerado, nunca erro: "ainda
        nao houve chamada hoje" e um resultado valido, nao uma falha de
        consulta.
        """

        alvo = dia or datetime.now(UTC).date()
        chamadas, entrada, saida = self._por_dia.get(alvo, (0, 0, 0))
        return ConsumoDoDia(dia=alvo, chamadas=chamadas, tokens_entrada=entrada, tokens_saida=saida)


#: Instancia unica do processo - mesma escolha de ``_execution_log_handler``
#: em ``core/logging.py``: o que a aplicacao usa em producao e um singleton de
#: modulo, nunca recriado a cada requisicao (a dependencia de
#: ``StructuringService`` e recriada por chamada; o consumo precisa sobreviver
#: a ela para agregar entre chamadas).
_consumo = ConsumoDeLLM()


def registrar_consumo(
    *,
    tokens_entrada: int,
    tokens_saida: int,
    limite_diario: int | None,
) -> ConsumoDoDia:
    """Registra os tokens de uma chamada bem-sucedida e alerta se vigiado (RNF22).

    Chamado uma unica vez por chamada bem-sucedida ao provedor, no mesmo ponto
    de ``structuring_service.structure()`` que ja sabe os tokens (RNF08.1) -
    chamada que falhou nao tem token de saida a contar.

    Args:
        tokens_entrada: tokens de entrada da chamada que acabou de responder.
        tokens_saida: tokens de saida da mesma chamada.
        limite_diario: teto configurado em ``LLM_DAILY_TOKEN_BUDGET``; ``None``
            desliga o alerta - sem teto definido ainda nao ha o que vigiar.

    Returns:
        O consumo acumulado do dia depois de somar esta chamada.
    """

    consumo = _consumo.registrar(tokens_entrada=tokens_entrada, tokens_saida=tokens_saida)
    if limite_diario is not None and consumo.tokens_totais > limite_diario:
        _logger.warning(
            "Limite diario de consumo de tokens excedido (dia=%s, tokens=%d, limite=%d).",
            consumo.dia,
            consumo.tokens_totais,
            limite_diario,
        )
    return consumo


def consultar_consumo(dia: date | None = None) -> ConsumoDoDia:
    """Consumo agregado do dia, para consulta externa (RNF22).

    Nunca levanta excecao: dia sem chamada devolve consumo zerado.
    """

    return _consumo.do_dia(dia)
