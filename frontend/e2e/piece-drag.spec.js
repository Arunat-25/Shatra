import { test } from '@playwright/test';
import { expectPieceDragFeedback, startAiGame } from './helpers.js';
import { setLiteUi } from './boardLayoutHelpers.js';

/** Белая пешка в начальной позиции (легально выбирается для хода). */
const WHITE_PAWN = 45;

const DESKTOP_VIEWPORT = { width: 1400, height: 900 };
const MOBILE_VIEWPORT = { width: 390, height: 760 };

test.describe('piece drag feedback', () => {
  test('desktop regular board allows dragging a piece', async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setLiteUi(page, false);
    await startAiGame(page, { asWhite: true });
    await expectPieceDragFeedback(page, WHITE_PAWN, 'белый');
  });

  test('mobile regular board allows dragging a piece', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, false);
    await startAiGame(page, { asWhite: true });
    await expectPieceDragFeedback(page, WHITE_PAWN, 'белый');
  });

  test('desktop lite canvas board allows dragging a piece', async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setLiteUi(page, true);
    await startAiGame(page, { asWhite: true });
    await expectPieceDragFeedback(page, WHITE_PAWN, 'белый');
  });

  test('mobile lite canvas board allows dragging a piece', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, true);
    await startAiGame(page, { asWhite: true });
    await expectPieceDragFeedback(page, WHITE_PAWN, 'белый');
  });
});
