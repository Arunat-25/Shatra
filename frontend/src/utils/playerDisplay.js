import { COLOR_WHITE } from '../constants';

export function playerForColor(playersInfo, color) {
  return playersInfo?.find((p) => p.color === color) ?? null;
}

export function playerNickname(player, color, t) {
  if (!player) {
    return color === COLOR_WHITE ? t('colors.whitePl') : t('colors.blackPl');
  }
  if (player.display_name) return player.display_name;
  if (!player.is_anonymous && player.username) return player.username;
  return t('lobby.anonymous');
}

export function playerRating(player) {
  if (player && !player.is_anonymous && player.rating != null) {
    return player.rating;
  }
  return null;
}

export function playerRatingDelta(player, gameOver) {
  if (!gameOver || !player || player.is_anonymous) return null;
  if (player.rating_delta == null) return null;
  return player.rating_delta;
}

/** Tooltip on nick hover: includes Elo for registered players. */
export function playerHoverTitle(player, nickname, t) {
  if (player && !player.is_anonymous && player.rating != null) {
    return t('game.playerRatingTooltip', { name: nickname, rating: player.rating });
  }
  return nickname;
}

export function playerDisplayForColor(playersInfo, color, t, gameOver = false) {
  const player = playerForColor(playersInfo, color);
  const nickname = playerNickname(player, color, t);
  const title = playerHoverTitle(player, nickname, t);
  const rating = playerRating(player);
  const ratingDelta = playerRatingDelta(player, gameOver);
  return { player, nickname, title, rating, ratingDelta };
}
