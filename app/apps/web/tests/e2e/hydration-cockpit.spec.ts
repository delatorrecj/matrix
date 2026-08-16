import { test, expect } from "@playwright/test";

test("/app does not show a Next.js hydration overlay", async ({ page }) => {
  const hydration: string[] = [];
  page.on("pageerror", (err) => {
    if (/hydrat/i.test(err.message)) hydration.push(err.message);
  });
  page.on("console", (msg) => {
    const t = msg.text();
    if (/hydrat/i.test(t)) hydration.push(t);
  });

  await page.goto("/app", { waitUntil: "networkidle" });
  await page.getByRole("navigation", { name: "Main navigation" }).waitFor({ state: "visible" });
  await page.waitForTimeout(1500);

  const overlay = page.getByText(/Hydration failed/i);
  const overlayVisible = await overlay.isVisible().catch(() => false);

  expect(
    { overlayVisible, hydration },
    overlayVisible ? "hydration overlay visible" : hydration.join("\n"),
  ).toEqual({ overlayVisible: false, hydration: [] });
});
