"""Modelos ORM: artefato e versao de artefato (RF08, RF15).

Tabelas ``artifacts`` e ``artifact_versions``.

``artifacts`` identifica o documento logico atrelado a demanda (ementa,
requisitos extraidos, proposta). ``artifact_versions`` guarda cada versao do
conteudo, com numero sequencial por artefato, autor, origem (IA ou humano) e
timestamp.

Regras:
    - versao nunca e alterada nem removida - editar cria versao nova (RF08);
    - toda versao aponta para a demanda, mantendo a fonte unica de verdade (RF15);
    - a origem distingue o que a IA gerou do que o humano revisou (RF14),
      insumo das metricas de qualidade (RNF04).

Ponto em aberto: ver docs/01-requisitos/questoes-em-aberto.md - a edicao humana
da saida da IA gera nova versao ou sobrescreve a corrente?

TODO(scaffolding): implementar ``Artifact`` e ``ArtifactVersion``.
"""
