/**
 * Estrutura gerada pela IA, apresentada por inteiro (RF19).
 *
 * A tela mostra a estrutura toda antes de qualquer decisao de revisao: campo
 * extraido da demanda (RF11), campo gerado (RF12) e observacao do modelo
 * aparecem juntos, sem aba e sem recorte. Aprovar ou devolver o que nao se leu
 * inteiro seria aprovar no automatico - exatamente o que esta tela existe para
 * impedir (RF14).
 *
 * Campo sem valor utilizavel aparece como ausencia declarada, e nao como linha
 * em branco: a IA nunca inventa valor, entao o vazio aqui e informacao e tem
 * de ser lido como tal.
 *
 * Campo apontado em `campos_ausentes` vem destacado no lugar onde e lido, com
 * o tipo da lacuna e o motivo (RF15): quem confere o campo precisa ver ali,
 * junto do valor, que aquele valor nao foi confirmado por ninguem.
 *
 * O que esta tela nao faz: editar os campos (#101) e decidir sobre a estrutura
 * - aprovar, rejeitar ou devolver (#102). Sao cards proprios.
 */

import { SEM_INFORMACAO } from '@/features/demands/DemandDetailLabels';
import { DemandStructuringGapNote } from '@/features/demands/DemandStructuringGaps';
import { classesDoDestaque, lacunasDoCampo } from '@/features/demands/DemandStructuringGapStyles';
import {
  formatarCargaHoraria,
  formatarParticipantes,
  rotuloDoCampo,
  rotuloDoFormato,
} from '@/features/demands/DemandStructuringLabels';
import type {
  CampoDoCurso,
  CursoEstruturadoLido,
} from '@/features/demands/StructuredCourseContent';
import type { FieldOrigin, SourceSegmentRead } from '@/types/api';

/** Campos de valor unico, na ordem canonica do contrato. */
const ESCALARES: readonly CampoDoCurso[] = [
  'tema',
  'nicho',
  'publico_alvo',
  'numero_participantes',
  'carga_horaria',
  'formato',
];

/** Valor de um campo de valor unico, ja formatado com a unidade quando tem. */
function valorDoCampo(curso: CursoEstruturadoLido, campo: CampoDoCurso): string | null {
  if (campo === 'tema') return curso.tema;
  if (campo === 'nicho') return curso.nicho;
  if (campo === 'publico_alvo') return curso.publico_alvo;
  if (campo === 'numero_participantes') {
    return curso.numero_participantes === null
      ? null
      : formatarParticipantes(curso.numero_participantes);
  }
  if (campo === 'carga_horaria') {
    return curso.carga_horaria === null ? null : formatarCargaHoraria(curso.carga_horaria);
  }
  if (campo === 'formato') {
    return curso.formato === null ? null : rotuloDoFormato(curso.formato);
  }

  return null;
}

interface DemandStructuringCourseProps {
  course: CursoEstruturadoLido;
  segments: readonly SourceSegmentRead[];
}

function textoDaProcedencia(origin: FieldOrigin | undefined, hasEvidence: boolean): string {
  if (origin === 'extraido') return 'Extraido da fonte';
  if (origin === 'inferido') return hasEvidence ? 'Inferido pela IA' : 'Inferido sem evidencia';

  return hasEvidence ? 'Procedencia nao declarada' : 'Sem valor utilizavel';
}

function classeDoCampo(course: CursoEstruturadoLido, field: CampoDoCurso, hasValue: boolean): string {
  const evidence = course.evidencias[field] ?? [];
  const origin = course.procedencia[field];

  if (!hasValue || origin === 'ausente') return 'structuring-course__field--absent';
  if (evidence.length === 0) return 'structuring-course__field--inferred';

  return 'structuring-course__field--evidenced';
}

