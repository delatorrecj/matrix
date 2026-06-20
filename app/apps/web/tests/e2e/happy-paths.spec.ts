import { test, expect } from '@playwright/test';
import { mockMatrixBackend } from './_mock-backend';

const SCENARIO = '/scenario/ref-1-school-molo';

test.describe('MATRIX scenario page (mocked backend)', () => {
  test('H-01/H-08: streams dimension results, synthesis, validation + bias log', async ({ page }) => {
    await mockMatrixBackend(page);
    await page.goto(SCENARIO);

    // Static shell renders.
    await expect(page.getByRole('heading', { name: 'Scenario Results' })).toBeVisible();

    // Streamed DIMENSION_RESULTs drove the reducer + glass-box cards.
    await expect(page.getByText('Mode shift to transit')).toBeVisible();
    await expect(page.getByText('+12.5')).toBeVisible();
    await expect(page.getByText('Displacement risk count')).toBeVisible();

    // The full lifecycle reached DONE (ACCEPTED → … → DONE through the reducer).
    await expect(page.getByTestId('ws-status')).toContainText('Done');

    // SYNTHESIS narrative rendered.
    await expect(page.getByText(/Illustrative synthesis for e2e/)).toBeVisible();

    // Validation panel: heading is static; the gate card proves GET /validation loaded.
    await expect(page.getByRole('heading', { name: 'Validation & Back-Testing' })).toBeVisible();
    await expect(page.getByTestId('gate-VAL-01')).toBeVisible();

    // Bias audit log: the "(Public)" heading only renders in the LOADED state, so this
    // proves GET /audit returned — distinct from the "Loading…" fallback.
    await expect(page.getByText('Bias Audit Log (Public)')).toBeVisible();
  });

  test('H-09: clicking a result card opens the glass-box Inspect drawer', async ({ page }) => {
    await mockMatrixBackend(page);
    await page.goto(SCENARIO);

    await page.getByText('Mode shift to transit').click();

    const drawer = page.getByTestId('inspect-drawer');
    await expect(drawer).toBeVisible();
    // The drawer surfaces the equation id + metric (provenance, PRD-F14). exact:true so the
    // id chip "BEH-1" doesn't also match the "…BEH-1 is registered…" equation-text fallback.
    await expect(drawer.getByText('BEH-1', { exact: true })).toBeVisible();
    await expect(drawer.getByRole('heading', { name: 'Mode shift to transit' })).toBeVisible();
  });
});
