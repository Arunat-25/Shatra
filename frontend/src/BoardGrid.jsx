import ShatraPiece from './ShatraPiece';

function getPieceType(pieceStr) {
  if (pieceStr.includes('бий')) return 'бий';
  if (pieceStr.includes('батыр')) return 'батыр';
  return 'шатра';
}

function getPieceColor(pieceStr) {
  return pieceStr.includes('бел') ? 'белый' : 'черный';
}

export default function BoardGrid({ board, onCellClick, moveFrom, highlightedEssential = [], highlightedCaptured = [], lastMove = null }) {
  const renderCell = (id, className) => {
    const isEssential = highlightedEssential.includes(id);
    const isCaptured = highlightedCaptured.includes(id);
    const isLastFrom = lastMove && lastMove.from === id;
    const isLastTo = lastMove && lastMove.to === id;
    const classes = [
      'kletka',
      className,
      board[id] ? 'has-piece' : '',
      moveFrom === id ? 'highlight-black' : '',
      isEssential ? 'highlight-essential' : '',
      isCaptured ? 'highlight-captured' : '',
      isLastFrom ? 'last-move-from' : '',
      isLastTo ? 'last-move-to' : '',
    ].filter(Boolean).join(' ');
    
    return (
      <div
        key={id}
        id={`position${id}`}
        className={classes}
        onClick={() => onCellClick(id)}
      >
        {board[id] && (
          <div className="image-in-kletka">
            <ShatraPiece 
              type={getPieceType(board[id])} 
              color={getPieceColor(board[id])}
              isSelected={moveFrom === id}
              isTarget={isCaptured}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="field-of-reserve">
        <div className="row">
          {renderCell(1, 'cell-dark')}{renderCell(2, 'cell-light')}{renderCell(3, 'cell-dark')}
        </div>
        <div className="row">
          {renderCell(4, 'cell-light')}{renderCell(5, 'cell-dark')}{renderCell(6, 'cell-light')}
        </div>
        <div className="row">
          {renderCell(7, 'cell-dark')}{renderCell(8, 'cell-light')}{renderCell(9, 'cell-dark')}
        </div>
      </div>
      <div className="field-of-king">{renderCell(10, 'cell-light')}</div>
      <div className="main-field">
        <div className="row">
          {renderCell(11, 'cell-dark')}{renderCell(12, 'cell-light')}{renderCell(13, 'cell-dark')}
          {renderCell(14, 'cell-light')}{renderCell(15, 'cell-dark')}{renderCell(16, 'cell-light')}{renderCell(17, 'cell-dark')}
        </div>
        <div className="row">
          {renderCell(18, 'cell-light')}{renderCell(19, 'cell-dark')}{renderCell(20, 'cell-light')}
          {renderCell(21, 'cell-dark')}{renderCell(22, 'cell-light')}{renderCell(23, 'cell-dark')}{renderCell(24, 'cell-light')}
        </div>
        <div className="row">
          {renderCell(25, 'cell-dark')}{renderCell(26, 'cell-light')}{renderCell(27, 'cell-dark')}
          {renderCell(28, 'cell-light')}{renderCell(29, 'cell-dark')}{renderCell(30, 'cell-light')}{renderCell(31, 'cell-dark')}
        </div>
      </div>
      <div className="main-field">
        <div className="row">
          {renderCell(32, 'cell-light')}{renderCell(33, 'cell-dark')}{renderCell(34, 'cell-light')}
          {renderCell(35, 'cell-dark')}{renderCell(36, 'cell-light')}{renderCell(37, 'cell-dark')}{renderCell(38, 'cell-light')}
        </div>
        <div className="row">
          {renderCell(39, 'cell-dark')}{renderCell(40, 'cell-light')}{renderCell(41, 'cell-dark')}
          {renderCell(42, 'cell-light')}{renderCell(43, 'cell-dark')}{renderCell(44, 'cell-light')}{renderCell(45, 'cell-dark')}
        </div>
        <div className="row">
          {renderCell(46, 'cell-light')}{renderCell(47, 'cell-dark')}{renderCell(48, 'cell-light')}
          {renderCell(49, 'cell-dark')}{renderCell(50, 'cell-light')}{renderCell(51, 'cell-dark')}{renderCell(52, 'cell-light')}
        </div>
      </div>
      <div className="field-of-king">{renderCell(53, 'cell-light')}</div>
      <div className="field-of-reserve">
        <div className="row">
          {renderCell(54, 'cell-dark')}{renderCell(55, 'cell-light')}{renderCell(56, 'cell-dark')}
        </div>
        <div className="row">
          {renderCell(57, 'cell-light')}{renderCell(58, 'cell-dark')}{renderCell(59, 'cell-light')}
        </div>
        <div className="row">
          {renderCell(60, 'cell-dark')}{renderCell(61, 'cell-light')}{renderCell(62, 'cell-dark')}
        </div>
      </div>
    </>
  );
}