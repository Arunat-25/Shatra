import { useState } from 'react';
import { TIMER_PRESETS, INCREMENT_PRESETS } from '../constants';

/**
 * Двухшаговый выбор таймера: сначала базовое время, потом инкремент.
 * @param {{
 *   onFinish: (timeValue: number|null, incrementValue: number) => void,
 *   onCancel: () => void
 * }} props
 */
export default function TimerPicker({ onFinish, onCancel }) {
  const [step, setStep] = useState('timer'); // 'timer' | 'increment'
  const [selectedTime, setSelectedTime] = useState(null);

  const handleTimerSelect = (timeValue) => {
    setSelectedTime(timeValue);
    if (timeValue === null) {
      onFinish(timeValue, 0);
    } else {
      setStep('increment');
    }
  };

  const handleIncrementSelect = (incValue) => {
    onFinish(selectedTime, incValue);
  };

  if (step === 'increment') {
    return (
      <div className="timer-picker">
        <h3 className="timer-picker-title">Добавка за ход</h3>
        <div className="timer-presets">
          {INCREMENT_PRESETS.map((preset) => (
            <button
              key={preset.value}
              className="btn-timer-preset"
              onClick={() => handleIncrementSelect(preset.value)}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <button className="btn-timer-cancel" onClick={() => setStep('timer')}>
          Назад
        </button>
      </div>
    );
  }

  return (
    <div className="timer-picker">
      <h3 className="timer-picker-title">Выберите таймер</h3>
      <div className="timer-presets">
        {TIMER_PRESETS.map((preset) => (
          <button
            key={preset.value}
            className="btn-timer-preset"
            onClick={() => handleTimerSelect(preset.value)}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <button
        className="btn-timer-preset btn-timer-none"
        onClick={() => handleTimerSelect(null)}
      >
        Без таймера
      </button>
      <button className="btn-timer-cancel" onClick={onCancel}>
        Отмена
      </button>
    </div>
  );
}