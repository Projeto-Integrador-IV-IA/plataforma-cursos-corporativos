"""Dominio do nucleo inteligente.

Expoe a forma canonica da saida da IA (RNF03): o curso estruturado, sua
validacao e o JSON Schema derivado dela. Quem consome importa daqui, nao do
modulo interno.
"""

from app.domain.course import (
    CAMPOS_DE_CONFIANCA,
    CAMPOS_EXTRAIDOS,
    CAMPOS_GERADOS,
    CHAVES_CANONICAS,
    CHAVES_OBRIGATORIAS,
    CourseFormat,
    FieldGap,
    GapKind,
    StructuredCourse,
    SyllabusModule,
    schema_do_curso_estruturado,
    validar_curso_estruturado,
)

__all__ = [
    "CAMPOS_DE_CONFIANCA",
    "CAMPOS_EXTRAIDOS",
    "CAMPOS_GERADOS",
    "CHAVES_CANONICAS",
    "CHAVES_OBRIGATORIAS",
    "CourseFormat",
    "FieldGap",
    "GapKind",
    "StructuredCourse",
    "SyllabusModule",
    "schema_do_curso_estruturado",
    "validar_curso_estruturado",
]
