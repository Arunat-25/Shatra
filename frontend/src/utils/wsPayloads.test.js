import { describe, expect, it } from 'vitest';
import { buildHintPayload, isHintWsMessage } from './wsPayloads';

describe('wsPayloads hints', () => {
  it('buildHintPayload sends position only', () => {
    expect(buildHintPayload(53)).toEqual({ position: 'position53' });
  });

  it('isHintWsMessage detects hint requests', () => {
    expect(isHintWsMessage({ position: 'position53' })).toBe(true);
    expect(isHintWsMessage({
      position: 'position53',
      move_from: 'position1',
      move_to: 'position2',
      board: {},
    })).toBe(false);
    expect(isHintWsMessage({
      move_from: 'position1',
      move_to: 'position2',
      board: {},
      movers_color: 'белый',
    })).toBe(false);
  });

  it('isHintWsMessage rejects move_from-only payloads', () => {
    expect(isHintWsMessage({ position: 'position10', move_from: 'position10' })).toBe(false);
  });

  it('buildHintPayload works for edge cells', () => {
    expect(buildHintPayload(1)).toEqual({ position: 'position1' });
    expect(buildHintPayload(64)).toEqual({ position: 'position64' });
  });
});
