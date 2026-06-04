import { getEmptyBoard } from '../../game/startingBoard';

function placeTutorialBlackPieces(board, config) {
  for (const id of config.blackCells ?? []) {
    if (!board[id]) board[id] = 'черная шатра';
  }
  for (const [pos, piece] of Object.entries(config.blackPieces ?? {})) {
    board[Number(pos)] = piece;
  }
}

/** @returns {Record<number, object[]> | null} */
export function getChainMap(config) {
  if (config.chains) return config.chains;
  if (config.chain) {
    const root = config.chain[0].piecePos;
    return { [root]: config.chain };
  }
  return null;
}

export function getChainForStart(chainMap, chainStart) {
  if (chainStart == null || !chainMap) return null;
  return chainMap[chainStart] ?? null;
}

function buildInitialTutorialBoard(config) {
  const board = getEmptyBoard();
  placeTutorialBlackPieces(board, config);
  const chainMap = getChainMap(config);
  if (chainMap) {
    for (const chain of Object.values(chainMap)) {
      const root = chain[0];
      board[root.piecePos] = root.piece;
    }
  }
  for (const id of config.whiteShatraCells ?? []) {
    if (!board[id]) board[id] = 'белая шатра';
  }
  return board;
}

export function getStepPieces(config, chainStart = null, chainHistory = []) {
  if (config.pieces) {
    return Object.fromEntries(
      Object.entries(config.pieces).map(([pos, data]) => [Number(pos), data]),
    );
  }
  const chainMap = getChainMap(config);
  if (chainMap) {
    const chain = getChainForStart(chainMap, chainStart);
    if (chain) {
      const active = getNextChainHop(chain, chainHistory);
      if (active) {
        return {
          [active.piecePos]: { piece: active.piece, captures: active.captures },
        };
      }
    }
    return Object.fromEntries(
      Object.values(chainMap).map((chain) => {
        const root = chain[0];
        return [root.piecePos, { piece: root.piece, captures: root.captures }];
      }),
    );
  }
  return {
    [config.piecePos]: {
      piece: config.piece,
      captures: config.captureLandings,
      allowedTargets: config.allowedTargets,
    },
  };
}

export function getChainHop(chain, hopIndex, chainHistory = []) {
  if (!chain?.length) return null;
  if (hopIndex === 0) return chain[0];
  if (hopIndex === 1) {
    if (chain[0]?.branches) {
      const branch = chain[0].branches[chainHistory[0]];
      if (!branch || branch.complete) return null;
      return branch;
    }
    return chain[1] ?? null;
  }

  let hop = getChainHop(chain, 1, chainHistory);
  for (let i = 2; i <= hopIndex; i += 1) {
    const landing = chainHistory[i - 1];
    if (hop?.branches?.[landing]) {
      hop = hop.branches[landing];
      if (hop?.complete) return null;
      continue;
    }
    if (!chain[0]?.branches && chain[i]) {
      hop = chain[i];
      continue;
    }
    return null;
  }
  return hop;
}

export function getNextChainHop(chain, chainHistory) {
  const hop = getChainHop(chain, chainHistory.length, chainHistory);
  if (!hop || hop.complete) return null;
  return hop;
}

export function buildCaptureBoard(steps, step, chainHistory = [], chainStart = null) {
  const config = steps[step];
  const b = getEmptyBoard();
  const chainMap = getChainMap(config);

  if (chainMap) {
    placeTutorialBlackPieces(b, config);
    for (const [startPos, chain] of Object.entries(chainMap)) {
      const start = Number(startPos);
      if (chainStart == null || start !== chainStart) {
        const root = chain[0];
        b[root.piecePos] = root.piece;
      }
    }
    const chain = getChainForStart(chainMap, chainStart);
    if (chain) {
      for (let i = 0; i < chainHistory.length; i += 1) {
        const hop = getChainHop(chain, i, chainHistory);
        const landing = chainHistory[i];
        const captured = hop.captures[landing];
        b[hop.piecePos] = null;
        b[landing] = hop.piece;
        if (captured != null) b[captured] = null;
      }
      const active = getNextChainHop(chain, chainHistory);
      if (active) b[active.piecePos] = active.piece;
    }
    for (const id of config.whiteShatraCells ?? []) {
      if (!b[id]) b[id] = 'белая шатра';
    }
    return b;
  }

  if (config.fillBlackFortress) {
    for (let c = 1; c <= 9; c += 1) {
      b[c] = 'черная шатра';
    }
    b[10] = 'черный бий';
  }
  const pieces = getStepPieces(config);
  for (const [pos, { piece }] of Object.entries(pieces)) {
    b[Number(pos)] = piece;
  }
  placeTutorialBlackPieces(b, config);
  for (const [pos, piece] of Object.entries(config.boardPieces ?? {})) {
    b[Number(pos)] = piece;
  }
  for (const id of config.whiteShatraCells ?? []) {
    if (!b[id]) b[id] = 'белая шатра';
  }
  return b;
}

export function getAllowedTargets(pieceConfig) {
  return pieceConfig.allowedTargets ?? Object.keys(pieceConfig.captures).map(Number);
}

/** Прозрачные «призраки» взятых фигур, пока серия взятий не закончена. */
export function buildChainCapturedGhosts(config, chainHistory, chainComplete, chainStart = null) {
  const chainMap = getChainMap(config);
  if (!chainMap || chainStart == null || chainComplete || chainHistory.length === 0) return {};

  const ghosts = {};
  const chain = getChainForStart(chainMap, chainStart);
  if (!chain) return {};
  const initialBoard = buildInitialTutorialBoard(config);
  for (let i = 0; i < chainHistory.length; i += 1) {
    const hop = getChainHop(chain, i, chainHistory);
    const captured = hop.captures[chainHistory[i]];
    if (captured != null) {
      ghosts[captured] = initialBoard[captured] ?? 'черная шатра';
    }
  }
  return ghosts;
}
