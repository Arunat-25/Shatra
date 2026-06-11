import { describe, expect, it, vi } from 'vitest';
import { formatGameOverMessage } from './utils';

vi.mock('./i18n', () => ({
  default: {
    t: (key) => key,
  },
}));

vi.mock('./i18n/resolveMessage', () => ({
  resolveMessageCode: (code) => code,
}));

describe('formatGameOverMessage timeout', () => {
  it('names the player who ran out of time, not the winner', () => {
    expect(formatGameOverMessage('черный', 'timeout')).toBe('result.timeoutWhite');
    expect(formatGameOverMessage('белый', 'timeout')).toBe('result.timeoutBlack');
  });
});
