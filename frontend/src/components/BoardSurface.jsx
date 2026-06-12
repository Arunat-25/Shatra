import useMediaQuery from '../hooks/useMediaQuery';
import { COMPACT_GAME_QUERY } from '../constants';
import BoardGrid from '../BoardGrid';
import CanvasBoard from '../board/CanvasBoard';

export default function BoardSurface(props) {
  const compactGame = useMediaQuery(COMPACT_GAME_QUERY);
  if (compactGame) {
    return <CanvasBoard {...props} />;
  }
  return <BoardGrid {...props} />;
}
