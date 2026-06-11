import { describe, expect, it } from 'vitest';
import { isSafeHttpUrl } from '../utils/safeUrl';

describe('Admin bug report page_url rendering policy', () => {
  it('allows clickable links only for safe http(s) URLs', () => {
    expect(isSafeHttpUrl('https://shatra.example/game')).toBe(true);
    expect(isSafeHttpUrl('javascript:alert(document.cookie)')).toBe(false);
  });
});
