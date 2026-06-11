import { describe, expect, it } from 'vitest';
import { isSafeHttpUrl } from './safeUrl';

describe('isSafeHttpUrl', () => {
  it('accepts http and https URLs', () => {
    expect(isSafeHttpUrl('http://localhost/game')).toBe(true);
    expect(isSafeHttpUrl('https://example.com/path')).toBe(true);
  });

  it('rejects javascript and data URLs', () => {
    expect(isSafeHttpUrl('javascript:alert(1)')).toBe(false);
    expect(isSafeHttpUrl('data:text/html,<script>alert(1)</script>')).toBe(false);
  });

  it('rejects empty and malformed values', () => {
    expect(isSafeHttpUrl('')).toBe(false);
    expect(isSafeHttpUrl('   ')).toBe(false);
    expect(isSafeHttpUrl('not-a-url')).toBe(false);
    expect(isSafeHttpUrl(null)).toBe(false);
  });
});
