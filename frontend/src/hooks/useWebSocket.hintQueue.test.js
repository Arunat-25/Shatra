import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useWebSocket from './useWebSocket';
import { buildHintPayload } from '../utils/wsPayloads';

vi.mock('../api', () => ({
  getWsUrl: (roomId) => `ws://test/${roomId}`,
}));

vi.mock('../observability/events', () => ({
  trackWsEvent: vi.fn(),
}));

vi.mock('../wsReconnect', () => ({
  classifyClose: () => ({ recoverable: false, type: 'fatal' }),
  getReconnectDelay: () => 1000,
  parseWsMessage: (raw) => ({ ok: true, data: JSON.parse(raw) }),
  shouldStopReconnecting: () => true,
}));

let mockSocket;

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.sent = [];
    mockSocket = this;
  }

  send(data) {
    this.sent.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }
}

describe('useWebSocket hint queue', () => {
  beforeEach(() => {
    mockSocket = null;
    global.WebSocket = MockWebSocket;
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('queues normal moves while CONNECTING but drops hints', () => {
    const { result } = renderHook(() => useWebSocket('room1', vi.fn(), vi.fn(), vi.fn()));

    const movePayload = {
      move_from: 'position10',
      move_to: 'position14',
      board: {},
      movers_color: 'белый',
    };

    act(() => {
      expect(result.current.send(buildHintPayload(53))).toBe(false);
      expect(result.current.send(movePayload)).toBe(true);
    });

    expect(mockSocket.sent).toHaveLength(0);

    act(() => {
      mockSocket.readyState = MockWebSocket.OPEN;
      mockSocket.onopen?.();
    });

    expect(mockSocket.sent).toHaveLength(1);
    expect(JSON.parse(mockSocket.sent[0])).toEqual(movePayload);
  });

  it('sends hints immediately when socket is OPEN', () => {
    const { result } = renderHook(() => useWebSocket('room2', vi.fn(), vi.fn(), vi.fn()));

    act(() => {
      mockSocket.readyState = MockWebSocket.OPEN;
      mockSocket.onopen?.();
    });

    act(() => {
      expect(result.current.send(buildHintPayload(19))).toBe(true);
    });

    expect(mockSocket.sent).toHaveLength(1);
    expect(JSON.parse(mockSocket.sent[0])).toEqual({ position: 'position19' });
  });

  it('returns false when socket is closed', () => {
    const { result } = renderHook(() => useWebSocket('room3', vi.fn(), vi.fn(), vi.fn()));

    act(() => {
      mockSocket.readyState = MockWebSocket.CLOSED;
    });

    act(() => {
      expect(result.current.send(buildHintPayload(10))).toBe(false);
    });
  });
});
