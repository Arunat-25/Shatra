/** Allow only http/https URLs for user-provided links. */
export function isSafeHttpUrl(value) {
  if (!value || typeof value !== 'string') {
    return false;
  }
  const text = value.trim();
  if (!text) {
    return false;
  }
  try {
    const parsed = new URL(text);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && Boolean(parsed.hostname);
  } catch {
    return false;
  }
}
