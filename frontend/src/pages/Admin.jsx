import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  fetchGamesSeries,
  fetchGamesStats,
  fetchOnlinePeriodStats,
  fetchOnlineSeries,
  fetchOnlineStats,
  fetchBugReportScreenshotBlob,
  fetchBugReports,
  fetchRegistrationSeries,
  fetchRegistrationStats,
} from '../api/admin';
import { ApiError } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { resolveApiErrorMessage } from '../i18n/resolveMessage';
import AdminLineChart from '../components/admin/AdminLineChart';
import AdminMultiLineChart from '../components/admin/AdminMultiLineChart';
import AdminPieChart from '../components/admin/AdminPieChart';

const PERIODS = ['1h', '3h', '6h', '12h', 'today', '24h', '7d', '30d', 'all'];
const ROOM_TYPES = ['all', 'public', 'private', 'ai'];
const ANON_COUNTS = ['all', '0', '1', '2'];

function buildStatsQuery(period) {
  if (period === 'today') {
    const now = new Date();
    const start = new Date(now);
    start.setHours(0, 0, 0, 0);
    return { from: start.toISOString(), to: now.toISOString() };
  }
  return { period };
}

function toLocalInputValue(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function localInputToIso(value) {
  if (!value) return null;
  const dt = new Date(value);
  return Number.isNaN(dt.getTime()) ? null : dt.toISOString();
}

function StatCard({ label, value }) {
  return (
    <div className="admin-stat-card">
      <span className="admin-stat-card__label">{label}</span>
      <strong className="admin-stat-card__value">{value}</strong>
    </div>
  );
}

export default function Admin() {
  const { t } = useTranslation();
  const { user, loading, isAuthenticated } = useAuth();
  const [period, setPeriod] = useState('7d');
  const [onlineStatsPeriod, setOnlineStatsPeriod] = useState('7d');
  const [onlineAtLocal, setOnlineAtLocal] = useState(() => toLocalInputValue());
  const [roomType, setRoomType] = useState('all');
  const [anonymousPlayers, setAnonymousPlayers] = useState('all');
  const [registrations, setRegistrations] = useState(null);
  const [registrationSeries, setRegistrationSeries] = useState(null);
  const [onlinePeriod, setOnlinePeriod] = useState(null);
  const [onlineSeries, setOnlineSeries] = useState(null);
  const [online, setOnline] = useState(null);
  const [games, setGames] = useState(null);
  const [gamesSeries, setGamesSeries] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [bugReports, setBugReports] = useState(null);
  const [expandedBugId, setExpandedBugId] = useState(null);
  const [screenshotUrls, setScreenshotUrls] = useState({});
  const screenshotUrlsRef = useRef({});

  const chartEmpty = t('admin.chartEmpty');

  const loadRegistrationsAndGames = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const query = buildStatsQuery(period);
      const gameQuery = { ...query, room_type: roomType, anonymous_players: anonymousPlayers };
      const [reg, regSeries, gameStats, gameSeriesData] = await Promise.all([
        fetchRegistrationStats(query),
        fetchRegistrationSeries(query),
        fetchGamesStats(gameQuery),
        fetchGamesSeries(gameQuery),
      ]);
      setRegistrations(reg);
      setRegistrationSeries(regSeries);
      setGames(gameStats);
      setGamesSeries(gameSeriesData);
    } catch (err) {
      setError(resolveApiErrorMessage(err instanceof ApiError ? err.message : err, t));
    } finally {
      setBusy(false);
    }
  }, [period, roomType, anonymousPlayers, t]);

  const loadOnlinePeriodStats = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const query = buildStatsQuery(onlineStatsPeriod);
      const [periodData, seriesData] = await Promise.all([
        fetchOnlinePeriodStats(query),
        fetchOnlineSeries(query),
      ]);
      setOnlinePeriod(periodData);
      setOnlineSeries(seriesData);
    } catch (err) {
      setError(resolveApiErrorMessage(err instanceof ApiError ? err.message : err, t));
    } finally {
      setBusy(false);
    }
  }, [onlineStatsPeriod, t]);

  const loadOnlineStats = useCallback(async () => {
    const iso = localInputToIso(onlineAtLocal);
    if (!iso) {
      setError(t('admin.invalidDateTime'));
      return;
    }
    setBusy(true);
    setError('');
    try {
      const data = await fetchOnlineStats(iso);
      setOnline(data);
    } catch (err) {
      setError(resolveApiErrorMessage(err instanceof ApiError ? err.message : err, t));
    } finally {
      setBusy(false);
    }
  }, [onlineAtLocal, t]);

  const loadBugReports = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const data = await fetchBugReports({ limit: 50 });
      setBugReports(data);
    } catch (err) {
      setError(resolveApiErrorMessage(err instanceof ApiError ? err.message : err, t));
    } finally {
      setBusy(false);
    }
  }, [t]);

  useEffect(() => {
    if (!loading && user?.is_admin) {
      loadRegistrationsAndGames();
      loadOnlinePeriodStats();
      loadBugReports();
    }
  }, [loading, user, loadRegistrationsAndGames, loadOnlinePeriodStats, loadBugReports]);

  useEffect(() => {
    if (!expandedBugId || !bugReports?.items) return undefined;
    const item = bugReports.items.find((r) => r.id === expandedBugId);
    if (!item?.has_screenshot || screenshotUrlsRef.current[expandedBugId]) {
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const blob = await fetchBugReportScreenshotBlob(expandedBugId);
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        screenshotUrlsRef.current[expandedBugId] = url;
        setScreenshotUrls((prev) => ({ ...prev, [expandedBugId]: url }));
      } catch (err) {
        if (!cancelled) {
          setError(resolveApiErrorMessage(err instanceof ApiError ? err.message : err, t));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [expandedBugId, bugReports, t]);

  useEffect(() => () => {
    Object.values(screenshotUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const gamesPieByRoom = useMemo(() => {
    if (!games?.by_room_type) return [];
    return Object.entries(games.by_room_type).map(([key, value]) => ({
      name: t(`admin.roomTypes.${key}`),
      value,
    }));
  }, [games, t]);

  const gamesPieByAnon = useMemo(() => {
    if (!games?.by_anonymous_count) return [];
    return Object.entries(games.by_anonymous_count).map(([key, value]) => ({
      name: t(`admin.anonymousCounts.${key}`),
      value,
    }));
  }, [games, t]);

  if (loading) {
    return (
      <div className="admin-page">
        <p>{t('auth.loading')}</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!user?.is_admin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="admin-page">
      <header className="admin-header">
        <div>
          <h1>{t('admin.title')}</h1>
          <p className="admin-subtitle">{t('admin.subtitle')}</p>
        </div>
        <Link to="/" className="admin-link">{t('auth.toHome')}</Link>
      </header>

      {error && (
        <div className="admin-error" role="alert">
          {error}
        </div>
      )}

      <section className="admin-section">
        <h2>{t('admin.registrations')}</h2>
        <div className="admin-controls">
          <label className="admin-field">
            <span>{t('admin.period')}</span>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              {PERIODS.map((p) => (
                <option key={p} value={p}>{t(`admin.periods.${p}`)}</option>
              ))}
            </select>
          </label>
          <button type="button" className="admin-btn" onClick={loadRegistrationsAndGames} disabled={busy}>
            {t('admin.refresh')}
          </button>
        </div>
        {registrations && (
          <StatCard label={t('admin.registrationsTotal')} value={registrations.total} />
        )}
        {registrationSeries && (
          <>
            <h3 className="admin-subheading">{t('admin.charts.registrations')}</h3>
            <AdminLineChart
              buckets={registrationSeries.buckets}
              granularity={registrationSeries.granularity}
              emptyLabel={chartEmpty}
            />
          </>
        )}
      </section>

      <section className="admin-section">
        <h2>{t('admin.online')}</h2>
        <p className="admin-hint">{t('admin.onlinePeriodHint')}</p>
        <h3 className="admin-subheading">{t('admin.onlinePeriod')}</h3>
        <div className="admin-controls">
          <label className="admin-field">
            <span>{t('admin.period')}</span>
            <select
              value={onlineStatsPeriod}
              onChange={(e) => setOnlineStatsPeriod(e.target.value)}
            >
              {PERIODS.map((p) => (
                <option key={p} value={p}>{t(`admin.periods.${p}`)}</option>
              ))}
            </select>
          </label>
          <button type="button" className="admin-btn" onClick={loadOnlinePeriodStats} disabled={busy}>
            {t('admin.refresh')}
          </button>
        </div>
        {onlinePeriod && (
          <div className="admin-stat-grid">
            <StatCard label={t('admin.onlineUniqueInPeriod')} value={onlinePeriod.total_unique} />
            <StatCard label={t('admin.onlineRegistered')} value={onlinePeriod.registered_unique} />
            <StatCard label={t('admin.onlineAnonymous')} value={onlinePeriod.anonymous_unique} />
          </div>
        )}
        {onlineSeries && (
          <>
            <p className="admin-hint">{t('admin.charts.onlineHint')}</p>
            <h3 className="admin-subheading">{t('admin.charts.online')}</h3>
            <AdminMultiLineChart
              buckets={onlineSeries.buckets}
              granularity={onlineSeries.granularity}
              emptyLabel={chartEmpty}
            />
          </>
        )}
        <h3 className="admin-subheading">{t('admin.onlineSnapshot')}</h3>
        <div className="admin-controls">
          <label className="admin-field">
            <span>{t('admin.onlineAt')}</span>
            <input
              type="datetime-local"
              value={onlineAtLocal}
              onChange={(e) => setOnlineAtLocal(e.target.value)}
            />
          </label>
          <button type="button" className="admin-btn" onClick={loadOnlineStats} disabled={busy}>
            {t('admin.show')}
          </button>
        </div>
        {online && (
          <div className="admin-stat-grid">
            <StatCard label={t('admin.onlineTotal')} value={online.total_unique} />
            <StatCard label={t('admin.onlineRegistered')} value={online.registered_unique} />
            <StatCard label={t('admin.onlineAnonymous')} value={online.anonymous_unique} />
          </div>
        )}
      </section>

      <section className="admin-section">
        <h2>{t('admin.games')}</h2>
        <div className="admin-controls admin-controls--wrap">
          <label className="admin-field">
            <span>{t('admin.period')}</span>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              {PERIODS.map((p) => (
                <option key={p} value={p}>{t(`admin.periods.${p}`)}</option>
              ))}
            </select>
          </label>
          <label className="admin-field">
            <span>{t('admin.roomType')}</span>
            <select value={roomType} onChange={(e) => setRoomType(e.target.value)}>
              {ROOM_TYPES.map((rt) => (
                <option key={rt} value={rt}>{t(`admin.roomTypes.${rt}`)}</option>
              ))}
            </select>
          </label>
          <label className="admin-field">
            <span>{t('admin.anonymousPlayers')}</span>
            <select value={anonymousPlayers} onChange={(e) => setAnonymousPlayers(e.target.value)}>
              {ANON_COUNTS.map((c) => (
                <option key={c} value={c}>{t(`admin.anonymousCounts.${c}`)}</option>
              ))}
            </select>
          </label>
          <button type="button" className="admin-btn" onClick={loadRegistrationsAndGames} disabled={busy}>
            {t('admin.refresh')}
          </button>
        </div>
        {games && (
          <>
            <StatCard label={t('admin.gamesTotal')} value={games.total} />
            {gamesSeries && (
              <>
                <h3 className="admin-subheading">{t('admin.charts.games')}</h3>
                <AdminLineChart
                  buckets={gamesSeries.buckets}
                  granularity={gamesSeries.granularity}
                  emptyLabel={chartEmpty}
                />
              </>
            )}
            <div className="admin-chart-grid">
              <div className="admin-chart-block">
                <h3>{t('admin.byRoomType')}</h3>
                <AdminPieChart data={gamesPieByRoom} emptyLabel={chartEmpty} />
              </div>
              <div className="admin-chart-block">
                <h3>{t('admin.byAnonymous')}</h3>
                <AdminPieChart data={gamesPieByAnon} emptyLabel={chartEmpty} />
              </div>
            </div>
          </>
        )}
      </section>

      <section className="admin-section">
        <h2>{t('admin.bugReports')}</h2>
        <div className="admin-controls">
          <button type="button" className="admin-btn" onClick={loadBugReports} disabled={busy}>
            {t('admin.refresh')}
          </button>
        </div>
        {bugReports && (
          <>
            <p className="admin-hint">{t('admin.bugReportsTotal', { count: bugReports.total })}</p>
            {bugReports.items.length === 0 ? (
              <p className="admin-chart-empty">{t('admin.bugReportsEmpty')}</p>
            ) : (
              <div className="admin-bug-reports">
                {bugReports.items.map((report) => {
                  const expanded = expandedBugId === report.id;
                  const preview = report.description.length > 120
                    ? `${report.description.slice(0, 120)}…`
                    : report.description;
                  const reporter = report.username || report.client_id || t('admin.bugReportsAnonymous');
                  return (
                    <div key={report.id} className="admin-bug-report">
                      <button
                        type="button"
                        className="admin-bug-report__header"
                        onClick={() => setExpandedBugId(expanded ? null : report.id)}
                        aria-expanded={expanded}
                      >
                        <span className="admin-bug-report__date">
                          {new Date(report.created_at).toLocaleString()}
                        </span>
                        <span className="admin-bug-report__reporter">{reporter}</span>
                        <span className="admin-bug-report__preview">{preview}</span>
                      </button>
                      {expanded && (
                        <div className="admin-bug-report__body">
                          <p className="admin-bug-report__description">{report.description}</p>
                          {report.page_url && (
                            <p className="admin-bug-report__meta">
                              <span>{t('admin.bugReportsPage')}</span>
                              {' '}
                              <a href={report.page_url} target="_blank" rel="noreferrer">
                                {report.page_url}
                              </a>
                            </p>
                          )}
                          {report.user_agent && (
                            <p className="admin-bug-report__meta">
                              <span>{t('admin.bugReportsUserAgent')}</span>
                              {' '}
                              {report.user_agent}
                            </p>
                          )}
                          {report.has_screenshot && screenshotUrls[report.id] && (
                            <img
                              src={screenshotUrls[report.id]}
                              alt=""
                              className="admin-bug-report__screenshot"
                            />
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