function EvidenceNote({
  course,
  field,
  segments,
  hasValue,
}: {
  course: CursoEstruturadoLido;
  field: CampoDoCurso;
  segments: readonly SourceSegmentRead[];
  hasValue: boolean;
}) {
  const numbers = course.evidencias[field] ?? [];
  const origin = course.procedencia[field];

  return (
    <div className={`structuring-course__evidence${numbers.length === 0 ? ' structuring-course__evidence--missing' : ''}`}>
      <strong>{textoDaProcedencia(origin, numbers.length > 0)}</strong>
      {hasValue && numbers.length === 0 ? <span>Sem trecho citado.</span> : null}
      {numbers.length > 0 ? (
        <ul>
          {numbers.map((number) => {
            const segment = segments.find((item) => item.position === number);

            return (
              <li key={number}>
                Trecho [{number}]: {segment?.content ?? 'trecho nao disponivel'}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

export function DemandStructuringCourse({ course, segments }: DemandStructuringCourseProps) {
  const lacunasDosObjetivos = lacunasDoCampo(course.campos_ausentes, 'objetivos_aprendizagem');
  const lacunasDaEmenta = lacunasDoCampo(course.campos_ausentes, 'ementa');

  return (
    <div className="structuring-course">
      <dl className="structuring-course__fields">
        {ESCALARES.map((campo) => {
          const valor = valorDoCampo(course, campo);
          const lacunas = lacunasDoCampo(course.campos_ausentes, campo);

          return (
            <div
              className={`structuring-course__field ${classeDoCampo(course, campo, valor !== null)}${classesDoDestaque(lacunas)}`}
              key={campo}
            >
              <dt className="structuring-course__term">{rotuloDoCampo(campo)}</dt>
              <dd className="structuring-course__value">
                {valor ?? SEM_INFORMACAO}
                {lacunas.map((lacuna, indice) => (
                  <DemandStructuringGapNote key={`${indice}-${lacuna.tipoDeclarado}`} lacuna={lacuna} />
                ))}
                <EvidenceNote
                  course={course}
                  field={campo}
                  segments={segments}
                  hasValue={valor !== null}
                />
              </dd>
            </div>
          );
        })}
      </dl>

      <section
        className={`structuring-course__block ${classeDoCampo(course, 'objetivos_aprendizagem', course.objetivos_aprendizagem.length > 0)}${classesDoDestaque(lacunasDosObjetivos)}`}
        aria-labelledby="estrutura-objetivos"
      >
        <h3 className="structuring-course__block-title" id="estrutura-objetivos">
          {rotuloDoCampo('objetivos_aprendizagem')}
        </h3>
        {lacunasDosObjetivos.map((lacuna, indice) => (
          <DemandStructuringGapNote key={`${indice}-${lacuna.tipoDeclarado}`} lacuna={lacuna} />
        ))}
        <EvidenceNote
          course={course}
          field="objetivos_aprendizagem"
          segments={segments}
          hasValue={course.objetivos_aprendizagem.length > 0}
        />
        {course.objetivos_aprendizagem.length === 0 ? (
          <p className="demand-detail__empty">
            A estrutura nao traz objetivos de aprendizagem. Confirme com o cliente o que o
            participante precisa saber fazer ao final.
          </p>
        ) : (
          <ol className="structuring-course__list">
            {course.objetivos_aprendizagem.map((objetivo) => (
              <li key={objetivo}>{objetivo}</li>
            ))}
          </ol>
        )}
      </section>

      <section
        className={`structuring-course__block ${classeDoCampo(course, 'ementa', course.ementa.length > 0)}${classesDoDestaque(lacunasDaEmenta)}`}
        aria-labelledby="estrutura-ementa"
      >
        <h3 className="structuring-course__block-title" id="estrutura-ementa">
          {rotuloDoCampo('ementa')}
        </h3>
        {lacunasDaEmenta.map((lacuna, indice) => (
          <DemandStructuringGapNote key={`${indice}-${lacuna.tipoDeclarado}`} lacuna={lacuna} />
        ))}
        <EvidenceNote
          course={course}
          field="ementa"
          segments={segments}
          hasValue={course.ementa.length > 0}
        />
        {course.ementa.length === 0 ? (
          <p className="demand-detail__empty">
            A estrutura nao traz modulos de ementa. O conteudo do treinamento ainda precisa ser
            acordado com o cliente.
          </p>
        ) : (
          <ol className="structuring-course__modules">
            {course.ementa.map((modulo, indice) => (
              <li className="structuring-course__module" key={`${indice}-${modulo.titulo}`}>
                <p className="structuring-course__module-title">
                  {modulo.titulo}
                  {modulo.carga_horaria === null ? null : (
                    <span className="structuring-course__module-load">
                      {' '}
                      — {formatarCargaHoraria(modulo.carga_horaria)}
                    </span>
                  )}
                </p>
                {modulo.topicos.length === 0 ? (
                  <p className="structuring-course__module-empty">Modulo sem topicos descritos.</p>
                ) : (
                  <ul className="structuring-course__topics">
                    {modulo.topicos.map((topico) => (
                      <li key={topico}>{topico}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>

      {course.observacoes.length === 0 ? null : (
        <section className="structuring-course__block" aria-labelledby="estrutura-observacoes">
          <h3 className="structuring-course__block-title" id="estrutura-observacoes">
            Observacoes do modelo
          </h3>
          <ul className="structuring-course__list">
            {course.observacoes.map((observacao) => (
              <li key={observacao}>{observacao}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
