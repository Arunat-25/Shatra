// ===== Цвета фигур =====
export const COLOR_WHITE = 'белый';
export const COLOR_BLACK = 'черный';
export const COLOR_WHITE_INCL = 'бел';

// ===== Типы фигур =====
export const PIECE_BIY = 'бий';
export const PIECE_BATYR = 'батыр';
export const PIECE_SHATRA = 'шатра';

// ===== Типы комнат =====
export const ROOM_QUICK = 'quick';
export const ROOM_FRIEND = 'friend';
export const ROOM_AI = 'ai';

// ===== Типы сообщений =====
export const MSG_INFO = 'info';
export const MSG_ERROR = 'error';
export const MSG_WARNING = 'warning';
export const MSG_VICTORY = 'victory';
export const MSG_SUCCESS = 'success';

// ===== Конфигурация доски =====
export const BOARD_SECTIONS = [
  {
    class: 'field-of-reserve',
    rows: [
      [{ id: 1, color: 'cell-dark' }, { id: 2, color: 'cell-light' }, { id: 3, color: 'cell-dark' }],
      [{ id: 4, color: 'cell-light' }, { id: 5, color: 'cell-dark' }, { id: 6, color: 'cell-light' }],
      [{ id: 7, color: 'cell-dark' }, { id: 8, color: 'cell-light' }, { id: 9, color: 'cell-dark' }],
    ],
  },
  {
    class: 'field-of-king',
    rows: [
      [{ id: 10, color: 'cell-light' }],
    ],
  },
  {
    class: 'main-field',
    rows: [
      [{ id: 11, color: 'cell-dark' }, { id: 12, color: 'cell-light' }, { id: 13, color: 'cell-dark' }, { id: 14, color: 'cell-light' }, { id: 15, color: 'cell-dark' }, { id: 16, color: 'cell-light' }, { id: 17, color: 'cell-dark' }],
      [{ id: 18, color: 'cell-light' }, { id: 19, color: 'cell-dark' }, { id: 20, color: 'cell-light' }, { id: 21, color: 'cell-dark' }, { id: 22, color: 'cell-light' }, { id: 23, color: 'cell-dark' }, { id: 24, color: 'cell-light' }],
      [{ id: 25, color: 'cell-dark' }, { id: 26, color: 'cell-light' }, { id: 27, color: 'cell-dark' }, { id: 28, color: 'cell-light' }, { id: 29, color: 'cell-dark' }, { id: 30, color: 'cell-light' }, { id: 31, color: 'cell-dark' }],
    ],
  },
  {
    class: 'main-field',
    rows: [
      [{ id: 32, color: 'cell-light' }, { id: 33, color: 'cell-dark' }, { id: 34, color: 'cell-light' }, { id: 35, color: 'cell-dark' }, { id: 36, color: 'cell-light' }, { id: 37, color: 'cell-dark' }, { id: 38, color: 'cell-light' }],
      [{ id: 39, color: 'cell-dark' }, { id: 40, color: 'cell-light' }, { id: 41, color: 'cell-dark' }, { id: 42, color: 'cell-light' }, { id: 43, color: 'cell-dark' }, { id: 44, color: 'cell-light' }, { id: 45, color: 'cell-dark' }],
      [{ id: 46, color: 'cell-light' }, { id: 47, color: 'cell-dark' }, { id: 48, color: 'cell-light' }, { id: 49, color: 'cell-dark' }, { id: 50, color: 'cell-light' }, { id: 51, color: 'cell-dark' }, { id: 52, color: 'cell-light' }],
    ],
  },
  {
    class: 'field-of-king',
    rows: [
      [{ id: 53, color: 'cell-light' }],
    ],
  },
  {
    class: 'field-of-reserve',
    rows: [
      [{ id: 54, color: 'cell-dark' }, { id: 55, color: 'cell-light' }, { id: 56, color: 'cell-dark' }],
      [{ id: 57, color: 'cell-light' }, { id: 58, color: 'cell-dark' }, { id: 59, color: 'cell-light' }],
      [{ id: 60, color: 'cell-dark' }, { id: 61, color: 'cell-light' }, { id: 62, color: 'cell-dark' }],
    ],
  },
];

// ===== Временные константы =====
export const MESSAGE_DURATION = 3000;
export const POLL_INTERVAL = 10000;
export const PAGE_TRANSITION_DURATION = 200;

// ===== Пресеты таймера (секунды) =====
export const TIMER_PRESETS = [
  { label: '15 сек', value: 15 },
  { label: '30 сек', value: 30 },
  { label: '1 мин', value: 60 },
  { label: '3 мин', value: 180 },
  { label: '5 мин', value: 300 },
  { label: '10 мин', value: 600 },
  { label: '15 мин', value: 900 },
  { label: '30 мин', value: 1800 },
];

// ===== Пресеты инкремента (добавка за ход) =====
export const INCREMENT_PRESETS = [
  { label: '0 сек', value: 0 },
  { label: '1 сек', value: 1 },
  { label: '2 сек', value: 2 },
  { label: '3 сек', value: 3 },
  { label: '5 сек', value: 5 },
  { label: '10 сек', value: 10 },
  { label: '15 сек', value: 15 },
  { label: '30 сек', value: 30 },
];