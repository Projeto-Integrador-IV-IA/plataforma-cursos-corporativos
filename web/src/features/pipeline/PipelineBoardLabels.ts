/**
 * Rotulos do quadro do pipeline (RF05).
 *
 * Os nomes de etapa e situacao vem de `features/demands/DemandListLabels`:
 * quadro e listagem mostram as mesmas demandas, e escrever "Captacao" num
 * lugar e "Prospeccao" no outro faria o operador duvidar se sao a mesma coisa.
 * Aqui ficam somente as contagens, que sao proprias do quadro.
 */

/** Quantidade de demandas em texto, no singular ou no plural. */
export function demandCount(total: number): string {
  return total === 1 ? '1 demanda' : `${total} demandas`;
}

/**
 * Contagem do cabecalho da coluna.
 *
 * Mostra sempre o total da etapa, que vem do servidor, e nao `items.length`:
 * cada coluna traz no maximo `limit` cartoes, entao contar os cartoes na tela
 * esconderia demandas que existem. Quando o recorte corta, o texto diz quantas
 * ficaram de fora em vez de deixar a diferenca invisivel.
 */
export function stageCount(shown: number, total: number): string {
  return shown < total ? `Mostrando ${shown} de ${demandCount(total)}` : demandCount(total);
}
