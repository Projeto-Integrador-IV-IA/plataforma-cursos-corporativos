import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProcessingMessage } from '@/components/ProcessingMessage';

describe('mensagem de processamento', () => {
  it('sinaliza a operacao em curso', () => {
    render(<ProcessingMessage operation="restauracao da versao" />);

    const message = screen.getByRole('status', {
      name: 'Processando: restauracao da versao…',
    });

    expect(message.getAttribute('aria-busy')).toBe('true');
  });
});
