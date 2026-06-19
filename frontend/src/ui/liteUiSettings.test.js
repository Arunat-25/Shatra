import { describe, expect, it, beforeEach } from 'vitest';
import { isLiteUiEnabled, setLiteUiEnabled, LITE_UI_KEY } from './liteUiSettings';

describe('liteUiSettings', () => {
  beforeEach(() => {
    localStorage.removeItem(LITE_UI_KEY);
  });

  it('defaults to disabled', () => {
    expect(isLiteUiEnabled()).toBe(false);
  });

  it('persists enabled state', () => {
    setLiteUiEnabled(true);
    expect(localStorage.getItem(LITE_UI_KEY)).toBe('true');
    expect(isLiteUiEnabled()).toBe(true);
  });

  it('persists disabled state', () => {
    setLiteUiEnabled(true);
    setLiteUiEnabled(false);
    expect(localStorage.getItem(LITE_UI_KEY)).toBe('false');
    expect(isLiteUiEnabled()).toBe(false);
  });
});
