import i18n from './index';

/** Map server-side Russian messages to i18n keys (with optional {{color}}). */
const SERVER_MESSAGE_MAP = [
  { match: 'Вы отменили игру.', key: 'server.cancelYou' },
  { match: 'Соперник отменил игру.', key: 'server.cancelOpponent' },
  { match: 'Бот не принимает ничью.', key: 'server.drawBotDeclined' },
  { match: 'Вы уже предложили ничью. Ожидание ответа соперника.', key: 'server.drawAlreadyOffered' },
  { match: 'Вы предложили ничью. Ожидание ответа соперника.', key: 'server.drawYouOffered' },
  { match: 'Соперник предлагает ничью. Нажмите ½, чтобы принять.', key: 'server.drawOpponentOffers' },
  { match: 'Ничья! Обоюдное согласие.', key: 'server.drawAgreed' },
  { match: 'Соперник отклонил предложение ничьей.', key: 'server.drawOpponentDeclined' },
  { match: 'Предложение ничьей отменено.', key: 'server.drawOfferCancelled' },
  { match: 'Ожидание согласия соперника на реванш…', key: 'server.rematchWaitSelf' },
  { match: 'Соперник готов к реваншу. Нажмите «Реванш».', key: 'server.rematchWaitOpponent' },
  { match: 'Соперник вышел. Реванш отменён.', key: 'server.rematchOpponentLeft' },
  { match: 'Реванш отменён.', key: 'server.rematchCancelled' },
  { match: 'Ход передан.', key: 'server.movePassed' },
  { match: 'Продолжайте взятие!', key: 'server.continueCapture' },
  { match: 'Продолжайте взятие той же фигурой!', key: 'server.continueSamePiece' },
  { match: 'Нужно бить! Продолжите взятие.', key: 'server.mustCaptureContinue' },
  { match: 'Нужно бить!', key: 'server.mustCapture' },
  { match: 'Ход невозможен', key: 'server.impossibleMove' },
];

const COLOR_IN_MESSAGE = [
  { re: /^Теперь ходит (белый|черный|чёрный)$/i, key: 'server.nowTurn' },
  { re: /^(Белый|Черный|Чёрный) шатра стала батыром!$/i, key: 'server.promotion' },
  { re: /^(Белый|Черный|Чёрный) бий победил!$/i, key: 'result.biyWins' },
];

function normalizeColorToken(raw) {
  const c = raw.toLowerCase();
  if (c.includes('бел')) return i18n.t('colors.white');
  if (c.includes('чер') || c.includes('чёр')) return i18n.t('colors.black');
  return raw;
}

export function translateServerMessage(message) {
  if (!message) return message;
  const text = String(message).trim();

  for (const { match, key } of SERVER_MESSAGE_MAP) {
    if (text === match) return i18n.t(key);
  }

  for (const { re, key } of COLOR_IN_MESSAGE) {
    const m = text.match(re);
    if (m) {
      return i18n.t(key, { color: normalizeColorToken(m[1]) });
    }
  }

  return message;
}

export function translateWsErrorMessage(message) {
  if (!message) return message;
  const map = {
    'Комната уже заполнена': 'errors.roomFull',
    'Игра уже открыта в другой вкладке': 'errors.alreadyInGame',
    'Комната не найдена': 'errors.roomNotFound',
    'Потеряно соединение. Пытаюсь восстановить...': 'errors.connectionLost',
    'Не удалось восстановить соединение. Обновите страницу или вернитесь в лобби.': 'errors.reconnectFailed',
    'Получено некорректное сообщение от сервера': 'errors.malformedMessage',
    'Не удалось разобрать ответ сервера': 'errors.parseFailed',
    'Сервер не отвечает. Проверьте подключение к интернету.': 'errors.serverNoResponse',
    'Сервер недоступен. Попробуйте позже.': 'errors.serverUnavailable',
    'Ошибка соединения': 'errors.connectionError',
  };
  const key = map[message];
  return key ? i18n.t(key) : message;
}

const API_ERROR_MAP = {
  'Требуется авторизация': 'auth.authRequired',
  'Недействительный токен': 'auth.invalidToken',
  'Пользователь не найден': 'auth.userNotFound',
  'Неверное имя пользователя или пароль': 'auth.invalidCredentials',
  'Сессия истекла. Войдите снова.': 'auth.sessionExpired',
  'Неверный текущий пароль': 'auth.wrongPassword',
  'Имя пользователя уже занято. Выберите другое или войдите, если аккаунт уже ваш.': 'auth.usernameTakenRegister',
  'Это имя пользователя уже занято. Выберите другое.': 'auth.usernameTakenProfile',
};

export function translateApiErrorMessage(message) {
  if (!message) return message;
  const key = API_ERROR_MAP[message];
  if (key) return i18n.t(key);
  return translateWsErrorMessage(message);
}
