import useMediaQuery from '../hooks/useMediaQuery';
import { COMPACT_GAME_QUERY } from '../constants';
import BoardGrid from '../BoardGrid';

export default function BoardSurface(props) {
  const compactGame = useMediaQuery(COMPACT_GAME_QUERY);
  if (compactGame) {
    // DOM + lite pieces: canvas repaint broke on touch (board vanished, hit-test still worked).
    return <BoardGrid {...props} pieceVariant="lite" enablePieceDrag={false} />;
  }
  return <BoardGrid {...props} />;
}
