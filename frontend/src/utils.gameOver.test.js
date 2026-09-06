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

describe('formatGameOverMessage draw reasons', () => {
  it('uses distinct text for rule-based draws', () => {
    expect(formatGameOverMessage('', 'draw_repetition')).toBe('result.drawRepetition');
    expect(formatGameOverMessage('', 'draw.two_biys')).toBe('result.drawTwoBiys');
    expect(formatGameOverMessage('', 'draw_agreed')).toBe('result.drawAgreed');
  });
});
