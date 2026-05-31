import { useEffect } from 'react';
import { resumeAudioContext, preloadGameSounds } from '../audio/gameSounds';

/** Resume AudioContext and preload samples on first user gesture. */
export default function useGameAudioUnlock() {
  useEffect(() => {
    const unlock = () => {
      void resumeAudioContext().then(() => preloadGameSounds());
    };
    document.addEventListener('pointerdown', unlock, { once: true });
    document.addEventListener('keydown', unlock, { once: true });
    return () => {
      document.removeEventListener('pointerdown', unlock);
      document.removeEventListener('keydown', unlock);
    };
  }, []);
}
