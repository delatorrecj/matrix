// Best-effort capture of REAL app screenshots for the deck's Proof slide.
// Requires the web app running locally (see presentation/README.md):
//   cd app && docker compose up -d
//   cd app/apps/api && uvicorn matrix_api.main:app --reload
//   cd app/apps/web && npm install && npm run dev      # http://localhost:3000
// Then:  node presentation/scripts/capture-shots.mjs
//
// Writes into presentation/assets/. The deck swaps these in automatically if present;
// if absent, the deck shows a labeled placeholder (nothing breaks).
//
// Selectors/routes are best-effort — adjust BASE / the scenario flow to match the live app.

import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const assets = resolve(__dirname, '..', 'assets');
const BASE = process.env.MATRIX_WEB_URL || 'http://localhost:3000';

let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error('Playwright not found. cd app/apps/web && npx playwright install chromium, then re-run.');
  process.exit(1);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

  // 1) landing / scenario entry
  try {
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 15000 });
    await page.screenshot({ path: resolve(assets, 'home.png') });
    console.log('captured home.png');
  } catch (e) { console.warn('home capture skipped:', e.message); }

  // 2) a running scenario (Deck.gl playback) — adjust the path/flow to your app
  try {
    await page.goto(BASE + '/scenario/demo', { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(6000); // let playback animate / results stream in
    await page.screenshot({ path: resolve(assets, 'scenario-playback.png') });
    console.log('captured scenario-playback.png');
  } catch (e) { console.warn('scenario capture skipped:', e.message); }

  // 3) the glass-box Inspect drawer (open it if a trigger exists)
  try {
    const trigger = page.locator('[data-inspect], button:has-text("Inspect")').first();
    if (await trigger.count()) {
      await trigger.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: resolve(assets, 'inspect-drawer.png') });
      console.log('captured inspect-drawer.png');
    }
  } catch (e) { console.warn('inspect capture skipped:', e.message); }

  console.log('\nDone. Files in', assets);
} finally {
  await browser.close();
}
