import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PageTransition from './components/PageTransition';
import Lobby from './Lobby';
import Game from './Game';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <PageTransition>
              <Lobby />
            </PageTransition>
          }
        />
        <Route
          path="/game"
          element={
            <PageTransition>
              <Game />
            </PageTransition>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}