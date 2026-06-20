/** Dev-only layout/debug probes. No network I/O in production builds. */

const DEFAULT_ENDPOINT = 'http://127.0.0.1:7570/ingest/7c8a0073-ab4a-4548-b425-fe00951377e1';

export function isDevProbeEnabled() {
  return import.meta.env.DEV && typeof fetch !== 'undefined';
}

/**
 * @param {Record<string, unknown>} payload
 */
export function sendDevProbe(payload) {
  if (!isDevProbeEnabled()) return;

  const endpoint = import.meta.env.VITE_DEBUG_PROBE_URL || DEFAULT_ENDPOINT;

  fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(payload.sessionId ? { 'X-Debug-Session-Id': String(payload.sessionId) } : {}),
    },
    body: JSON.stringify({ ...payload, timestamp: Date.now() }),
  }).catch(() => {});
}
