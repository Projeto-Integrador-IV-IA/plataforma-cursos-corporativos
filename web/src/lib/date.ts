/**
 * Utilitário único para formatação de datas e horários no frontend (RNF17).
 * Fuso horário padrão de exibição: America/Sao_Paulo (Horário de Brasília - UTC-3).
 * O armazenamento no backend permanece estritamente normalizado em UTC (ISO 8601).
 */

export const DEFAULT_TIMEZONE = 'America/Sao_Paulo';
export const DEFAULT_LOCALE = 'pt-BR';

/**
 * Formata um timestamp/ISO string em data e hora amigáveis.
 * Exemplo de saída: "28/10/2026 14:30"
 */
export function formatDateTime(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return '-';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '-';

  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: DEFAULT_TIMEZONE,
  }).format(date);
}

/**
 * Formata apenas a data.
 * Exemplo de saída: "28/10/2026"
 */
export function formatDateOnly(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return '-';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '-';

  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: DEFAULT_TIMEZONE,
  }).format(date);
}
