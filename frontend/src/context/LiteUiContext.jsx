import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { isLiteUiEnabled, setLiteUiEnabled, LITE_UI_KEY } from '../ui/liteUiSettings';

const LiteUiContext = createContext(null);

function applyLiteUiClass(enabled) {
  document.documentElement.classList.toggle('app-shell--lite-ui', enabled);
}

export function LiteUiProvider({ children }) {
  const [enabled, setEnabledState] = useState(() => isLiteUiEnabled());

  useEffect(() => {
    applyLiteUiClass(enabled);
  }, [enabled]);

  useEffect(() => {
    const onStorage = (event) => {
      if (event.key !== LITE_UI_KEY) return;
      const next = event.newValue === 'true';
      setEnabledState(next);
      applyLiteUiClass(next);
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const setEnabled = useCallback((value) => {
    const next = Boolean(value);
    setLiteUiEnabled(next);
    setEnabledState(next);
    applyLiteUiClass(next);
  }, []);

  const toggle = useCallback(() => {
    setEnabled(!enabled);
  }, [enabled, setEnabled]);

  const value = useMemo(
    () => ({ enabled, setEnabled, toggle }),
    [enabled, setEnabled, toggle],
  );

  return (
    <LiteUiContext.Provider value={value}>
      {children}
    </LiteUiContext.Provider>
  );
}

export function useLiteUi() {
  const ctx = useContext(LiteUiContext);
  if (!ctx) {
    throw new Error('useLiteUi must be used within LiteUiProvider');
  }
  return ctx;
}
