/**
 * Cliente HTTP do gateway.
 *
 * Ponto unico de saida da aplicacao para a rede. Nenhum componente chama
 * `fetch` diretamente.
 *
 * Responsabilidades:
 *  - ler a URL base de `VITE_API_BASE_URL` (RNF11);
 *  - anexar o token de acesso em toda requisicao autenticada (RF16);
 *  - traduzir o corpo de erro padronizado da plataforma em erro tipado,
 *    conforme `packages/contracts/schemas/error.schema.json`;
 *  - aplicar timeouts distintos: operacoes de CRM seguem o alvo de RNF07,
 *    a estruturacao por IA segue o de RNF06 (ate 15 s);
 *  - redirecionar ao login quando o token expira.
 *
 * TODO(scaffolding): implementar.
 */

export {};
