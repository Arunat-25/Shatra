import { Sentry } from './sentry';

const CAPTURED_EVENTS = new Set([
  'game_joined',
  'game_started',
  'game_over',
  'ws_fatal_close',
  'ws_reconnect_failed',
]);

export function trackGameEvent(name, data = {}) {
  Sentry.addBreadcrumb({
    category: 'game',
    message: name,
    data,
    level: 'info',
  });

  if (CAPTURED_EVENTS.has(name)) {
    Sentry.captureMessage(name, {
      level: 'info',
      tags: { event: name },
      extra: data,
    });
  }
}

export function trackWsEvent(name, data = {}) {
  Sentry.addBreadcrumb({
    category: 'websocket',
    message: name,
    data,
    level: name.includes('failed') || name.includes('fatal') ? 'warning' : 'info',
  });

  if (name === 'ws_reconnect_failed' || name === 'ws_fatal_close') {
    trackGameEvent(name, data);
  }
}

export function trackApiError(resource, status, attempt) {
  Sentry.addBreadcrumb({
    category: 'api',
    message: 'api_error',
    data: { resource, status, attempt },
    level: 'warning',
  });
}

export function setObservabilityUser(user, clientId) {
  if (clientId) {
    Sentry.setTag('client_id', clientId);
  }
  if (user?.id) {
    Sentry.setUser({ id: String(user.id), username: user.username });
  } else {
    Sentry.setUser(null);
  }
}
