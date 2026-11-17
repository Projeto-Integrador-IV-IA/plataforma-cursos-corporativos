import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProcessingMessage } from '@/components/ProcessingMessage';

describe('mensagem de processamento', () => {
  it('sinaliza a operacao em curso para pessoa e tecnologia assistiva', () => {
    render(<ProcessingMessage operation="salvamento do cadastro" />);

    const mensagem = screen.getByRole('status', { name: 'Processando: salvamento do cadastro…' });

    expect(mensagem.getAttribute('aria-busy')).toBe('true');
    expect(mensagem.className).toContain('processing-message');
  });
});
