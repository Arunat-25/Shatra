import { useEffect } from 'react';
import useMediaQuery from '../hooks/useMediaQuery';
import { useLiteUi } from '../context/LiteUiContext';
import { COMPACT_GAME_QUERY } from '../constants';
import BoardGrid from '../BoardGrid';
import CanvasBoard from '../board/CanvasBoard';
import { preloadPieceSprites } from '../board/pieceSprites';

export default function BoardSurface(props) {
  const compactViewport = useMediaQuery(COMPACT_GAME_QUERY);
  const { enabled: liteUi } = useLiteUi();

  useEffect(() => {
    if (!liteUi) return;
    preloadPieceSprites({ vectorOnly: true });
  }, [liteUi]);

  if (liteUi) {
    return <CanvasBoard {...props} drawTheme="lite" vectorOnlySprites />;
  }

  const useLitePieces = compactViewport;

  if (useLitePieces) {
    return (
      <BoardGrid
        {...props}
        pieceVariant="lite"
        enablePieceDrag={false}
      />
    );
  }

  return <BoardGrid {...props} />;
}
