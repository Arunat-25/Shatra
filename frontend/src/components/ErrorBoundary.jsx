import { Component } from 'react';
import { withTranslation } from 'react-i18next';
import { Sentry } from '../observability/sentry';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    Sentry.captureException(error, { contexts: { react: info } });
  }

  componentDidMount() {
    const splash = document.getElementById('splash-screen');
    if (splash) splash.remove();
  }

  render() {
    const { t, children } = this.props;
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-boundary-icon">⚠️</div>
            <h2 className="error-boundary-title">{t('errorBoundary.title')}</h2>
            <p className="error-boundary-text">
              {t('errorBoundary.text')}
            </p>
            <button
              className="btn-lobby btn-battle"
              onClick={() => window.location.reload()}
              style={{ maxWidth: 280, fontSize: '1rem', padding: '14px 36px' }}
            >
              {t('errorBoundary.reload')}
            </button>
            {this.state.error && (
              <details className="error-boundary-details">
                <summary>{t('errorBoundary.details')}</summary>
                <pre>{this.state.error.message}</pre>
              </details>
            )}
          </div>
        </div>
      );
    }
    return children;
  }
}

export default withTranslation()(ErrorBoundary);
