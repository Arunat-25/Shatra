/**
 * Оверлей, отображаемый при отключении соперника.
 * @param {{ disconnectCountdown: number }} props
 */
export default function DisconnectOverlay({ disconnectCountdown }) {
  return (
    <div className="opponent-disconnected-overlay">
      <div className="opponent-disconnected-modal">
        <div className="opponent-disconnected-icon">📡</div>
        <h3 className="opponent-disconnected-title">Соперник отключился</h3>
        <p className="opponent-disconnected-text">
          Если соперник не вернётся — ваша победа!
        </p>
        <div className="opponent-disconnected-countdown">
          <span className="countdown-number">{disconnectCountdown}</span>
          <span className="countdown-label">сек</span>
        </div>
      </div>
    </div>
  );
}