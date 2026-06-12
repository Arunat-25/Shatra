import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import GameChat from './GameChat';

vi.mock('../api', () => ({
  getClientId: () => 'me123',
}));

describe('GameChat', () => {
  afterEach(() => {
    cleanup();
  });

  it('toggle hides messages but keeps send enabled', () => {
    const onSend = vi.fn();
    const onToggle = vi.fn();
    render(
      <GameChat
        messages={[{ client_id: 'x', text: 'hi', ts: 1 }]}
        onSend={onSend}
        disabled={false}
        chatHidden={false}
        onToggleHidden={onToggle}
        roomId="room1"
      />,
    );
    expect(screen.getByText('hi')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /скрыть|hide/i }));
    expect(onToggle).toHaveBeenCalled();
  });

  it('shows hidden hint when chatHidden', () => {
    render(
      <GameChat
        messages={[]}
        onSend={vi.fn()}
        disabled={false}
        chatHidden
        onToggleHidden={vi.fn()}
        roomId="room1"
      />,
    );
    expect(screen.getByText(/скрыты|hidden/i)).toBeTruthy();
    const input = screen.getByLabelText(/сообщ|message/i);
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByRole('button', { name: /отпр|send/i }));
    expect(screen.queryByText('test')).toBeNull();
  });
});
