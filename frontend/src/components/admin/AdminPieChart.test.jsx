import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import AdminPieChart from './AdminPieChart';

vi.mock('recharts', () => import('./rechartsMock.jsx'));

describe('AdminPieChart', () => {
  afterEach(() => {
    cleanup();
  });

  it('shows empty label when all values are zero', () => {
    render(
      <AdminPieChart
        data={[
          { name: 'Public', value: 0 },
          { name: 'AI', value: 0 },
        ]}
        emptyLabel="No games"
      />,
    );
    expect(screen.getByText('No games')).toBeTruthy();
  });

  it('renders pie for positive slices only', () => {
    render(
      <AdminPieChart
        data={[
          { name: 'Public', value: 5 },
          { name: 'AI', value: 0 },
        ]}
        emptyLabel="No games"
      />,
    );
    const pie = screen.getByTestId('pie');
    expect(pie.getAttribute('data-slices')).toBe('1');
  });
});
