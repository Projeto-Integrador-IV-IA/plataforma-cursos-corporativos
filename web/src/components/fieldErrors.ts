import { isApiError } from '@/services/api';

export type FieldErrors = Readonly<Record<string, string | undefined>>;

interface ValidationIssue {
  readonly location?: readonly unknown[];
  readonly message?: unknown;
}

function isValidationIssue(value: unknown): value is ValidationIssue {
  return typeof value === 'object' && value !== null;
}

/** Extrai os erros de campo do envelope 422 padronizado pela plataforma. */
export function fieldErrorsFrom(error: unknown): FieldErrors {
  if (!isApiError(error) || error.status !== 422) return {};

  const issues = error.details?.issues;
  if (!Array.isArray(issues)) return {};

  const mapped: Record<string, string> = {};
  for (const candidate of issues) {
    if (!isValidationIssue(candidate) || !Array.isArray(candidate.location)) continue;
    const field = [...candidate.location]
      .reverse()
      .find((part): part is string => typeof part === 'string' && part !== 'body');
    if (field !== undefined && typeof candidate.message === 'string') {
      mapped[field] ??= candidate.message;
    }
  }

  return mapped;
}

export function hasFieldErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0;
}
