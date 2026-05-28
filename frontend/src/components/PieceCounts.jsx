import ShatraPiece from '../ShatraPiece';
import { COLOR_WHITE, COLOR_BLACK, PIECE_BATYR, PIECE_SHATRA } from '../constants';

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

export default function PieceCounts({ countsByType }) {
  const white = countsByType?.white ?? { batyr: 0, shatra: 0 };
  const black = countsByType?.black ?? { batyr: 0, shatra: 0 };

  return (
    <div className="room-counts-block">
      <div className="room-counts-row">
        <CountCell type={PIECE_BATYR} color={COLOR_WHITE} count={white.batyr} />
        <CountCell type={PIECE_SHATRA} color={COLOR_WHITE} count={white.shatra} />
      </div>
      <div className="room-counts-row">
        <CountCell type={PIECE_BATYR} color={COLOR_BLACK} count={black.batyr} />
        <CountCell type={PIECE_SHATRA} color={COLOR_BLACK} count={black.shatra} />
      </div>
    </div>
  );
}
