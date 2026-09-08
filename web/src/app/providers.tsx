/**
 * Providers globais da aplicacao.
 *
 * Hoje monta apenas o cliente de dados, responsavel por cache e revalidacao
 * das chamadas ao gateway. O `QueryClient` e criado uma vez por montagem para
 * que cada teste tenha cache proprio e nao contamine o seguinte.
 *
 * TODO(RF16): adicionar o contexto de autenticacao (token e usuario corrente).
 * TODO(RF17): adicionar o contexto de notificacoes de processamento.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useState } from 'react';

interface ProvidersProps {
  children: ReactNode;
}

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: 1, refetchOnWindowFocus: false },
    },
  });
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(createQueryClient);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
