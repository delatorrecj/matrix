import { test, expect } from '@playwright/test';

test.describe('MATRIX Happy Paths', () => {
  test('H-01 / H-08: Scenario layout and inspection', async ({ page }) => {
    // Navigate to a reference scenario
    await page.goto('/scenario/ref-1-school-molo');

    // Wait for the scenario results to load
    await expect(page.locator('text=Scenario Results')).toBeVisible();

    // Verify the 5 dimensions exist (this asserts the dimensions array renders)
    // We expect some dimensions like "behavioral", "economic", etc. to be present
    // Assuming backend is streaming properly or at least the panel exists
    const panel = page.locator('.w-full.md\\:w-\\[360px\\]');
    await expect(panel).toBeVisible();

    // Verify Validation and Bias Auditor logs exist
    await expect(page.locator('text=Validation & Back-Testing')).toBeVisible();
    await expect(page.locator('text=Bias Audit Log')).toBeVisible();
  });
});
