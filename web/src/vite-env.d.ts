/// <reference types="vite/client" />

/**
 * Variaveis de ambiente do frontend (RNF11).
 *
 * Declarar aqui e o que faz `import.meta.env.VITE_API_BASE_URL` ser `string` em
 * vez de tipo solto: variavel nova exige uma linha nesta interface e outra em
 * `.env.example`. Apenas o prefixo `VITE_` chega ao navegador - nunca coloque
 * segredo nestas variaveis.
 */
interface ImportMetaEnv {
  /** URL base do gateway, ja com o prefixo de versao. Ex.: `http://localhost:8000/api/v1`. */
  readonly VITE_API_BASE_URL: string;
}
