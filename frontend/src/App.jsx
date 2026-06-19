import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { LiteUiProvider } from './context/LiteUiContext';
import AuthNav from './components/AuthNav';
import PageTransition from './components/PageTransition';
import Lobby from './Lobby';
import { isTutorialPath, isTutorialLessonPath } from './tutorialPaths';
import { isGamePath } from './appPaths';

const Game = lazy(() => import('./Game'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Profile = lazy(() => import('./pages/Profile'));
const Tutorial = lazy(() => import('./pages/Tutorial'));
const TutorialSection1 = lazy(() => import('./pages/TutorialSection1'));
const TutorialSection2 = lazy(() => import('./pages/TutorialSection2'));
const TutorialSection3 = lazy(() => import('./pages/TutorialSection3'));
const TutorialSection4 = lazy(() => import('./pages/TutorialSection4'));
const TutorialSection5 = lazy(() => import('./pages/TutorialSection5'));
const Admin = lazy(() => import('./pages/Admin'));

function RouteFallback() {
  return (
    <div className="route-fallback" aria-busy="true" aria-live="polite">
      <div className="waiting-spinner" />
    </div>
  );
}

function AdminFallback() {
  return (
    <div className="admin-page">
      <p>…</p>
    </div>
  );
}

function suspend(element, withTransition = false) {
  const deferred = <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
  return withTransition ? <PageTransition>{deferred}</PageTransition> : deferred;
}

const routes = [
  { path: '/', element: <Lobby /> },
  { path: '/login', element: suspend(<Login />, true) },
  { path: '/register', element: suspend(<Register />, true) },
  { path: '/profile', element: suspend(<Profile />, true) },
  { path: '/tutorial', element: suspend(<Tutorial />, true) },
  { path: '/tutorial/1', element: suspend(<TutorialSection1 />, true) },
  { path: '/tutorial/2', element: suspend(<TutorialSection2 />, true) },
  { path: '/tutorial/3', element: suspend(<TutorialSection3 />, true) },
  { path: '/tutorial/4', element: suspend(<TutorialSection4 />, true) },
  { path: '/tutorial/5', element: suspend(<TutorialSection5 />, true) },
  {
    path: '/admin',
    element: (
      <Suspense fallback={<AdminFallback />}>
        <Admin />
      </Suspense>
    ),
  },
  { path: '/:roomId', element: suspend(<Game />) },
];

const AUTH_FORM_PATHS = new Set(['/login', '/register', '/profile', '/admin', '/tutorial']);

function AppShell() {
  const { pathname } = useLocation();
  const tutorialLessonLayout = isTutorialLessonPath(pathname);
  const authFormLayout =
    (AUTH_FORM_PATHS.has(pathname) || isTutorialPath(pathname)) && !tutorialLessonLayout;
  const lobbyLayout = pathname === '/';
  const gameLayout = isGamePath(pathname);

  return (
    <div
      className={[
        'app-shell',
        'app-shell--chrome',
        authFormLayout ? 'app-shell--auth-form' : '',
        tutorialLessonLayout ? 'app-shell--tutorial-lesson' : '',
        lobbyLayout ? 'app-shell--lobby' : '',
        gameLayout ? 'app-shell--game' : '',
      ].filter(Boolean).join(' ')}
    >
      <AuthNav />
      <main className="app-main">
        <Routes>
          {routes.map(({ path, element }) => (
            <Route
              key={path}
              path={path}
              element={
                path === '/'
                  ? <PageTransition>{element}</PageTransition>
                  : element
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
    <LiteUiProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </AuthProvider>
    </LiteUiProvider>
  );
}
