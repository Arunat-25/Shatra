import { describe, expect, it } from 'vitest';
import {
  resolveMessage,
  resolveMessageCode,
  resolveWsErrorMessage,
  resolveApiErrorMessage,
} from './resolveMessage';

describe('resolveMessageCode', () => {
  it('maps turn.now with color param', () => {
    const text = resolveMessageCode('turn.now', { color: 'белый' });
    expect(text).toContain('бел');
  });

  it('maps room close codes', () => {
    expect(resolveMessageCode('room_full')).toBe('Комната уже заполнена');
    expect(resolveMessageCode('already_in_game')).toContain('вкладке');
  });
});

describe('resolveMessage', () => {
  it('resolves payload with message_code', () => {
    expect(resolveMessage({ message_code: 'cancel.opponent' })).toBe('Соперник отменил игру.');
  });

  it('resolves plain code string', () => {
    expect(resolveMessage('draw.agreed')).toContain('Ничья');
  });

  it('returns empty for missing input', () => {
    expect(resolveMessage(null)).toBe('');
  });
});

describe('resolveWsErrorMessage', () => {
  it('maps room_not_found close code', () => {
    expect(resolveWsErrorMessage('room_not_found')).toBe('Комната не найдена');
  });
});

describe('resolveMessage chat errors', () => {
  it('maps chat.rate_limit', () => {
    expect(resolveMessage({ message_code: 'chat.rate_limit' }))
      .toContain('много');
  });

  it('maps chat.duplicate', () => {
    expect(resolveMessage({ message_code: 'chat.duplicate' }))
      .toContain('подряд');
  });
});

describe('resolveApiErrorMessage', () => {
  it('maps auth.invalid_credentials', () => {
    expect(resolveApiErrorMessage('auth.invalid_credentials'))
      .toBe('Неверное имя пользователя или пароль');
  });
});
