// Configuracao do bundler do frontend.
// A URL da API vem de VITE_API_BASE_URL (RNF11) - nunca fixada no codigo.
// O alias `@` espelha `paths` do tsconfig.json: os dois precisam andar juntos,
// senao o import compila e quebra em execucao.
// TODO(scaffolding): revisar proxy de desenvolvimento quando o gateway existir.
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
