// Export the MATRIX deck to a one-slide-per-page PDF using Playwright (headless Chromium).
//
// Run from anywhere Playwright's Chromium is installed. The web app (app/apps/web) already
// depends on Playwright, so the simplest path is:
//   node presentation/scripts/export-pdf.mjs
// If "Cannot find package 'playwright'": cd app/apps/web && npx playwright install chromium,
// then re-run, or:  node --experimental-vm-modules ... (not needed) — just ensure playwright resolves.
//
// Output: presentation/matrix-pitch.pdf
//
// The deck's print stylesheet (@media print + @page size:1280x720) makes Chromium render every
// <section class="slide"> as its own 16:9 page. We force print media + CSS page size below.

import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, resolve } from 'node:path';
import { existsSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const deckPath = resolve(__dirname, '..', 'deck', 'index.html');
const outPath = resolve(__dirname, '..', 'matrix-pitch.pdf');

if (!existsSync(deckPath)) {
  console.error('Deck not found at', deckPath);
  process.exit(1);
}

let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch (err) {
  console.error('\nCould not load Playwright. Install it first, e.g.:');
  console.error('  cd app/apps/web && npm install && npx playwright install chromium');
  console.error('then re-run this script.\n');
  process.exit(1);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(deckPath).href, { waitUntil: 'networkidle' });
  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: outPath,
    printBackground: true,
    preferCSSPageSize: true,
    // fallback size if the CSS @page size isn't honored (16:9 @ 96dpi ≈ 13.333in x 7.5in)
    width: '1280px',
    height: '720px',
    margin: { top: '0', right: '0', bottom: '0', left: '0' },
  });
  console.log('Wrote', outPath);
} finally {
  await browser.close();
}
