import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../api/auth';
import { resolveApiErrorMessage } from '../i18n/resolveMessage';
import GameEmblem from '../components/GameEmblem';

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const passwordChanged = searchParams.get('passwordChanged') === '1';
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate('/');
    } catch (err) {
      setError(
        err instanceof ApiError
          ? resolveApiErrorMessage(err.message)
          : t('auth.loginFailed'),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__emblem">
          <GameEmblem size={56} />
        </div>
        <h1>{t('auth.loginTitle')}</h1>
        <p className="auth-subtitle">{t('auth.loginSubtitle')}</p>

        {passwordChanged && (
          <p className="auth-subtitle" style={{ color: 'var(--gold)' }}>
            {t('auth.passwordChangedLogin')}
          </p>
        )}

        <p className="auth-warning">{t('auth.passwordWarning')}</p>

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
            />
          </div>
          <div className="auth-field">
            <label htmlFor="password">{t('auth.password')}</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" className="btn-lobby btn-primary" disabled={submitting}>
            {submitting ? t('auth.loggingIn') : t('auth.loginButton')}
          </button>
        </form>
        <p className="auth-footer">
          <Link to="/register">{t('nav.register')}</Link>
          {' · '}
          <Link to="/">{t('auth.toHome')}</Link>
        </p>
      </div>
    </div>
  );
}
