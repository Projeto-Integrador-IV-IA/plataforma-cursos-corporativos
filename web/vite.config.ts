// Configuracao do bundler do frontend.
// A URL da API vem de VITE_API_BASE_URL (RNF11) - nunca fixada no codigo.
// TODO(scaffolding): revisar proxy de desenvolvimento quando o gateway existir.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
