import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { isLiteUiEnabled, setLiteUiEnabled, LITE_UI_KEY } from '../ui/liteUiSettings';

const LiteUiContext = createContext(null);

/** In-game lite board preference only (lobby chrome is always simplified). */
export function LiteUiProvider({ children }) {
  const [enabled, setEnabledState] = useState(() => isLiteUiEnabled());

  useEffect(() => {
    const onStorage = (event) => {
      if (event.key !== LITE_UI_KEY) return;
      setEnabledState(event.newValue === 'true');
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const setEnabled = useCallback((value) => {
    const next = Boolean(value);
    setLiteUiEnabled(next);
    setEnabledState(next);
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
