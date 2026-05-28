import { useState } from 'react';
import ShatraPiece from '../ShatraPiece';
import {
  COLOR_WHITE,
  COLOR_BLACK,
  PIECE_BIY,
  COLOR_PREF_WHITE,
  COLOR_PREF_BLACK,
  COLOR_PREF_RANDOM,
  TIMER_PRESETS,
  INCREMENT_PRESETS,
} from '../constants';

const COLOR_OPTIONS = [
  { value: COLOR_PREF_WHITE, label: 'Белые', color: COLOR_WHITE },
  { value: COLOR_PREF_RANDOM, label: 'Случайно', random: true },
  { value: COLOR_PREF_BLACK, label: 'Чёрные', color: COLOR_BLACK },
];

function RandomBiyIcon() {
  return (
    <span className="color-pick-random-icon" aria-hidden>
      <span className="color-pick-random-half color-pick-random-half--white">
        <ShatraPiece type={PIECE_BIY} color={COLOR_WHITE} positionNum="rand-w" />
      </span>
      <span className="color-pick-random-half color-pick-random-half--black">
        <ShatraPiece type={PIECE_BIY} color={COLOR_BLACK} positionNum="rand-b" />
      </span>
    </span>
  );
}

/**
 * Единое окно: цвет, таймер и добавка за ход.
 * @param {{
 *   onFinish: (timeValue: number|null, incrementValue: number, colorPreference: string) => void,
 *   onCancel: () => void,
 *   aiOnly?: boolean
 * }} props
 */
export default function GameSetupPicker({ onFinish, onCancel, aiOnly = false }) {
  const [colorPref, setColorPref] = useState(COLOR_PREF_RANDOM);
  const [timeValue, setTimeValue] = useState(null);
  const [increment, setIncrement] = useState(0);

  const hasTimer = timeValue !== null;

  const handleCreate = () => {
    onFinish(timeValue, hasTimer ? increment : 0, colorPref);
  };

  return (
    <div className="timer-picker game-setup-picker">
      <h3 className="timer-picker-title">Настройки игры</h3>

      <section className="game-setup-section" aria-labelledby="setup-color-label">
        <p id="setup-color-label" className="game-setup-label">Цвет фигур</p>
        <div className="color-picker-options">
          {COLOR_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`btn-color-pick${colorPref === opt.value ? ' active' : ''}`}
              onClick={() => setColorPref(opt.value)}
              aria-label={opt.label}
              aria-pressed={colorPref === opt.value}
            >
              <span className="btn-color-pick__icon">
                {opt.random ? (
                  <RandomBiyIcon />
                ) : (
                  <ShatraPiece type={PIECE_BIY} color={opt.color} positionNum={opt.value} />
                )}
              </span>
              <span className="btn-color-pick__label">{opt.label}</span>
            </button>
          ))}
        </div>
      </section>

      {!aiOnly && (
        <>
          <section className="game-setup-section" aria-labelledby="setup-timer-label">
            <p id="setup-timer-label" className="game-setup-label">Таймер</p>
            <div className="timer-presets">
              {TIMER_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  className={`btn-timer-preset${timeValue === preset.value ? ' active' : ''}`}
                  onClick={() => setTimeValue(preset.value)}
                  aria-pressed={timeValue === preset.value}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={`btn-timer-preset btn-timer-none${timeValue === null ? ' active' : ''}`}
              onClick={() => setTimeValue(null)}
              aria-pressed={timeValue === null}
            >
              Без таймера
            </button>
          </section>

          <section
            className={`game-setup-section${hasTimer ? '' : ' game-setup-section--disabled'}`}
            aria-labelledby="setup-inc-label"
            aria-disabled={!hasTimer}
          >
            <p id="setup-inc-label" className="game-setup-label">Добавка за ход</p>
            <div className="timer-presets">
              {INCREMENT_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  className={`btn-timer-preset${hasTimer && increment === preset.value ? ' active' : ''}`}
                  onClick={() => setIncrement(preset.value)}
                  disabled={!hasTimer}
                  aria-pressed={hasTimer && increment === preset.value}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </section>
        </>
      )}

      <button type="button" className="btn-setup-create" onClick={handleCreate}>
        {aiOnly ? 'Играть' : 'Создать игру'}
      </button>
      <button type="button" className="btn-timer-cancel" onClick={onCancel}>
        Отмена
      </button>
    </div>
  );
}
