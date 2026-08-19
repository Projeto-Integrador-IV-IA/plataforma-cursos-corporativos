"""Entidades do dominio (independentes de banco e de framework).

Modelo conceitual - detalhamento completo em ``docs/03-dados/modelo-dados.md``.

    Client            empresa cliente (RF01)
    Demand            negociacao vinculada a um cliente (RF02)
    RawInput          texto bruto recebido para uma demanda (RF09)
    StageTransition   registro imutavel de mudanca de etapa (RF07)
    Artifact          documento atrelado a demanda (RF15)
    ArtifactVersion   versao de um artefato, append-only (RF08)
    StructuredCourse  saida estruturada da IA (tema, publico, carga, ementa)

Regras de dominio que esta camada precisa garantir:
    - uma demanda pertence a exatamente um cliente (RNF08);
    - toda mudanca de etapa gera uma StageTransition - nunca sobrescreve (RF07, RNF09);
    - versao de artefato nunca e apagada nem alterada; edicao cria versao nova (RF08);
    - a demanda bruta e persistida antes de qualquer chamada ao LLM (RNF05).

TODO(scaffolding): implementar as entidades como dataclasses ou modelos Pydantic.
"""

# TODO: @dataclass class Client: ...
# TODO: @dataclass class Demand: ...
# TODO: @dataclass class StageTransition: ...
# TODO: @dataclass class Artifact: ...
# TODO: @dataclass class ArtifactVersion: ...
