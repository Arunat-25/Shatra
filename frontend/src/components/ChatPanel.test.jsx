import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import ChatPanel from './ChatPanel';

vi.mock('../api', () => ({
  getClientId: () => 'test-client',
}));

describe('ChatPanel', () => {
  afterEach(() => {
    cleanup();
  });

  it('respects maxLength on input', () => {
    render(
      <ChatPanel
        messages={[]}
        onSend={vi.fn()}
        maxLength={500}
        title="Lobby"
        placeholder="Type…"
      />,
    );
    const input = screen.getByRole('textbox');
    expect(input.getAttribute('maxLength')).toBe('500');
  });

  it('does not submit when disabled', () => {
    const onSend = vi.fn();
    render(
      <ChatPanel
        messages={[]}
        onSend={onSend}
        disabled
        placeholder="Type…"
      />,
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'blocked' } });
    fireEvent.submit(input.closest('form'));
    expect(onSend).not.toHaveBeenCalled();
  });

  it('calls onSend with trimmed text', () => {
    const onSend = vi.fn();
    render(
      <ChatPanel
        messages={[]}
        onSend={onSend}
        placeholder="Type…"
      />,
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '  hello  ' } });
    fireEvent.submit(input.closest('form'));
    expect(onSend).toHaveBeenCalledWith('hello');
  });
});
