import i18n from '../i18n';
import { authFetch, getAccessToken } from './auth';
import { ApiError } from './errors';

export function fetchRegistrationStats(params = {}) {
  const qs = new URLSearchParams();
  if (params.period) qs.set('period', params.period);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  const query = qs.toString();
  return authFetch(`/api/admin/stats/registrations${query ? `?${query}` : ''}`);
}

export function fetchOnlineStats(at) {
  const qs = new URLSearchParams({ at });
  return authFetch(`/api/admin/stats/online?${qs.toString()}`);
}

export function fetchOnlinePeriodStats(params = {}) {
  const qs = new URLSearchParams();
  if (params.period) qs.set('period', params.period);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  const query = qs.toString();
  return authFetch(`/api/admin/stats/online/period${query ? `?${query}` : ''}`);
}

export function fetchGamesStats(params = {}) {
  const qs = new URLSearchParams();
  if (params.period) qs.set('period', params.period);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  if (params.room_type) qs.set('room_type', params.room_type);
  if (params.anonymous_players) qs.set('anonymous_players', params.anonymous_players);
  const query = qs.toString();
  return authFetch(`/api/admin/stats/games${query ? `?${query}` : ''}`);
}

function buildPeriodQuery(params = {}) {
  const qs = new URLSearchParams();
  if (params.period) qs.set('period', params.period);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  return qs.toString();
}

export function fetchRegistrationSeries(params = {}) {
  const query = buildPeriodQuery(params);
  return authFetch(`/api/admin/stats/registrations/series${query ? `?${query}` : ''}`);
}

export function fetchOnlineSeries(params = {}) {
  const query = buildPeriodQuery(params);
  return authFetch(`/api/admin/stats/online/series${query ? `?${query}` : ''}`);
}

export function fetchGamesSeries(params = {}) {
  const qs = new URLSearchParams();
  if (params.period) qs.set('period', params.period);
  if (params.from) qs.set('from', params.from);
  if (params.to) qs.set('to', params.to);
  if (params.room_type) qs.set('room_type', params.room_type);
  if (params.anonymous_players) qs.set('anonymous_players', params.anonymous_players);
  const query = qs.toString();
  return authFetch(`/api/admin/stats/games/series${query ? `?${query}` : ''}`);
}

export function fetchBugReports(params = {}) {
  const qs = new URLSearchParams();
  if (params.limit != null) qs.set('limit', String(params.limit));
  if (params.offset != null) qs.set('offset', String(params.offset));
  const query = qs.toString();
  return authFetch(`/api/admin/bug-reports${query ? `?${query}` : ''}`);
}

export async function fetchBugReportScreenshotBlob(id) {
  const headers = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`/api/admin/bug-reports/${id}/screenshot`, { headers });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const detail = err.detail;
    const message = typeof detail === 'string'
      ? detail
      : i18n.t('errors.genericHttp', { status: response.status });
    throw new ApiError(message, response.status);
  }
  return response.blob();
}
