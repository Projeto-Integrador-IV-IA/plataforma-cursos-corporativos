import { describe, expect, it } from 'vitest';

import { ApiError } from '@/services/api';
import { fieldErrorsFrom } from '@/components/fieldErrors';

describe('fieldErrorsFrom', () => {
  it('maps the API 422 locations to form field names', () => {
    const error = new ApiError({
      kind: 'http',
      code: 'VALIDATION_ERROR',
      message: 'Dados invalidos.',
      status: 422,
      details: {
        issues: [
          { location: ['body', 'name'], message: 'Informe o nome.' },
          { location: ['body', 'contact_email'], message: 'E-mail invalido.' },
        ],
      },
    });

    expect(fieldErrorsFrom(error)).toEqual({
      name: 'Informe o nome.',
      contact_email: 'E-mail invalido.',
    });
  });

  it('does not turn non-validation errors into field errors', () => {
    const error = new ApiError({
      kind: 'http',
      code: 'CONFLICT',
      message: 'Conflito.',
      status: 409,
    });

    expect(fieldErrorsFrom(error)).toEqual({});
  });
});
