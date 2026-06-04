"""Интеграционные тесты правил игры: взятие в крепость, обязательные взятия."""

from game_engine.board import Board
from game_engine.validation import get_all_mandatory_captures, validate_move


# ============================================================
# 1. Шатра — взятие в крепость
# ============================================================
# Белая шатра на 42, враг на 49, цель 53 (ворота белых)
# captures[42] = {..., 53: 49, ...}

def _make_board():
    return {i: None for i in range(1, 63)}


def test_shatra_capture_into_fortress_blocked_by_own_shatra():
    """1a. Белая шатра не может взять в свои ворота при своей шатре в крепости."""
    board = _make_board()
    board[42] = "белая шатра"
    board[49] = "черная шатра"  # враг
    board[54] = "белая шатра"   # своя шатра в крепости — блокирует

    from game_engine.pieces.shatra import Shatra
    s = Shatra("белый")
    can = s.can_capture(board, 42, 53, [])
    assert not can, "Шатра НЕ может взять в свои ворота при своей шатре в крепости"

    b = Board(board)
    mandatory = get_all_mandatory_captures(b, "белый", [])
    for f, t in mandatory:
        assert not (f == 42 and t == 53), "get_all_mandatory_captures не должно содержать 42->53"


def test_shatra_capture_into_fortress_forbidden_even_with_biy():
    """1b. Белая шатра не может взять в свои ворота, даже если в крепости только бий."""
    board = _make_board()
    board[42] = "белая шатра"
    board[49] = "черная шатра"  # враг
    board[54] = "белый бий"     # свой бий в крепости — не помогает

    from game_engine.pieces.shatra import Shatra
    s = Shatra("белый")
    can = s.can_capture(board, 42, 53, [])
    assert not can, "Шатра НЕ может взять в свои ворота, даже если в крепости только бий"

    b = Board(board)
    mandatory = get_all_mandatory_captures(b, "белый", [])
    assert (42, 53) not in mandatory, "get_all_mandatory_captures не должно содержать 42->53"
    v, _ = validate_move(board, 42, 53, "белый", [])
    assert not v, "validate_move(42->53) должно быть False"


# ============================================================
# 2. Батыр — взятие в крепость
# ============================================================
# Белый батыр на 35, direction [42, 49, 53, 55, 58, 61]
# Враг на 49, приземление на 53 (ворота белых)

def test_batyr_capture_into_fortress_blocked_by_own_shatra():
    """2a. Белый батыр не может взять в свои ворота при своей шатре в крепости."""
    board = _make_board()
    board[35] = "белый батыр"
    board[49] = "черная шатра"  # враг на пути
    board[54] = "белая шатра"   # своя шатра в крепости — блокирует

    from game_engine.pieces.batyr import Batyr
    b = Batyr("белый")
    can = b.can_capture(board, 35, 53, [])
    assert not can, "Батыр НЕ может взять в свои ворота при своей шатре в крепости"

    board_obj = Board(board)
    mandatory = get_all_mandatory_captures(board_obj, "белый", [])
    for f, t in mandatory:
        assert not (f == 35 and t == 53), "get_all_mandatory_captures не должно содержать 35->53"


def test_batyr_capture_into_fortress_allowed_with_biy():
    """2b. Белый батыр может взять в свои ворота если в крепости только бий (не шатра)."""
    board = _make_board()
    board[35] = "белый батыр"
    board[49] = "черная шатра"  # враг на пути
    board[54] = "белый бий"     # свой бий в крепости — не блокирует

    from game_engine.pieces.batyr import Batyr
    b = Batyr("белый")
    can = b.can_capture(board, 35, 53, [])
    assert can, "Батыр может взять в свои ворота, если в крепости только бий"

    board_obj = Board(board)
    mandatory = get_all_mandatory_captures(board_obj, "белый", [])
    assert (35, 53) in mandatory, "get_all_mandatory_captures должно содержать 35->53"
    v, _ = validate_move(board, 35, 53, "белый", [])
    assert v, "validate_move(35->53) должно быть True"


# ============================================================
# 3. Бий — взятие в крепость
# ============================================================
# Белый бий на 48, captures[48] = {..., 56: 53, ...}
# 48->56 берёт 53 (ворота белых)

def test_biy_capture_into_fortress_blocked_by_own_shatra():
    """3a. Белый бий не может взять в свои ворота при своей шатре в крепости."""
    board = _make_board()
    board[48] = "белый бий"
    board[53] = "черная шатра"  # враг на 53
    board[54] = "белая шатра"   # своя шатра в крепости — блокирует

    from game_engine.pieces.biy import Biy
    b = Biy("белый")
    can = b.can_capture(board, 48, 56, [])
    assert not can, "Бий НЕ может взять в свои ворота при своей шатре в крепости"

    board_obj = Board(board)
    mandatory = get_all_mandatory_captures(board_obj, "белый", [])
    for f, t in mandatory:
        assert not (f == 48 and t == 56), "get_all_mandatory_captures не должно содержать 48->56"


def test_biy_capture_into_fortress_allowed_with_batyr():
    """3b. Белый бий может взять в свои ворота если в крепости только батыр (не шатра)."""
    board = _make_board()
    board[48] = "белый бий"
    board[53] = "черная шатра"  # враг на 53
    board[54] = "белый батыр"   # свой батыр в крепости — не блокирует

    from game_engine.pieces.biy import Biy
    b = Biy("белый")
    can = b.can_capture(board, 48, 56, [])
    assert can, "Бий может взять в свои ворота, если в крепости только батыр"

    board_obj = Board(board)
    mandatory = get_all_mandatory_captures(board_obj, "белый", [])
    assert (48, 56) in mandatory, "get_all_mandatory_captures должно содержать 48->56"
    v, _ = validate_move(board, 48, 56, "белый", [])
    assert v, "validate_move(48->56) должно быть True"


# ============================================================
# 4. Одновременное взятие шатрой, батыром, бием
# ============================================================

def test_biy_cannot_move_when_shatra_batyr_and_biy_can_capture():
    """4. Если есть взятие шатрой, батыром и бием, бий не может делать обычный ход."""
    board = _make_board()
    # Батыр на 35: 35→53 через врага на 49 (42 свободна — шатра не блокирует путь)
    board[35] = "белый батыр"
    # Шатра на 20: 20→36 через врага на 28 (не в свою крепость)
    board[20] = "белая шатра"
    # Бий на 48: 48→46 через врага на 47
    board[48] = "белый бий"
    board[49] = "черная шатра"
    board[28] = "черная шатра"
    board[47] = "черная шатра"

    board_obj = Board(board)
    mandatory = get_all_mandatory_captures(board_obj, "белый", [])
    assert len(mandatory) > 0, "Должны быть обязательные взятия"

    attacker_types = {
        board_obj.get_piece_object(f).get_type()
        for f, _ in mandatory
        if board_obj.get_piece_object(f)
    }
    assert attacker_types == {"шатра", "батыр", "бий"}, (
        f"Ожидались взятия шатрой, батыром и бием, получено: {attacker_types}"
    )

    # Бий не может сделать обычный ход (48→41 — пустая клетка, не взятие)
    v, msg = validate_move(board, 48, 41, "белый", [])
    assert not v, "Бий не может сделать обычный ход, когда есть взятие не-биями"
    assert "Нужно бить" in msg, f'Ожидалось "Нужно бить!", получено: {msg}'

    # Бий должен иметь возможность взять
    v_cap, _ = validate_move(board, 48, 46, "белый", [])
    assert v_cap, "Бий должен иметь возможность взять (48→46)"