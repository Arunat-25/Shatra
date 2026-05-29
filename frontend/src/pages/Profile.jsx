import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ApiError, changePassword, updateProfile } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import { DISTRICTS } from '../constants/profile';
import { resolveApiErrorMessage } from '../i18n/resolveMessage';
import GameEmblem from '../components/GameEmblem';

export default function Profile() {
  const { t } = useTranslation();
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

  useEffect(() => {
    if (user) {
      setUsername(user.username || '');
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      setDistrict(user.district || '');
    }
  }, [user]);

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
      <div className="auth-card">
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
                <option key={d} value={d}>{d}</option>
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
        <p className="auth-footer">
          <Link to="/">{t('auth.toHome')}</Link>
        </p>
      </div>
    </div>
  );
}
