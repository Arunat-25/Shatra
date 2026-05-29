import { describe, expect, it } from 'vitest';
import { gameReducer, initialGameState } from './reducer';
import { GAME_ACTIONS } from './actions';

describe('gameReducer chat and players', () => {
  it('CHAT_HISTORY replaces messages', () => {
    const history = [{ text: 'a', ts: 1 }, { text: 'b', ts: 2 }];
    const next = gameReducer(
      { ...initialGameState, chatMessages: [{ text: 'old' }] },
      { type: GAME_ACTIONS.CHAT_HISTORY, payload: history },
    );
    expect(next.chatMessages).toEqual(history);
  });

  it('CHAT_MESSAGE appends and caps at 50', () => {
    const base = {
      ...initialGameState,
      chatMessages: Array.from({ length: 50 }, (_, i) => ({ text: String(i) })),
    };
    const msg = { text: 'new', ts: 99 };
    const next = gameReducer(base, { type: GAME_ACTIONS.CHAT_MESSAGE, payload: msg });
    expect(next.chatMessages).toHaveLength(50);
    expect(next.chatMessages[49]).toEqual(msg);
    expect(next.chatMessages[0].text).toBe('1');
  });

  it('SET_PLAYERS_INFO updates list', () => {
    const info = [{ client_id: 'x', display_name: 'Аноним' }];
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.SET_PLAYERS_INFO,
      payload: info,
    });
    expect(next.playersInfo).toEqual(info);
  });

  it('GAME_STARTED merges players_info from payload', () => {
    const info = [{ client_id: 'a', display_name: 'u' }];
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_STARTED,
      payload: {
        your_color: 'белый',
        movers_color: 'белый',
        desk: { '10': 'белый бий' },
        players_info: info,
      },
    });
    expect(next.playersInfo).toEqual(info);
    expect(next.waiting).toBe(false);
  });
});
