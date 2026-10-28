/**
 * Leitura do curso estruturado guardado na versao do artefato (RF19).
 *
 * O que chega do contrato e um objeto JSON aberto (`structured_content`), ja
 * validado contra o schema canonico pelo servico (RNF03). Esta tela nao
 * revalida: a regra de negocio e do backend, e duplica-la aqui criaria duas
 * verdades que divergem no primeiro campo novo.
 *
 * O que este modulo faz e outra coisa - traduzir aquele objeto para a forma
 * que a tela consome, sem `any` e sem quebrar quando um campo vem fora do
 * tipo esperado. Campo ilegivel vira ausencia, nao excecao: a revisao humana
 * precisa acontecer justamente quando a saida do modelo nao esta perfeita, e
 * uma tela em branco seria o pior desfecho possivel.
 *
 * As chaves do resultado sao as do contrato, em `snake_case`, de proposito: e
 * por elas que `campos_ausentes[].campo` encontra o campo que apontou (RF15).
 */

import { GAP_KINDS, type GapKind, type JsonObject, type JsonValue } from '@/types/api';

/** Campos do curso apresentados na revisao, na ordem canonica do contrato. */
export const CAMPOS_DO_CURSO = [
  'tema',
  'nicho',
  'publico_alvo',
  'numero_participantes',
  'carga_horaria',
  'formato',
  'objetivos_aprendizagem',
  'ementa',
] as const;

export type CampoDoCurso = (typeof CAMPOS_DO_CURSO)[number];

/**
 * Lacuna como a tela a le.
 *
 * `tipo` e nulo quando o servico declarou um tipo que esta versao da interface
 * nao conhece; `tipoDeclarado` guarda o codigo como veio, para que a lacuna
 * apareca de todo modo em vez de sumir da revisao.
 */
export interface LacunaLida {
  readonly campo: string;
  readonly tipo: GapKind | null;
  readonly tipoDeclarado: string;
  readonly motivo: string | null;
}

/** Modulo da ementa como a tela o le. */
export interface ModuloLido {
  readonly titulo: string;
  readonly topicos: readonly string[];
  readonly carga_horaria: number | null;
}

/** Curso estruturado na forma que a tela de revisao consome. */
export interface CursoEstruturadoLido {
  readonly tema: string | null;
  readonly nicho: string | null;
  readonly publico_alvo: string | null;
  readonly numero_participantes: number | null;
  readonly carga_horaria: number | null;
  readonly formato: string | null;
  readonly objetivos_aprendizagem: readonly string[];
  readonly ementa: readonly ModuloLido[];
  readonly campos_ausentes: readonly LacunaLida[];
  readonly observacoes: readonly string[];
}

function ehObjeto(valor: JsonValue | undefined): valor is JsonObject {
  return typeof valor === 'object' && valor !== null && !Array.isArray(valor);
}

function itens(valor: JsonValue | undefined): readonly JsonValue[] {
  return Array.isArray(valor) ? valor : [];
}

/** Texto nao vazio, ou `null`. Espaco em branco e tratado como ausencia. */
function texto(valor: JsonValue | undefined): string | null {
  if (typeof valor !== 'string') {
    return null;
  }

  const limpo = valor.trim();

  return limpo === '' ? null : limpo;
}

/**
 * Numero positivo, ou `null`.
 *
 * Zero nao e ausencia por acaso: o contrato declara carga horaria e numero de
 * participantes como positivos, e exibir "0 horas" faria o operador ler como
 * dado confirmado o que e falta de dado.
 */
function numeroPositivo(valor: JsonValue | undefined): number | null {
  if (typeof valor !== 'number' || !Number.isFinite(valor) || valor <= 0) {
    return null;
  }

  return valor;
}

function textos(valor: JsonValue | undefined): readonly string[] {
  return itens(valor)
    .map((item) => texto(item))
    .filter((item): item is string => item !== null);
}

function modulos(valor: JsonValue | undefined): readonly ModuloLido[] {
  return itens(valor)
    .map((item): ModuloLido | null => {
      if (!ehObjeto(item)) {
        // Modulo em texto puro ainda e informacao: vale como titulo.
        const titulo = texto(item);

        return titulo === null ? null : { titulo, topicos: [], carga_horaria: null };
      }

      const titulo = texto(item.titulo);

      return titulo === null
        ? null
        : {
            titulo,
            topicos: textos(item.topicos),
            carga_horaria: numeroPositivo(item.carga_horaria),
          };
    })
    .filter((item): item is ModuloLido => item !== null);
}

function tipoDeLacuna(valor: JsonValue | undefined): GapKind | null {
  const declarado = texto(valor);

  return GAP_KINDS.find((tipo) => tipo === declarado) ?? null;
}

function lacunas(valor: JsonValue | undefined): readonly LacunaLida[] {
  return itens(valor)
    .map((item): LacunaLida | null => {
      if (!ehObjeto(item)) {
        return null;
      }

      const campo = texto(item.campo);

      return campo === null
        ? null
        : {
            campo,
            tipo: tipoDeLacuna(item.tipo),
            tipoDeclarado: texto(item.tipo) ?? '',
            motivo: texto(item.motivo),
          };
    })
    .filter((item): item is LacunaLida => item !== null);
}

/** Traduz o conteudo da versao do artefato para a forma que a tela consome. */
export function lerCursoEstruturado(content: JsonObject): CursoEstruturadoLido {
  return {
    tema: texto(content.tema),
    nicho: texto(content.nicho),
    publico_alvo: texto(content.publico_alvo),
    numero_participantes: numeroPositivo(content.numero_participantes),
    carga_horaria: numeroPositivo(content.carga_horaria),
    formato: texto(content.formato),
    objetivos_aprendizagem: textos(content.objetivos_aprendizagem),
    ementa: modulos(content.ementa),
    campos_ausentes: lacunas(content.campos_ausentes),
    observacoes: textos(content.observacoes),
  };
}
