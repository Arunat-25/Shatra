import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/react';
import Cell from './Cell';

describe('Cell pointer/click handling', () => {
  it('fires onCellClick when drag is disabled (lite UI path)', () => {
    const onCellClick = vi.fn();
    render(
      <Cell
        id={11}
        className="cell-dark"
        board={{ 11: 'черная шатра' }}
        onCellClick={onCellClick}
      />,
    );

    fireEvent.click(document.getElementById('position11'));
    expect(onCellClick).toHaveBeenCalledWith(11);
  });
});
