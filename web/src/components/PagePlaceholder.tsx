/**
 * Moldura de tela ainda nao implementada.
 *
 * Existe para que a estrutura de rotas seja navegavel e conferivel antes das
 * telas reais (RNF01). Cada uso declara o requisito que a tela vai atender,
 * mantendo a rastreabilidade visivel na propria interface.
 */

interface PagePlaceholderProps {
  /** Titulo da tela, como aparece na navegacao. */
  title: string;
  /** IDs dos requisitos que esta tela atende. Ex.: ['RF01', 'RF03']. */
  requirements: readonly string[];
  /** O que a tela vai fazer quando implementada. */
  description: string;
}

export function PagePlaceholder({ title, requirements, description }: PagePlaceholderProps) {
  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">{title}</h1>
        <p className="page__requirements">
          {requirements.map((requirement) => (
            <span key={requirement} className="tag">
              {requirement}
            </span>
          ))}
        </p>
      </header>
      <p className="page__description">{description}</p>
      <p className="page__pending">Tela ainda nao implementada.</p>
    </section>
  );
}
