import React from 'react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import GameSetupPicker from './GameSetupPicker';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => ({
      'setup.title': 'Настройка',
      'setup.colorLabel': 'Цвет',
      'setup.colorWhite': 'Белые',
      'setup.colorBlack': 'Чёрные',
      'setup.colorRandom': 'Случайно',
      'setup.timerLabel': 'Время',
      'setup.noTimer': 'Без таймера',
      'setup.preset5m': '5 мин',
      'setup.incrementLabel': 'Добавка',
      'setup.inc0': '0',
      'setup.ratedGame': 'Игра на рейтинг',
      'setup.ratedGameHint': 'Рейтинг изменится',
      'setup.createGame': 'Создать',
      'setup.play': 'Играть',
      'setup.cancel': 'Отмена',
    }[key] ?? key),
  }),
}));

vi.mock('../ShatraPiece', () => ({
  default: () => <span data-testid="piece" />,
}));

describe('GameSetupPicker rated toggle', () => {
  afterEach(() => {
    cleanup();
  });

  it('shows rated checkbox only in private mode', () => {
    const { rerender } = render(
      <GameSetupPicker onFinish={vi.fn()} onCancel={vi.fn()} privateMode={false} />,
    );
    expect(screen.queryByRole('checkbox', { name: /игра на рейтинг/i })).toBeNull();

    rerender(
      <GameSetupPicker onFinish={vi.fn()} onCancel={vi.fn()} privateMode />,
    );
    expect(screen.getByRole('checkbox', { name: /игра на рейтинг/i })).toBeTruthy();
  });

  it('passes rated=true to onFinish when checkbox checked', () => {
    const onFinish = vi.fn();
    render(
      <GameSetupPicker onFinish={onFinish} onCancel={vi.fn()} privateMode />,
    );
    fireEvent.click(screen.getByRole('checkbox', { name: /игра на рейтинг/i }));
    fireEvent.click(screen.getByRole('button', { name: /создать/i }));
    expect(onFinish).toHaveBeenCalledWith(null, 0, 'random', true);
  });

  it('passes rated=false for public mode even if internal state toggled', () => {
    const onFinish = vi.fn();
    render(
      <GameSetupPicker onFinish={onFinish} onCancel={vi.fn()} privateMode={false} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /создать/i }));
    expect(onFinish).toHaveBeenCalledWith(null, 0, 'random', false);
  });
});
