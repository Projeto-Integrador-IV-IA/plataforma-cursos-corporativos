/**
 * Setup da suite de testes.
 *
 * Com `globals: false` no vitest, a Testing Library nao consegue registrar sua
 * limpeza automatica sozinha - sem isto, um render vaza para o teste seguinte e
 * as consultas encontram elementos duplicados.
 */

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(cleanup);
