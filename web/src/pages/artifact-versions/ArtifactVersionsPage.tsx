/**
 * Historico de versoes de um artefato (RF08).
 *
 * Versoes sao append-only (RNF09): esta tela le, nunca sobrescreve.
 *
 * TODO(RF08): consumir GET /api/v1/artifacts/{id}/versions.
 */

import { useParams } from 'react-router-dom';

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function ArtifactVersionsPage() {
  const { artifactId } = useParams<{ artifactId: string }>();

  return (
    <PagePlaceholder
      title="Versoes do artefato"
      requirements={['RF08']}
      description={`Historico append-only de versoes do artefato ${artifactId ?? ''}.`}
    />
  );
}
