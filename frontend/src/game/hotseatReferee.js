import {
  MOVE_REJECT_MESSAGE_CODES,
  normalizeCells,
  onlyTwoBiysLeft,
  processMove,
} from '@shatra/rules';
import i18n from '../i18n';
import { COLOR_BLACK, COLOR_WHITE } from '../constants';
import { getStartingBoard } from './startingBoard.js';
import { opponentColor } from './passTurn.js';

/**
 * Локальный «рефери» хотсита: партии двух игроков на одном устройстве.
 *
 * Реализует ровно те же инварианты, что серверная партия: персистентная
 * история позиций (повторы), счётчик ходов с двумя биями, отложенные взятия
 * бием и продолжение серий. Отдаёт сообщения в том же v1-формате, который
 * потребляет reducer, поэтому UI не отличает хотсит от онлайн-партии.
 */

function hotseatPlayersInfo() {
  return [
    {
      client_id: 'hotseat-white',
      color: COLOR_WHITE,
      username: i18n.t('colors.white'),
      is_anonymous: true,
      display_name: i18n.t('colors.white'),
    },
    {
      client_id: 'hotseat-black',
      color: COLOR_BLACK,
      username: i18n.t('colors.black'),
      is_anonymous: true,
      display_name: i18n.t('colors.black'),
    },
  ];
}

export function createHotseatReferee(initial = {}) {
  let cells = initial.cells ? { ...initial.cells } : getStartingBoard();
  let mover = initial.mover ?? COLOR_WHITE;
  let ply = initial.ply ?? 0;
  let chainCell = initial.chainCell ?? null;
  let batyrCaptured = [...(initial.batyrCaptured ?? [])];
  let positionHistory = { ...(initial.positionHistory ?? {}) };
  let movesWithTwoBiys = initial.movesWithTwoBiys ?? 0;
  let finished = false;

  // Зеркало applyServerPersist из engine/clientServerSync.test.js + счётчик
  // «ходов с двумя биями» из backend/session/messages.py.
  function persistAfterMove(result, prevMover) {
    if (result.updatedPositions) cells = result.updatedPositions;
    const pending = result.positionForMandatoryCapture ?? null;
    chainCell =
      pending != null && result.moversColor === prevMover ? pending : null;
    if (result.moversColor && result.moversColor !== prevMover) {
      batyrCaptured = [];
    } else if (result.capturedPieces?.length) {
      batyrCaptured = [...result.capturedPieces];
    } else if (!result.positionForMandatoryCapture) {
      batyrCaptured = [];
    }
    if (result.moversColor) mover = result.moversColor;
    ply += 1;
    movesWithTwoBiys = onlyTwoBiysLeft({ cells })
      ? movesWithTwoBiys + 1
      : 0;
  }

  function rejectMove(result) {
    return [{ status: 'error', message_code: result.messageCode || 'move.impossible' }];
  }

  function buildMoveMessage(result, prevMover, from, to) {
    return {
      from_pos: from,
      to_pos: to,
      mover: prevMover,
      movers_color: mover,
      desk: { ...cells },
      captured_positions: result.capturedPositions || [],
      captured_pieces: [...batyrCaptured],
      position_for_mandatory_capture: chainCell,
      opportunity_pass_the_move: Boolean(result.opportunityPassTheMove),
      ply,
      message_code: result.messageCode,
    };
  }

  function pushGameOverIfAny(result, messages) {
    if (!result.gameOver) return;
    finished = true;
    messages.push({
      game_over: true,
      winner_color: result.winnerColor ?? '',
      reason: result.drawReason ?? '',
      ply,
    });
  }

  function startMessage({ resync = false } = {}) {
    return {
      status: 'game_started',
      your_color: mover,
      movers_color: mover,
      desk: { ...cells },
      move_history: [],
      players_info: hotseatPlayersInfo(),
      ply,
      time_control: null,
      increment: null,
      ...(resync ? { _resync: true } : {}),
    };
  }

  function applyMove(payload) {
    if (finished) {
      return [{ status: 'error', message_code: 'game.over' }];
    }
    const from = Number(payload.from);
    const to = Number(payload.to);
    const prevMover = mover;
    const result = processMove({
      cells: normalizeCells(cells),
      currentColor: mover,
      fromCell: from,
      toCell: to,
      chainCaptureCell: chainCell,
      batyrCapturedThisTurn: batyrCaptured,
      positionHistory,
      movesWithTwoBiys,
    });
    if (MOVE_REJECT_MESSAGE_CODES.has(result.messageCode) || !result.updatedPositions) {
      return rejectMove(result);
    }
    persistAfterMove(result, prevMover);
    const messages = [buildMoveMessage(result, prevMover, from, to)];
    pushGameOverIfAny(result, messages);
    return messages;
  }

  // Зеркало backend/session/v2/messages.py: пас — ход с from/to = 0/0
  // и position_for_mandatory_capture = 0.
  function passMove() {
    if (finished) {
      return [{ status: 'error', message_code: 'game.over' }];
    }
    const prevMover = mover;
    const result = processMove({
      cells: normalizeCells(cells),
      currentColor: mover,
      fromCell: 0,
      toCell: 0,
      chainCaptureCell: 0,
      batyrCapturedThisTurn: batyrCaptured,
      positionHistory,
      movesWithTwoBiys,
    });
    if (MOVE_REJECT_MESSAGE_CODES.has(result.messageCode) || !result.updatedPositions) {
      return rejectMove(result);
    }
    persistAfterMove(result, prevMover);
    const messages = [buildMoveMessage(result, prevMover, 0, 0)];
    pushGameOverIfAny(result, messages);
    return messages;
  }

  function resign() {
    if (finished) return [];
    finished = true;
    return [
      {
        game_over: true,
        winner_color: opponentColor(mover) ?? '',
        reason: 'resign',
        ply,
      },
    ];
  }

  function rematch() {
    cells = getStartingBoard();
    mover = COLOR_WHITE;
    ply = 0;
    chainCell = null;
    batyrCaptured = [];
    positionHistory = {};
    movesWithTwoBiys = 0;
    finished = false;
    return [startMessage()];
  }

  function handleSend(payload) {
    if (!payload || typeof payload !== 'object') return [];
    switch (payload.t) {
      case 'move':
        return applyMove(payload);
      case 'pass':
        return passMove();
      case 'resign':
        return resign();
      case 'request_rematch':
        return rematch();
      // Чат, ничьи и отмена партии в хотсите не поддерживаются.
      default:
        return [];
    }
  }

  return {
    start: startMessage,
    handleSend,
    isFinished: () => finished,
  };
}
