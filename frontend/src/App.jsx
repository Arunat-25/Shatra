import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AuthNav from './components/AuthNav';
import PageTransition from './components/PageTransition';
import Lobby from './Lobby';
import Game from './Game';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';

const routes = [
  { path: '/', element: <Lobby /> },
  { path: '/login', element: <Login /> },
  { path: '/register', element: <Register /> },
  { path: '/profile', element: <Profile /> },
  { path: '/:roomId', element: <Game /> },
];

const AUTH_NAV_PATHS = new Set(['/', '/login', '/register', '/profile']);

const AUTH_FORM_PATHS = new Set(['/login', '/register', '/profile']);

function AppChrome() {
  const { pathname } = useLocation();
  if (!AUTH_NAV_PATHS.has(pathname)) return null;
  return <AuthNav />;
}

function AppShell() {
  const { pathname } = useLocation();
  const authFormLayout = AUTH_FORM_PATHS.has(pathname);
  const lobbyLayout = pathname === '/';

  return (
    <div
      className={[
        'app-shell',
        authFormLayout ? 'app-shell--auth-form' : '',
        lobbyLayout ? 'app-shell--lobby' : '',
      ].filter(Boolean).join(' ')}
    >
      <AppChrome />
      <main className="app-main">
        <Routes>
          {routes.map(({ path, element }) => (
            <Route
              key={path}
              path={path}
              element={
                path === '/:roomId'
                  ? element
                  : <PageTransition>{element}</PageTransition>
              }
            />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </AuthProvider>
  );
}