import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ApiError, register } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { DISTRICTS } from '../constants/profile';
import { resolveApiErrorMessage } from '../i18n/resolveMessage';
import GameEmblem from '../components/GameEmblem';

export default function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { applyTokens } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [district, setDistrict] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== password2) {
      setError(t('auth.passwordMismatch'));
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      const data = await register({
        username: username.trim(),
        password,
        first_name: firstName.trim() || null,
        last_name: lastName.trim() || null,
        district: district || null,
      });
      applyTokens(data);
      navigate('/');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(resolveApiErrorMessage(err.message));
      } else {
        setError(t('auth.registerFailed'));
      }
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
        <h1>{t('auth.registerTitle')}</h1>
        <p className="auth-subtitle">{t('auth.loginSubtitle')}</p>

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
              minLength={3}
              maxLength={32}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="password">{t('auth.password')}</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="password2">{t('auth.repeatPassword')}</label>
            <input
              id="password2"
              type="password"
              autoComplete="new-password"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              required
            />
          </div>
          <div className="auth-field">
            <label htmlFor="firstName">{t('auth.firstNameOptional')}</label>
            <input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="lastName">{t('auth.lastNameOptional')}</label>
            <input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="district">{t('auth.districtOptional')}</label>
            <select id="district" value={district} onChange={(e) => setDistrict(e.target.value)}>
              <option value="">{t('auth.districtNone')}</option>
              {DISTRICTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" className="btn-lobby btn-primary" disabled={submitting}>
            {submitting ? t('auth.registering') : t('auth.registerButton')}
          </button>
        </form>
        <p className="auth-footer">
          {t('auth.alreadyHaveAccount')}{' '}
          <Link to="/login">{t('auth.loginButton')}</Link>
          {' · '}
          <Link to="/">{t('auth.toHome')}</Link>
        </p>
      </div>
    </div>
  );
}
