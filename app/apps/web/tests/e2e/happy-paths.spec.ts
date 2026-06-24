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
    await expect(page.getByText('Trips on the affected road (morning rush)')).toBeVisible();
    await expect(page.getByText('People at risk of displacement')).toBeVisible();
    await expect(page.getByText('+12', { exact: true })).toBeVisible(); // SOC-2 (signed, 0 dp)

    // The full lifecycle reached DONE (ACCEPTED → … → DONE through the reducer).
    await expect(page.getByTestId('ws-status')).toContainText('Done');

    // The summary defers the deep detail to Analytics — open it.
    await page.getByRole('button', { name: /View full analytics/i }).click();

    // Analytics carries the raw metric names, the synthesis narrative, validation + bias.
    await expect(page.getByText('Displacement risk count')).toBeVisible();
    await expect(page.getByText(/Illustrative synthesis for e2e/)).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Validation & Back-Testing' })).toBeVisible();
    await expect(page.getByTestId('gate-VAL-01')).toBeVisible();
    await expect(page.getByText('Bias Audit Log (Public)')).toBeVisible();
  });

  test('H-09: clicking a summary card opens the glass-box Inspect drawer', async ({ page }) => {
    await mockMatrixBackend(page);
    await page.goto(SCENARIO);

    // Click the humanized summary card; the drawer still surfaces raw provenance.
    await page.getByText('Trips on the affected road (morning rush)').click();

    const drawer = page.getByTestId('inspect-drawer');
    await expect(drawer).toBeVisible();
    // The drawer surfaces the equation id + raw metric name (provenance, PRD-F14). exact:true
    // so the id chip "BEH-1" doesn't also match the "…BEH-1 is registered…" equation-text fallback.
    await expect(drawer.getByText('BEH-1', { exact: true })).toBeVisible();
    await expect(drawer.getByRole('heading', { name: 'Δ trips on affected corridor (AM-peak)' })).toBeVisible();
  });
});
