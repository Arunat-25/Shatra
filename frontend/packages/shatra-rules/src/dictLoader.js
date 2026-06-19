import raw from './dictionaries.json';

function intKeys(obj) {
  if (obj == null || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map(intKeys);
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    const nk = /^\d+$/.test(k) ? Number(k) : k;
    out[nk] = intKeys(v);
  }
  return out;
}

const d = intKeys(raw);

export const blackShatraPossibleMoves = d.black_shatra_possible_moves;
export const whiteShatraPossibleMoves = d.white_shatra_possible_moves;
export const blackBiyPossibleMoves = d.black_biy_possible_moves;
export const whiteBiyPossibleMoves = d.white_biy_possible_moves;
export const shatraAndBiyPossibleCaptures = d.shatra_and_biy_possible_captures;
export const batyrMovesAndCaptures = d.batyr_moves_and_captures;
