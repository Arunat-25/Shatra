/** Read chart colors from CSS variables (admin page). */
export function getAdminChartColors() {
  const gridFallback = 'rgba(154, 102, 0, 0.14)';
  const textFallback = '#271200';
  if (typeof document === 'undefined') {
    return {
      accent: '#9A6600',
      muted: 'rgba(39, 18, 0, 0.50)',
      line2: '#106E68',
      line3: '#AA2B10',
      grid: gridFallback,
      text: textFallback,
    };
  }
  const root = document.documentElement;
  const style = getComputedStyle(root);
  const accent = style.getPropertyValue('--gold').trim() || '#9A6600';
  const muted = style.getPropertyValue('--text-muted').trim() || 'rgba(39, 18, 0, 0.50)';
  const text = style.getPropertyValue('--text-primary').trim() || textFallback;
  const borderSubtle = style.getPropertyValue('--border-subtle').trim();
  return {
    accent,
    muted,
    line2: '#106E68',
    line3: '#AA2B10',
    grid: borderSubtle || gridFallback,
    text,
  };
}

export function getAdminChartTooltipStyle(colors) {
  return {
    background: 'var(--bg-elevated, #FAF5E8)',
    border: `1px solid ${colors.grid}`,
    borderRadius: 8,
    fontSize: 12,
    color: colors.text,
  };
}

export function formatBucketLabel(ts, granularity) {
  const d = new Date(ts);
  if (granularity === 'hour') {
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' });
  }
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
