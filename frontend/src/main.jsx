import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import { initSentry } from './observability/sentry';
import { initI18n } from './i18n';
import './fonts.css';
import './index.css';

initSentry();

initI18n().then(() => {
  const root = createRoot(document.getElementById('root'));
  root.render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>,
  );

  setTimeout(() => {
    const splash = document.getElementById('splash-screen');
    if (splash) {
      splash.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
      splash.style.opacity = '0';
      splash.style.transform = 'scale(0.95)';
      setTimeout(() => splash.remove(), 500);
    }
  }, 100);
});
