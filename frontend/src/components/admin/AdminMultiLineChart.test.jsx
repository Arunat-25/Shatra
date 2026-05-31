import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import AdminMultiLineChart from './AdminMultiLineChart';

vi.mock('recharts', () => import('./rechartsMock.jsx'));

describe('AdminMultiLineChart', () => {
  afterEach(() => {
    cleanup();
  });

  const emptyBuckets = [
    {
      ts: '2026-05-29T00:00:00Z',
      total_unique: 0,
      registered_unique: 0,
      anonymous_unique: 0,
    },
  ];

  const sampleBuckets = [
    {
      ts: '2026-05-29T00:00:00Z',
      total_unique: 3,
      registered_unique: 2,
      anonymous_unique: 1,
    },
  ];

  it('shows empty label when all unique counts are zero', () => {
    render(
      <AdminMultiLineChart
        buckets={emptyBuckets}
        granularity="hour"
        emptyLabel="No online data"
      />,
    );
    expect(screen.getByText('No online data')).toBeTruthy();
  });

  it('renders three metric lines when data exists', () => {
    render(
      <AdminMultiLineChart
        buckets={sampleBuckets}
        granularity="hour"
        emptyLabel="No online data"
      />,
    );
    expect(screen.getByTestId('line-total_unique')).toBeTruthy();
    expect(screen.getByTestId('line-registered_unique')).toBeTruthy();
    expect(screen.getByTestId('line-anonymous_unique')).toBeTruthy();
  });
});
