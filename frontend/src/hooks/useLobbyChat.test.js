import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useLobbyChat from './useLobbyChat';

vi.mock('../api', () => ({
  getLobbyWsUrl: () => 'ws://localhost/ws/lobby/?client_id=test',
}));

vi.mock('../i18n/resolveMessage', () => ({
  resolveWsErrorMessage: (code) => `err:${code}`,
}));

describe('useLobbyChat', () => {
  let mockWs;

  beforeEach(() => {
    mockWs = {
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    };
    global.WebSocket = vi.fn(() => mockWs);
    global.WebSocket.OPEN = 1;
    global.WebSocket.CONNECTING = 0;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('loads chat_history into messages', async () => {
    const { result } = renderHook(() => useLobbyChat(true));

    act(() => {
      mockWs.onopen?.();
    });

    act(() => {
      mockWs.onmessage?.({
        data: JSON.stringify({
          type: 'chat_history',
          messages: [
            { client_id: 'a', text: 'hi', ts: 1, is_anonymous: true },
          ],
        }),
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].text).toBe('hi');
  });

  it('chat_history replaces prior messages instead of merging', () => {
    const { result } = renderHook(() => useLobbyChat(true));
    act(() => {
      mockWs.onopen?.();
      mockWs.onmessage?.({
        data: JSON.stringify({
          type: 'chat_history',
          messages: [{ client_id: 'a', text: 'old', ts: 1 }],
        }),
      });
      mockWs.onmessage?.({
        data: JSON.stringify({
          type: 'chat_history',
          messages: [{ client_id: 'b', text: 'fresh', ts: 2 }],
        }),
      });
    });
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].text).toBe('fresh');
  });

  it('appends incoming chat message', async () => {
    const { result } = renderHook(() => useLobbyChat(true));

    act(() => {
      mockWs.onopen?.();
      mockWs.onmessage?.({
        data: JSON.stringify({
          type: 'chat_history',
          messages: [],
        }),
      });
      mockWs.onmessage?.({
        data: JSON.stringify({
          type: 'chat',
          client_id: 'b',
          text: 'new',
          ts: 2,
          is_anonymous: true,
        }),
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].text).toBe('new');
  });

  it('normalizes from_client_id when only client_id is present', () => {
    const { result } = renderHook(() => useLobbyChat(true));
    act(() => {
      mockWs.onopen?.();
      mockWs.onmessage?.({
        data: JSON.stringify({
          type: 'chat',
          client_id: 'only-id',
          text: 'x',
          ts: 1,
        }),
      });
    });
    expect(result.current.messages[0].from_client_id).toBe('only-id');
    expect(result.current.messages[0].client_id).toBe('only-id');
  });

  it('maps server message_code to localized error string', () => {
    const { result } = renderHook(() => useLobbyChat(true));
    act(() => {
      mockWs.onopen?.();
      mockWs.onmessage?.({
        data: JSON.stringify({
          status: 'error',
          message_code: 'chat.too_fast',
        }),
      });
    });
    expect(result.current.error).toBe('err:chat.too_fast');
  });

  it('send returns false when socket is not open', () => {
    mockWs.readyState = 0;
    const { result } = renderHook(() => useLobbyChat(true));
    let ok;
    act(() => {
      ok = result.current.send('hello');
    });
    expect(ok).toBe(false);
    expect(mockWs.send).not.toHaveBeenCalled();
  });

  it('send posts chat payload when connected', () => {
    const { result } = renderHook(() => useLobbyChat(true));
    act(() => {
      mockWs.onopen?.();
    });
    act(() => {
      result.current.send('  hi  ');
    });
    expect(mockWs.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'chat', text: '  hi  ' }),
    );
  });

  it('does not open websocket when disabled', () => {
    renderHook(() => useLobbyChat(false));
    expect(global.WebSocket).not.toHaveBeenCalled();
  });

  it('closes websocket when toggled off', () => {
    const { rerender } = renderHook(({ enabled }) => useLobbyChat(enabled), {
      initialProps: { enabled: true },
    });
    act(() => {
      mockWs.onopen?.();
    });
    rerender({ enabled: false });
    expect(mockWs.close).toHaveBeenCalled();
  });
});
