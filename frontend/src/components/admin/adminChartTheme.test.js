import { describe, expect, it } from 'vitest';
import { formatBucketLabel, getAdminChartColors } from './adminChartTheme';

describe('adminChartTheme', () => {
  it('formatBucketLabel formats hour granularity', () => {
    const label = formatBucketLabel('2026-05-29T14:00:00.000Z', 'hour');
    expect(label).toBeTruthy();
    expect(typeof label).toBe('string');
  });

  it('formatBucketLabel formats day granularity', () => {
    const label = formatBucketLabel('2026-05-29T00:00:00.000Z', 'day');
    expect(label).toBeTruthy();
    expect(label).not.toMatch(/:\d{2}/);
  });

  it('getAdminChartColors returns defaults without document', () => {
    const colors = getAdminChartColors();
    expect(colors.accent).toBeTruthy();
    expect(colors.muted).toBeTruthy();
    expect(colors.grid).toBeTruthy();
  });
});
