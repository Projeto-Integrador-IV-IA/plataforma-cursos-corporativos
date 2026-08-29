/**
 * Tela de autenticacao (RF16).
 *
 * Unica rota publica da aplicacao: todas as demais exigem sessao (RNF10).
 *
 * TODO(RF16): implementar o formulario e a troca de credenciais por token
 * junto ao gateway-service.
 */

import { PagePlaceholder } from '@/components/PagePlaceholder';

export function LoginPage() {
  return (
    <PagePlaceholder
      title="Entrar"
      requirements={['RF16']}
      description="Autenticacao do operador junto ao gateway-service."
    />
  );
}
