import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { submitBugReport } from '../api/bugReports';
import { ApiError } from '../api/errors';
import { getClientId } from '../api';
import { resolveApiErrorMessage } from '../i18n/resolveMessage';
import useEscapeKey from '../hooks/useEscapeKey';

const MAX_SCREENSHOT_BYTES = 3 * 1024 * 1024;
const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const MIN_DESCRIPTION_LEN = 10;
const MAX_DESCRIPTION_LEN = 5000;

export default function BugReportModal({ open, onClose }) {
  const { t } = useTranslation();
  const [description, setDescription] = useState('');
  const [screenshot, setScreenshot] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);
  const closeTimerRef = useRef(null);

  const resetForm = useCallback(() => {
    setDescription('');
    setScreenshot(null);
    setPreviewUrl(null);
    setError('');
    setSuccess(false);
    setSubmitting(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const handleClose = useCallback(() => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    resetForm();
    onClose();
  }, [onClose, resetForm]);

  useEscapeKey(open, handleClose);

  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => () => {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    setError('');
    if (!file) {
      setScreenshot(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      return;
    }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError(t('bugReport.invalidScreenshot'));
      e.target.value = '';
      return;
    }
    if (file.size > MAX_SCREENSHOT_BYTES) {
      setError(t('bugReport.tooLarge'));
      e.target.value = '';
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setScreenshot(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const trimmedDescription = description.trim();
  const trimmedLen = trimmedDescription.length;
  const canSubmit = !submitting
    && trimmedLen >= MIN_DESCRIPTION_LEN
    && trimmedLen <= MAX_DESCRIPTION_LEN;

  const handleDescriptionChange = (e) => {
    setDescription(e.target.value);
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;

    if (trimmedLen < MIN_DESCRIPTION_LEN) {
      setError(t('bugReport.descriptionTooShort'));
      return;
    }
    if (trimmedLen > MAX_DESCRIPTION_LEN) {
      setError(t('bugReport.descriptionTooLong'));
      return;
    }

    setError('');
    setSubmitting(true);
    try {
      await submitBugReport({
        description: trimmedDescription,
        screenshot,
        pageUrl: window.location.href,
        clientId: getClientId(),
      });
      setSuccess(true);
      closeTimerRef.current = setTimeout(handleClose, 2000);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? resolveApiErrorMessage(err.message)
          : t('bugReport.failed'),
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="bug-report-backdrop"
      role="presentation"
      onClick={handleClose}
    >
      <div
        className="auth-card bug-report-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bug-report-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h1 id="bug-report-title">{t('bugReport.title')}</h1>
        <p className="auth-subtitle">{t('bugReport.subtitle')}</p>

        {success ? (
          <p className="bug-report-success">{t('bugReport.success')}</p>
        ) : (
          <form className="auth-form" noValidate onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="bug-description">{t('bugReport.description')}</label>
              <textarea
                id="bug-description"
                className="bug-report-textarea"
                value={description}
                onChange={handleDescriptionChange}
                maxLength={MAX_DESCRIPTION_LEN}
                rows={5}
                disabled={submitting}
              />
              <p className={`bug-report-counter${trimmedLen > MAX_DESCRIPTION_LEN ? ' bug-report-counter--over' : ''}`}>
                {t('bugReport.charCount', { count: trimmedLen, max: MAX_DESCRIPTION_LEN })}
              </p>
              {!submitting && trimmedLen > 0 && trimmedLen < MIN_DESCRIPTION_LEN && (
                <p className="bug-report-hint">{t('bugReport.minCharsHint', { min: MIN_DESCRIPTION_LEN })}</p>
              )}
            </div>
            <div className="auth-field">
              <label htmlFor="bug-screenshot">{t('bugReport.screenshot')}</label>
              <input
                id="bug-screenshot"
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleFileChange}
                disabled={submitting}
              />
              {previewUrl && (
                <img
                  src={previewUrl}
                  alt=""
                  className="bug-report-preview"
                />
              )}
            </div>
            {error && <div className="auth-error">{error}</div>}
            <div className="bug-report-actions">
              <button
                type="button"
                className="btn-lobby"
                onClick={handleClose}
                disabled={submitting}
              >
                {t('bugReport.close')}
              </button>
              <button
                type="submit"
                className="btn-lobby btn-primary"
                disabled={!canSubmit}
                title={submitting ? t('bugReport.submitting') : undefined}
              >
                {submitting ? t('bugReport.submitting') : t('bugReport.submit')}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
