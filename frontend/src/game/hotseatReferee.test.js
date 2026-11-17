import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { COLOR_BLACK, COLOR_WHITE } from '../constants';
import { getStartingBoard } from './startingBoard.js';
import { createHotseatReferee } from './hotseatReferee';

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = join(here, '../../../tests/fixtures/sync/client_server_sync.json');
const { scenarios } = JSON.parse(readFileSync(fixturePath, 'utf8'));

const boardFromFixture = (cells) => {
  const board = getStartingBoard();
  for (const key of Object.keys(board)) {
    board[Number(key)] = Object.prototype.hasOwnProperty.call(cells, key)
      ? cells[key]
      : null;
  }
  return board;
};

const moveMessages = (messages) => messages.filter((m) => m.from_pos !== undefined);

describe('hotseatReferee', () => {
  it('start message matches the server game_started contract', () => {
    const referee = createHotseatReferee();
    const msg = referee.start();

    expect(msg.status).toBe('game_started');
    expect(msg.your_color).toBe(COLOR_WHITE);
    expect(msg.movers_color).toBe(COLOR_WHITE);
    expect(msg.ply).toBe(0);
    expect(msg.time_control).toBeNull();
    expect(msg.move_history).toEqual([]);
    expect(msg.players_info).toHaveLength(2);
    expect(msg.players_info.map((p) => p.color)).toEqual([COLOR_WHITE, COLOR_BLACK]);
    expect(Object.keys(msg.desk).length).toBe(62);
    expect(msg.desk).toEqual(getStartingBoard());
  });

  for (const scenario of scenarios) {
    it(`replays parity fixture: ${scenario.id}`, () => {
      const initial = {};
      if (scenario.board) {
        initial.cells = boardFromFixture(scenario.board);
        initial.mover = scenario.mover ?? COLOR_WHITE;
      }
      const referee = createHotseatReferee(initial);
      let last = referee.start();

      for (const [, from, to] of scenario.moves) {
        const messages = referee.handleSend({ t: 'move', from, to, ply: last.ply ?? 0 });
        const errors = messages.filter((m) => m.status === 'error');
        expect(errors, `move ${from}->${to} rejected`).toEqual([]);
        last = moveMessages(messages).at(-1);
        expect(last).toBeDefined();
      }

      expect(last.movers_color).toBe(scenario.expect_mover);
      expect(last.position_for_mandatory_capture ?? null).toBe(
        scenario.expect_server_pending ?? null,
      );
    });
  }

  it('rejects an illegal move with a server-shaped error', () => {
    const referee = createHotseatReferee();
    referee.start();
    // Ход черной шатрой в первый ход — цвет не совпадает.
    const messages = referee.handleSend({ t: 'move', from: 20, to: 26, ply: 1 });
    expect(messages[0].status).toBe('error');
    expect(typeof messages[0].message_code).toBe('string');
  });

  it('resign ends the game with the opponent as winner', () => {
    const referee = createHotseatReferee();
    referee.start();
    const messages = referee.handleSend({ t: 'resign' });
    expect(messages).toHaveLength(1);
    expect(messages[0].game_over).toBe(true);
    expect(messages[0].reason).toBe('resign');
    expect(messages[0].winner_color).toBe(COLOR_BLACK);
    // Партия закончена — ходы больше не принимаются.
    const late = referee.handleSend({ t: 'move', from: 40, to: 32, ply: 1 });
    expect(late[0].status).toBe('error');
  });

  it('rematch resets the referee to a fresh game', () => {
    const referee = createHotseatReferee();
    referee.start();
    referee.handleSend({ t: 'resign' });

    const messages = referee.handleSend({ t: 'request_rematch' });
    expect(messages).toHaveLength(1);
    expect(messages[0].status).toBe('game_started');
    expect(messages[0].your_color).toBe(COLOR_WHITE);
    expect(messages[0].movers_color).toBe(COLOR_WHITE);
    expect(messages[0].ply).toBe(0);
    expect(messages[0].desk).toEqual(getStartingBoard());

    // После реванша легальный ход снова принимается.
    const next = referee.handleSend({ t: 'move', from: 40, to: 32, ply: 1 });
    expect(next.filter((m) => m.status === 'error')).toEqual([]);
  });

  it('ignores chat and draw payloads like the AI room does', () => {
    const referee = createHotseatReferee();
    referee.start();
    expect(referee.handleSend({ t: 'chat', text: 'hi' })).toEqual([]);
    expect(referee.handleSend({ t: 'offer_draw' })).toEqual([]);
    expect(referee.handleSend({ t: 'cancel_game' })).toEqual([]);
  });
});
