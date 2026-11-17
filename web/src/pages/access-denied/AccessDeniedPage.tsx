export function AccessDeniedPage() {
  return (
    <section className="page">
      <header className="page__header">
        <h1 className="page__title">Acesso nao autorizado</h1>
      </header>
      <p className="page__description">
        Seu perfil nao pode acessar esta tela. Esta verificacao visual nao substitui a autorizacao
        feita pelo servidor.
      </p>
    </section>
  );
}
