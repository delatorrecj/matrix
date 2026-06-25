import { test, expect } from '@playwright/test';
import { mockMatrixBackend } from './_mock-backend';

const SCENARIO = '/scenario/ref-1-school-molo';

test.describe('MATRIX scenario page (mocked backend)', () => {
  test('H-01/H-08: summary humanizes results; analytics holds the full detail', async ({ page }) => {
    await mockMatrixBackend(page);
    await page.goto(SCENARIO);

    // Default view is the plain-language summary dock (CR-010).
    await expect(page.getByRole('heading', { name: 'Scenario summary' })).toBeVisible();

    // Streamed results render with HUMAN labels + rounded values (registry, not raw floats).
    // Target the summary cards (buttons) — the hidden print brief mirrors the same label
    // text, so a bare getByText is ambiguous under Playwright strict mode.
    await expect(page.getByRole('button', { name: /Trips on the affected road/ })).toBeVisible();
    const displacementCard = page.getByRole('button', { name: /People at risk of displacement/ });
    await expect(displacementCard).toBeVisible();
    await expect(displacementCard).toContainText('+12'); // SOC-2 (signed, 0 dp)

    // The full lifecycle reached DONE (ACCEPTED → … → DONE through the reducer).
    await expect(page.getByTestId('ws-status')).toContainText('Done');

    // The summary defers the deep detail to Analytics — open it.
    await page.getByRole('button', { name: /View full analytics/i }).click();

    // Analytics carries the raw metric names + the synthesis narrative. Scope to the
    // analytics view — the hidden print brief mirrors the same label/headline text in the DOM.
    const analytics = page.getByTestId('analytics-view');
    await expect(analytics.getByText('Displacement risk count')).toBeVisible();
    // CR-010: the synthesis narrative is the plain-language BLUF brief; the English half
    // shows by default (the Hiligaynon half sits behind the delimiter + language toggle).
    await expect(analytics.getByText(/Closing the lane eases the morning rush/)).toBeVisible();
    await expect(page.getByText(/nagapahapos sang trapiko/)).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Validation & Back-Testing' })).toBeVisible();
    await expect(page.getByTestId('gate-VAL-01')).toBeVisible();
    await expect(page.getByText('Bias Audit Log (Public)')).toBeVisible();
  });

  test('H-09: clicking a summary card opens the glass-box Inspect drawer', async ({ page }) => {
    await mockMatrixBackend(page);
    await page.goto(SCENARIO);

    // Click the humanized summary card (button, not the hidden print brief's mirror text).
    await page.getByRole('button', { name: /Trips on the affected road/ }).click();

    const drawer = page.getByTestId('inspect-drawer');
    await expect(drawer).toBeVisible();
    // The drawer surfaces the equation id + raw metric name (provenance, PRD-F14). exact:true
    // so the id chip "BEH-1" doesn't also match the "…BEH-1 is registered…" equation-text fallback.
    await expect(drawer.getByText('BEH-1', { exact: true })).toBeVisible();
    await expect(drawer.getByRole('heading', { name: 'Δ trips on affected corridor (AM-peak)' })).toBeVisible();

    await drawer.getByRole('button', { name: /Show details/i }).click();
    await expect(drawer.getByText(/ΔT_c = Σ_a/)).toBeVisible();
    await expect(drawer.getByRole('link', { name: /overpass-api/i })).toBeVisible();
  });

  test('H-10: map context menu appears only over the map canvas', async ({ page }) => {
    await mockMatrixBackend(page);
    await page.goto(SCENARIO);

    const mapStage = page.locator('.maplibregl-canvas').first();
    await mapStage.click({ button: 'right', position: { x: 120, y: 120 } });
    await expect(page.getByTestId('map-context-menu')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByTestId('map-context-menu')).toHaveCount(0);

    await page.getByRole('heading', { name: 'Scenario summary' }).click({ button: 'right' });
    await expect(page.getByTestId('map-context-menu')).toHaveCount(0);
  });
});
