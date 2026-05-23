import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PageTransition from './components/PageTransition';
import Lobby from './Lobby';
import Game from './Game';

const routes = [
  { path: '/', element: <Lobby /> },
  { path: '/:roomId', element: <Game /> },
];

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {routes.map(({ path, element }) => (
          <Route
            key={path}
            path={path}
            element={<PageTransition>{element}</PageTransition>}
          />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}