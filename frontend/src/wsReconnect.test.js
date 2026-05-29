import { describe, expect, it } from 'vitest';
import {
  classifyClose,
  getReconnectDelay,
  parseWsMessage,
  shouldStopReconnecting,
  MAX_RECONNECT_ATTEMPTS,
} from './wsReconnect';

describe('getReconnectDelay', () => {
  it('exponential backoff capped at max', () => {
    expect(getReconnectDelay(1)).toBe(500);
    expect(getReconnectDelay(3)).toBe(2000);
    expect(getReconnectDelay(10)).toBe(5000);
  });
});

describe('classifyClose', () => {
  it('normal close is not recoverable', () => {
    expect(classifyClose({ code: 1000, reason: '' }).recoverable).toBe(false);
  });

  it('room_full code is fatal', () => {
    const info = classifyClose({ code: 1008, reason: 'room_full' });
    expect(info.recoverable).toBe(false);
    expect(info.type).toBe('room_full');
  });

  it('already_in_game code is fatal', () => {
    const info = classifyClose({ code: 1008, reason: 'already_in_game' });
    expect(info.type).toBe('already_in_game');
  });

  it('room_not_found code is fatal', () => {
    const info = classifyClose({ code: 1008, reason: 'room_not_found' });
    expect(info.type).toBe('room_not_found');
  });

  it('unknown disconnect is recoverable', () => {
    expect(classifyClose({ code: 1006, reason: '' }).recoverable).toBe(true);
  });
});

describe('parseWsMessage', () => {
  it('accepts object payloads', () => {
    expect(parseWsMessage('{"status":"ok"}').ok).toBe(true);
  });

  it('rejects arrays', () => {
    expect(parseWsMessage('[]').ok).toBe(false);
  });

  it('rejects invalid json', () => {
    expect(parseWsMessage('not-json').ok).toBe(false);
  });
});

describe('shouldStopReconnecting', () => {
  it(`stops after ${MAX_RECONNECT_ATTEMPTS} attempts`, () => {
    expect(shouldStopReconnecting(MAX_RECONNECT_ATTEMPTS)).toBe(false);
    expect(shouldStopReconnecting(MAX_RECONNECT_ATTEMPTS + 1)).toBe(true);
  });
});
