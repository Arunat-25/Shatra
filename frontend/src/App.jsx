import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AuthNav from './components/AuthNav';
import PageTransition from './components/PageTransition';
import Lobby from './Lobby';
import Game from './Game';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';
import Tutorial from './pages/Tutorial';
import TutorialSection1 from './pages/TutorialSection1';
import TutorialSection2 from './pages/TutorialSection2';
import TutorialSection3 from './pages/TutorialSection3';
import TutorialSection4 from './pages/TutorialSection4';
import TutorialSection5 from './pages/TutorialSection5';
import { isTutorialPath, isTutorialLessonPath } from './tutorialPaths';
import { isGamePath } from './appPaths';
const Admin = lazy(() => import('./pages/Admin'));

function AdminFallback() {
  return (
    <div className="admin-page">
      <p>…</p>
    </div>
  );
}

const routes = [
  { path: '/', element: <Lobby /> },
  { path: '/login', element: <Login /> },
  { path: '/register', element: <Register /> },
  { path: '/profile', element: <Profile /> },
  { path: '/tutorial', element: <Tutorial /> },
  { path: '/tutorial/1', element: <TutorialSection1 /> },
  { path: '/tutorial/2', element: <TutorialSection2 /> },
  { path: '/tutorial/3', element: <TutorialSection3 /> },
  { path: '/tutorial/4', element: <TutorialSection4 /> },
  { path: '/tutorial/5', element: <TutorialSection5 /> },
  {
    path: '/admin',
    element: (
      <Suspense fallback={<AdminFallback />}>
        <Admin />
      </Suspense>
    ),
  },
  { path: '/:roomId', element: <Game /> },
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
                path === '/:roomId' || path === '/admin'
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