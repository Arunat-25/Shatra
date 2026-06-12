import ShatraPiece from '../ShatraPiece';
import { PIECE_BATYR, PIECE_SHATRA } from '../constants';
import { colorToCountsKey, getBoardSideOrder } from '../utils';

function CountCell({ type, color, count }) {
  return (
    <div className="room-counts-cell">
      <span className="room-counts-piece" aria-hidden="true">
        <ShatraPiece type={type} color={color} isSelected={false} isTarget={false} />
      </span>
      <span className="room-counts-num">{count}</span>
    </div>
  );
}

export function PieceCountRow({ color, countsByType }) {
  const key = colorToCountsKey(color);
  const counts = countsByType?.[key] ?? { batyr: 0, shatra: 0 };
  return (
    <div className="room-counts-row room-counts-row--inline">
      <CountCell type={PIECE_BATYR} color={color} count={counts.batyr} />
      <CountCell type={PIECE_SHATRA} color={color} count={counts.shatra} />
    </div>
  );
}

export default function PieceCounts({ countsByType, myColor }) {
  const { top, bottom } = getBoardSideOrder(myColor);

  return (
    <div className="room-counts-block room-counts-block--desktop">
      <PieceCountRow color={top} countsByType={countsByType} />
      <PieceCountRow color={bottom} countsByType={countsByType} />
    </div>
  );
}
