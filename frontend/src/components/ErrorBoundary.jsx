import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidMount() {
    // Убираем splash, если он ещё виден (например, при ошибке до монтирования App)
    const splash = document.getElementById('splash-screen');
    if (splash) splash.remove();
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-boundary-icon">⚠️</div>
            <h2 className="error-boundary-title">Что-то пошло не так</h2>
            <p className="error-boundary-text">
              Произошла непредвиденная ошибка. Пожалуйста, обновите страницу.
            </p>
            <button
              className="btn-lobby btn-battle"
              onClick={() => window.location.reload()}
              style={{ maxWidth: 280, fontSize: '1rem', padding: '14px 36px' }}
            >
              Обновить страницу
            </button>
            {this.state.error && (
              <details className="error-boundary-details">
                <summary>Технические детали</summary>
                <pre>{this.state.error.message}</pre>
              </details>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}