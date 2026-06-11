import { describe, expect, it } from 'vitest';
import { hintMatchesSelection } from './messageHandlers';

describe('hintMatchesSelection', () => {
  const select53 = () => ({ moveFrom: 53, chainCell: null });
  const chain19 = () => ({ moveFrom: null, chainCell: 19 });

  it('accepts when server omits hint_position (legacy)', () => {
    expect(hintMatchesSelection({ essential_positions: [10] }, select53)).toBe(true);
  });

  it('accepts when hint_position matches moveFrom', () => {
    expect(hintMatchesSelection({ hint_position: 53 }, select53)).toBe(true);
  });

  it('accepts when hint_position matches chainCell', () => {
    expect(hintMatchesSelection({ hint_position: 19 }, chain19)).toBe(true);
  });

  it('rejects when hint_position mismatches moveFrom', () => {
    expect(hintMatchesSelection({ hint_position: 48 }, select53)).toBe(false);
  });

  it('rejects when hint_position mismatches chainCell', () => {
    expect(hintMatchesSelection({ hint_position: 33 }, chain19)).toBe(false);
  });

  it('rejects when hint_position set but nothing selected', () => {
    expect(hintMatchesSelection({ hint_position: 53 }, () => ({ moveFrom: null, chainCell: null }))).toBe(false);
  });

  it('prefers moveFrom over chainCell when both set', () => {
    expect(hintMatchesSelection(
      { hint_position: 53 },
      () => ({ moveFrom: 53, chainCell: 19 }),
    )).toBe(true);
    expect(hintMatchesSelection(
      { hint_position: 19 },
      () => ({ moveFrom: 53, chainCell: 19 }),
    )).toBe(false);
  });

  it('treats string hint_position as number', () => {
    expect(hintMatchesSelection({ hint_position: '53' }, select53)).toBe(true);
  });

  it('accepts invalid hint_position as legacy (NaN)', () => {
    expect(hintMatchesSelection({ hint_position: 'nope' }, select53)).toBe(true);
  });

  it('accepts when getSelection is missing', () => {
    expect(hintMatchesSelection({ hint_position: 99 }, undefined)).toBe(true);
  });
});
