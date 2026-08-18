import { test, expect } from "@playwright/test";

test("/app paints a MapLibre basemap on the cockpit stage", async ({ page }) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/app", { waitUntil: "domcontentloaded" });
  await page.getByRole("navigation", { name: "Main navigation" }).waitFor({ state: "visible" });

  const canvas = page.locator("#basemap-stage .maplibregl-canvas");
  await expect(
    canvas,
    [
      "basemap must be a MapLibre map filling the stage, not an empty DeckGL view overlay",
      `pageErrors: ${pageErrors.join(" | ") || "(none)"}`,
      `consoleErrors: ${consoleErrors.join(" | ") || "(none)"}`,
    ].join("\n"),
  ).toBeVisible({ timeout: 20_000 });

  const box = await canvas.boundingBox();
  expect(box, "basemap canvas has a non-zero box").toBeTruthy();
  expect(box!.width).toBeGreaterThan(100);
  expect(box!.height).toBeGreaterThan(100);

  await page.waitForResponse(
    (res) => res.url().includes("tiles.openfreemap.org/planet/") && res.ok(),
    { timeout: 20_000 },
  );
});
