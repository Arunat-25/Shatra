/** Paths that use the tutorial / auth-form chrome (nav, locale, lesson layout). */
export function isTutorialPath(pathname) {
  return pathname === '/tutorial' || /^\/tutorial\/\d+$/.test(pathname);
}

export function isTutorialLessonPath(pathname) {
  return /^\/tutorial\/\d+$/.test(pathname);
}
