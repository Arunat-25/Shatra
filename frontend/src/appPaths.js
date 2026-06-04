import { isTutorialPath } from './tutorialPaths';

export const STATIC_APP_PATHS = new Set([
  '/',
  '/login',
  '/register',
  '/profile',
  '/admin',
  '/tutorial',
]);

/** Active game room (dynamic /:roomId), not static app routes. */
export function isGamePath(pathname) {
  if (STATIC_APP_PATHS.has(pathname)) return false;
  if (isTutorialPath(pathname)) return false;
  return true;
}
