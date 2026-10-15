/**
 * Cartao da demanda no quadro do pipeline (RF05).
 *
 * Unidade visual da coluna. Em poucos centimetros precisa dizer de quem e a
 * negociacao, do que ela trata, quem a conduz e em que situacao esta - cliente,
 * titulo, responsavel e situacao, nesta ordem de leitura. O resto (contexto,
 * fontes, artefatos, historico) fica no detalhe, que e onde o cartao leva.
 *
 * O cartao inteiro e um unico link para o detalhe da demanda. Nao e um bloco
 * com um link dentro: alvo de clique do tamanho do cartao evita a mira no
 * titulo, e um unico elemento interativo por cartao mantem a tabulacao
 * previsivel - o teclado anda de demanda em demanda, nao de pedaco em pedaco.
 *
 * Demanda que exige atencao: a que esta sem responsavel. E o sinal que os dados
 * do quadro sustentam hoje sem inventar regra. "Parada ha N dias" seria o outro
 * candidato natural, e nao entra por decisao consciente: o prazo aceitavel de
 * cada etapa e regra de negocio: ela pertence ao pipeline-service (RF05, RF06),
 * e um limite escolhido aqui faria o quadro acusar atraso que o servico nao
 * reconhece.
 *
 * O sinal nao depende so de cor (nem o daltonico nem a impressao em preto e
 * branco perdem o aviso): o lugar do responsavel passa a dizer "Sem responsavel
 * definido", com um marcador textual antes, e o cartao ganha borda mais grossa
 * do lado esquerdo. Cor, forma e texto dizem a mesma coisa.
 */

import { Link } from 'react-router-dom';

import { buildPath } from '@/app/paths';
import { STATUS_LABELS } from '@/features/demands/DemandListLabels';
import type { PipelineCardRead } from '@/types/api';

interface PipelineCardProps {
  readonly card: PipelineCardRead;
}

export function PipelineCard({ card }: PipelineCardProps) {
  // Sem responsavel ninguem conduz a negociacao: e o que o quadro precisa
  // destacar para o operador agir.
  const needsAttention = card.owner === null;
  const className = needsAttention ? 'pipeline-card pipeline-card--attention' : 'pipeline-card';

  return (
    <Link className={className} to={buildPath.demandDetail(card.id)}>
      <span className="pipeline-card__client">{card.client.name}</span>
      <span className="pipeline-card__title">{card.title}</span>
      <span className="pipeline-card__meta">
        <span
          className={`pipeline-card__status pipeline-card__status--${card.status.toLowerCase()}`}
        >
          {STATUS_LABELS[card.status]}
        </span>
        {card.owner === null ? (
          <span className="pipeline-card__attention">
            <span className="pipeline-card__attention-mark" aria-hidden="true">
              !
            </span>
            Sem responsavel definido
          </span>
        ) : (
          <span className="pipeline-card__owner">{card.owner.name}</span>
        )}
      </span>
    </Link>
  );
}
