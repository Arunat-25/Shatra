import { useCallback, useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ApiError, changePassword, fetchMyGames, updateProfile } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { DISTRICTS } from '../constants/profile';
import { useDistrictLabel } from '../i18n/districtLabel';
import { resolveApiErrorMessage } from '../i18n/resolveMessage';
import GameEmblem from '../components/GameEmblem';

const PAGE_SIZE = 20;

function formatOpponent(display, t) {
  if (display === '__ai__') return t('auth.opponentAi');
  if (display === '__anonymous__') return t('auth.opponentAnonymous');
  return display;
}

function formatResult(result, t) {
  if (result === 'win') return t('auth.resultWin');
  if (result === 'loss') return t('auth.resultLoss');
  return t('auth.resultDraw');
}

function formatRoomType(roomType, t) {
  if (roomType === 'private') return t('auth.roomTypePrivate');
  if (roomType === 'ai') return t('auth.roomTypeAi');
  return t('auth.roomTypePublic');
}

function formatGameDate(iso, locale) {
  try {
    return new Date(iso).toLocaleString(locale);
  } catch {
    return iso;
  }
}

export default function Profile() {
  const { t, i18n } = useTranslation();
  const districtLabel = useDistrictLabel();
  const { user, loading, isAuthenticated, setUser, logout } = useAuth();
  const [username, setUsername] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [district, setDistrict] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);
  const [games, setGames] = useState([]);
  const [gamesTotal, setGamesTotal] = useState(0);
  const [gamesLoading, setGamesLoading] = useState(false);
  const [gamesError, setGamesError] = useState('');

  useEffect(() => {
    if (user) {
      setUsername(user.username || '');
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      setDistrict(user.district || '');
    }
  }, [user]);

  const loadGames = useCallback(async (offset = 0, append = false) => {
    setGamesLoading(true);
    setGamesError('');
    try {
      const data = await fetchMyGames({ limit: PAGE_SIZE, offset });
      setGames((prev) => (append ? [...prev, ...data.items] : data.items));
      setGamesTotal(data.total);
    } catch (err) {
      setGamesError(err instanceof ApiError ? resolveApiErrorMessage(err.message) : t('auth.gamesLoadFailed'));
    } finally {
      setGamesLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (isAuthenticated && !loading) {
      void loadGames(0, false);
    }
  }, [isAuthenticated, loading, loadGames]);

  if (loading) {
    return (
      <div className="auth-page">
        <p className="auth-subtitle">{t('auth.loading')}</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      const updated = await updateProfile({
        username: username.trim(),
        first_name: firstName.trim() || null,
        last_name: lastName.trim() || null,
        district: district || null,
      });
      setUser(updated);
      setSuccess(t('auth.profileSaved'));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(resolveApiErrorMessage(err.message));
      } else {
        setError(t('auth.saveFailed'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError('');
    if (newPassword !== confirmPassword) {
      setPasswordError(t('auth.passwordMismatch'));
      return;
    }
    setPasswordSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      await logout();
      window.location.href = '/login?passwordChanged=1';
    } catch (err) {
      if (err instanceof ApiError) {
        setPasswordError(resolveApiErrorMessage(err.message));
      } else {
        setPasswordError(t('auth.changePasswordFailed'));
      }
    } finally {
      setPasswordSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--wide">
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
          <GameEmblem size={56} />
        </div>
        <h1>{t('auth.profileTitle')}</h1>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="username">{t('auth.username')}</label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={32}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="firstName">{t('auth.firstName')}</label>
            <input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="lastName">{t('auth.lastName')}</label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="district">{t('auth.district')}</label>
            <select id="district" value={district} onChange={(e) => setDistrict(e.target.value)}>
              <option value="">{t('auth.districtNone')}</option>
              {DISTRICTS.map((d) => (
                <option key={d} value={d}>{districtLabel(d)}</option>
              ))}
            </select>
          </div>
          {error && <div className="auth-error">{error}</div>}
          {success && <p className="auth-subtitle" style={{ color: 'var(--gold)', margin: 0 }}>{success}</p>}
          <button type="submit" className="btn-lobby btn-primary" disabled={submitting}>
            {submitting ? t('auth.saving') : t('auth.save')}
          </button>
        </form>
        <hr style={{ margin: '24px 0', borderColor: 'var(--border)' }} />
        <h2 style={{ fontSize: '1.1rem', marginBottom: 12 }}>{t('auth.changePassword')}</h2>
        <form className="auth-form" onSubmit={handlePasswordSubmit}>
          <div className="auth-field">
            <label htmlFor="currentPassword">{t('auth.currentPassword')}</label>
            <input
              id="currentPassword"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="auth-field">
            <label htmlFor="newPassword">{t('auth.newPassword')}</label>
            <input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="confirmPassword">{t('auth.confirmPassword')}</label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          {passwordError && <div className="auth-error">{passwordError}</div>}
          <button type="submit" className="btn-lobby btn-secondary" disabled={passwordSubmitting}>
            {passwordSubmitting ? t('auth.changingPassword') : t('auth.changePassword')}
          </button>
        </form>

        <hr style={{ margin: '24px 0', borderColor: 'var(--border)' }} />
        <h2 className="profile-games-title">{t('auth.gamesTitle')}</h2>
        {gamesError && <div className="auth-error">{gamesError}</div>}
        {gamesLoading && games.length === 0 ? (
          <p className="auth-subtitle">{t('auth.gamesLoading')}</p>
        ) : games.length === 0 ? (
          <p className="auth-subtitle">{t('auth.gamesEmpty')}</p>
        ) : (
          <div className="profile-games-table-wrap">
            <table className="profile-games-table">
              <thead>
                <tr>
                  <th>{t('auth.gameDate')}</th>
                  <th>{t('auth.gameOpponent')}</th>
                  <th>{t('auth.gameResult')}</th>
                  <th>{t('auth.gameType')}</th>
                  <th>{t('auth.gameMoves')}</th>
                </tr>
              </thead>
              <tbody>
                {games.map((game) => (
                  <tr key={game.id}>
                    <td>{formatGameDate(game.finished_at, i18n.language)}</td>
                    <td>{formatOpponent(game.opponent_display, t)}</td>
                    <td className={`profile-games-result profile-games-result--${game.result}`}>
                      {formatResult(game.result, t)}
                    </td>
                    <td>{formatRoomType(game.room_type, t)}</td>
                    <td>{game.moves_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {games.length < gamesTotal && (
          <button
            type="button"
            className="btn-lobby btn-secondary profile-games-load-more"
            disabled={gamesLoading}
            onClick={() => void loadGames(games.length, true)}
          >
            {gamesLoading ? t('auth.gamesLoading') : t('auth.gamesLoadMore')}
          </button>
        )}

        <p className="auth-footer">
          <Link to="/">{t('auth.toHome')}</Link>
        </p>
      </div>
    </div>
  );
}
