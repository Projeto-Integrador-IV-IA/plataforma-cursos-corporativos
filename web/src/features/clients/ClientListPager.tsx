/**
 * Navegacao entre paginas da listagem de clientes (RF03).
 *
 * Dois botoes e a posicao dita em texto, como no paginador de demandas: a
 * carteira cabe em poucas paginas e uma regua de numeros so acrescentaria
 * alvos de clique.
 *
 * A posicao vive num `aria-live="polite"`: quem navega por teclado ouve
 * "Pagina 2 de 4" ao avancar, sem perder o foco do botao que acabou de
 * pressionar. Os botoes ficam desabilitados enquanto a proxima pagina nao
 * chega, para dois cliques seguidos nao pularem uma pagina.
 */

interface ClientListPagerProps {
  /** Pagina corrente, contada a partir de 1. */
  readonly page: number;
  readonly totalPages: number;
  /** Total de clientes cadastrados, nao o tamanho da pagina. */
  readonly total: number;
  /** Verdadeiro enquanto a proxima pagina nao chegou. */
  readonly loading: boolean;
  readonly onPageChange: (page: number) => void;
}

function clientCount(total: number): string {
  return total === 1 ? '1 cliente' : `${total} clientes`;
}

export function ClientListPager({
  page,
  totalPages,
  total,
  loading,
  onPageChange,
}: ClientListPagerProps) {
  return (
    <nav className="client-list__pager" aria-label="Paginacao dos clientes">
      <button
        type="button"
        className="button"
        disabled={page <= 1 || loading}
        onClick={() => onPageChange(page - 1)}
      >
        Pagina anterior
      </button>
      <p className="client-list__position" aria-live="polite">
        Pagina {page} de {totalPages} — {clientCount(total)}
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
