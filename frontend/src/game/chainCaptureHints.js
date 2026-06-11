/** When to auto-request capture hints after a chain step (Game.jsx useEffect). */
export function shouldRequestChainHints(state) {
  if (state.waiting || state.gameOver || state.viewingHistoryIndex !== null) return false;
  if (state.moversColor !== state.myColor) return false;
  if (state.posForMandatoryCapture == null) return false;
  return true;
}
