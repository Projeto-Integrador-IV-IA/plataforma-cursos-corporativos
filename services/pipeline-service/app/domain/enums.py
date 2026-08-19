"""Enumeracoes do dominio.

Vocabulario fechado do negocio. Estes valores sao contrato: aparecem na API, no
banco e na interface, entao mudanca aqui e mudanca de contrato (RNF02).

PipelineStage - as cinco etapas percorridas por uma negociacao (RF05):
    CAPTACAO        demanda registrada, ainda bruta
    ESTRUTURACAO    demanda enviada / retornada da camada de IA
    PRODUTO         curso estruturado revisado pelo operador (RF14)
    PROPOSTA        proposta montada para o cliente
    ACOMPANHAMENTO  pos-proposta, negociacao em andamento

    O avanco e sequencial, mas o retrocesso e livre para qualquer etapa
    anterior (RF06) - o cliente muda escopo a qualquer momento.

DemandStatus - situacao da negociacao, ortogonal a etapa:
    ABERTA, GANHA, PERDIDA, CANCELADA

ArtifactType - natureza do artefato consolidado (RF15):
    DEMANDA_BRUTA, REQUISITOS_EXTRAIDOS, EMENTA, PROPOSTA, OUTRO

TODO(scaffolding): implementar os enums como ``StrEnum``.
"""

# TODO: class PipelineStage(StrEnum): ...
# TODO: class DemandStatus(StrEnum): ...
# TODO: class ArtifactType(StrEnum): ...
