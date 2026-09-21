/**
 * Navegacao entre paginas da listagem de demandas (RF03).
 *
 * Dois botoes e uma posicao dita em texto. Nada de "…" com numeros de pagina:
 * o total de demandas de uma negociadora cabe em poucas paginas e a lista de
 * numeros so acrescenta alvos de clique.
 *
 * A posicao vive num `aria-live="polite"`: quem navega por teclado ouve
 * "Pagina 2 de 4" ao avancar, sem perder o foco do botao que acabou de
 * pressionar.
 */

interface DemandListPagerProps {
  /** Pagina corrente, contada a partir de 1. */
  readonly page: number;
  readonly totalPages: number;
  /** Total de demandas que atendem ao filtro, nao o tamanho da pagina. */
  readonly total: number;
  /** Verdadeiro enquanto a proxima pagina nao chegou. */
  readonly loading: boolean;
  readonly onPageChange: (page: number) => void;
}

function demandCount(total: number): string {
  return total === 1 ? '1 demanda' : `${total} demandas`;
}

export function DemandListPager({
  page,
  totalPages,
  total,
  loading,
  onPageChange,
}: DemandListPagerProps) {
  return (
    <nav className="demand-list__pager" aria-label="Paginacao das demandas">
      <button
        type="button"
        className="button"
        disabled={page <= 1 || loading}
        onClick={() => onPageChange(page - 1)}
      >
        Pagina anterior
      </button>
      <p className="demand-list__position" aria-live="polite">
        Pagina {page} de {totalPages} — {demandCount(total)}
      </p>
      <button
        type="button"
        className="button"
        disabled={page >= totalPages || loading}
        onClick={() => onPageChange(page + 1)}
      >
        Proxima pagina
      </button>
    </nav>
  );
}
