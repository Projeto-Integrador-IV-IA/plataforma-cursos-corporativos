/**
 * Fontes captadas da demanda (RF09), vistas a partir do detalhe.
 *
 * A secao existe, mas vazia de proposito: nao ha nenhuma operacao de
 * `raw_inputs` declarada em `packages/contracts/openapi/` ate agora. Inventar
 * aqui uma chamada para uma rota que o contrato nao declara iria contra RNF02
 * e quebraria no primeiro ambiente com servico de verdade.
 *
 * Esconder a secao seria pior que mostra-la vazia: quem opera precisa saber
 * que a demanda ainda nao tem fonte registrada - e que o texto de contexto
 * acima nao e a fonte, e sim o resumo escrito pelo proprio operador.
 *
 * TODO(RF09): listar as fontes captadas (`raw_inputs`) da demanda, com
 * procedencia, data e o indicador de conteudo truncado, assim que a operacao
 * de captacao for publicada no contrato.
 */

import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import type { Uuid } from '@/types/api';

interface DemandDetailSourcesProps {
  demandId: Uuid;
}

export function DemandDetailSources({ demandId }: DemandDetailSourcesProps) {
  return (
    <>
      <p className="demand-detail__empty">
        A listagem das fontes captadas ainda nao esta disponivel: o servico nao publicou a operacao
        que as devolve.
      </p>
      <p className="page__description">
        <Link to={buildPath.demandIngestion(demandId)}>Registrar uma fonte na captacao</Link>
      </p>
    </>
  );
}
