import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import AdminLineChart from './AdminLineChart';

vi.mock('recharts', () => import('./rechartsMock.jsx'));

describe('AdminLineChart', () => {
  afterEach(() => {
    cleanup();
  });

  it('shows empty label when all counts are zero', () => {
    render(
      <AdminLineChart
        buckets={[
          { ts: '2026-05-29T00:00:00Z', count: 0 },
          { ts: '2026-05-30T00:00:00Z', count: 0 },
        ]}
        granularity="day"
        emptyLabel="No data"
      />,
    );
    expect(screen.getByText('No data')).toBeTruthy();
    expect(screen.queryByTestId('line-chart')).toBeNull();
  });

  it('renders chart when a bucket has data', () => {
    render(
      <AdminLineChart
        buckets={[
          { ts: '2026-05-29T00:00:00Z', count: 0 },
          { ts: '2026-05-30T00:00:00Z', count: 5 },
        ]}
        granularity="day"
        emptyLabel="No data"
      />,
    );
    expect(screen.queryByText('No data')).toBeNull();
    expect(screen.getByTestId('line-chart')).toBeTruthy();
    expect(screen.getByTestId('line-chart').getAttribute('data-points')).toBe('2');
  });
});
