import i18n from '../i18n';
import { ApiError } from './errors';
import { getAccessToken } from './auth';

const API_BASE = '';

export async function submitBugReport({ description, screenshot, pageUrl, clientId }) {
  const form = new FormData();
  form.append('description', description);
  if (pageUrl) form.append('page_url', pageUrl);
  if (clientId) form.append('client_id', clientId);
  if (screenshot) form.append('screenshot', screenshot);

  const headers = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}/api/bug-reports`, {
    method: 'POST',
    headers,
    body: form,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const detail = err.detail;
    const message = typeof detail === 'string'
      ? detail
      : i18n.t('bugReport.failed');
    throw new ApiError(message, response.status);
  }
  return response.json();
}
