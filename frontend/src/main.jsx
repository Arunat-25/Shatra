import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import './index.css';

// Remove the splash screen once React mounts
function removeSplash() {
  const splash = document.getElementById('splash-screen');
  if (splash) {
    splash.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
    splash.style.opacity = '0';
    splash.style.transform = 'scale(0.95)';
    setTimeout(() => splash.remove(), 500);
  }
}

const root = createRoot(document.getElementById('root'));
root.render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);

// Splash screen removal after React is done
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    removeSplash();
  });
});