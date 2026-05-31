/** Read chart colors from CSS variables (admin page). */
export function getAdminChartColors() {
  if (typeof document === 'undefined') {
    return {
      accent: '#c9a227',
      muted: '#888888',
      line2: '#6b9bd1',
      line3: '#c97b6b',
      grid: 'rgba(255,255,255,0.08)',
      text: '#cccccc',
    };
  }
  const root = document.documentElement;
  const style = getComputedStyle(root);
  const accent = style.getPropertyValue('--accent').trim() || '#c9a227';
  const muted = style.getPropertyValue('--text-muted').trim() || '#888888';
  return {
    accent,
    muted,
    line2: '#6b9bd1',
    line3: '#c97b6b',
    grid: 'rgba(255, 255, 255, 0.08)',
    text: style.getPropertyValue('--text').trim() || '#e8e8e8',
  };
}

export function formatBucketLabel(ts, granularity) {
  const d = new Date(ts);
  if (granularity === 'hour') {
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' });
  }
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
