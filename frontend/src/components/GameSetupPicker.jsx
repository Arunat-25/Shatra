import { useState } from 'react';
import { useTranslation } from 'react-i18next';
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

const TIMER_LABEL_KEYS = {
  15: 'setup.preset15s',
  30: 'setup.preset30s',
  60: 'setup.preset1m',
  180: 'setup.preset3m',
  300: 'setup.preset5m',
  600: 'setup.preset10m',
  900: 'setup.preset15m',
  1800: 'setup.preset30m',
};

const INC_LABEL_KEYS = {
  0: 'setup.inc0',
  1: 'setup.inc1',
  2: 'setup.inc2',
  3: 'setup.inc3',
  5: 'setup.inc5',
  10: 'setup.inc10',
  15: 'setup.inc15',
  30: 'setup.inc30',
};

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

export default function GameSetupPicker({ onFinish, onCancel, aiOnly = false }) {
  const { t } = useTranslation();
  const [colorPref, setColorPref] = useState(COLOR_PREF_RANDOM);
  const [timeValue, setTimeValue] = useState(null);
  const [increment, setIncrement] = useState(0);

  const colorOptions = [
    { value: COLOR_PREF_WHITE, label: t('setup.colorWhite'), color: COLOR_WHITE },
    { value: COLOR_PREF_RANDOM, label: t('setup.colorRandom'), random: true },
    { value: COLOR_PREF_BLACK, label: t('setup.colorBlack'), color: COLOR_BLACK },
  ];

  const hasTimer = timeValue !== null;

  const handleCreate = () => {
    onFinish(timeValue, hasTimer ? increment : 0, colorPref);
  };

  return (
    <div className="timer-picker game-setup-picker">
      <h3 className="timer-picker-title">{t('setup.title')}</h3>

      <section className="game-setup-section" aria-labelledby="setup-color-label">
        <p id="setup-color-label" className="game-setup-label">{t('setup.colorLabel')}</p>
        <div className="color-picker-options">
          {colorOptions.map((opt) => (
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
            <p id="setup-timer-label" className="game-setup-label">{t('setup.timerLabel')}</p>
            <div className="timer-presets">
              {TIMER_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  className={`btn-timer-preset${timeValue === preset.value ? ' active' : ''}`}
                  onClick={() => setTimeValue(preset.value)}
                  aria-pressed={timeValue === preset.value}
                >
                  {t(TIMER_LABEL_KEYS[preset.value])}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={`btn-timer-preset btn-timer-none${timeValue === null ? ' active' : ''}`}
              onClick={() => setTimeValue(null)}
              aria-pressed={timeValue === null}
            >
              {t('setup.noTimer')}
            </button>
          </section>

          <section
            className={`game-setup-section${hasTimer ? '' : ' game-setup-section--disabled'}`}
            aria-labelledby="setup-inc-label"
            aria-disabled={!hasTimer}
          >
            <p id="setup-inc-label" className="game-setup-label">{t('setup.incrementLabel')}</p>
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
                  {t(INC_LABEL_KEYS[preset.value])}
                </button>
              ))}
            </div>
          </section>
        </>
      )}

      <button type="button" className="btn-setup-create" onClick={handleCreate}>
        {aiOnly ? t('setup.play') : t('setup.createGame')}
      </button>
      <button type="button" className="btn-timer-cancel" onClick={onCancel}>
        {t('setup.cancel')}
      </button>
    </div>
  );
}
