import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using a standard desktop resolution
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("Navigating to Landing Page...")
        await page.goto("http://matrix-atlan.vercel.app/")
        # Wait for the hero image and animations to settle
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="docs/images/landing_page.png")
        print("Saved docs/images/landing_page.png")

        print("Navigating to App Dashboard...")
        await page.goto("http://matrix-atlan.vercel.app/app")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000) # Wait for map to load

        print("Triggering sample simulation...")
        # Type in the textarea
        await page.fill("textarea#scenario-query", "What if we build a 3,000-seat school in Molo?")
        # Click the Simulate Scenario button
        await page.click("button:has-text('Simulate Scenario')")
        
        # It may navigate to /scenario/[id] or show sample results
        print("Waiting for results to load...")
        await page.wait_for_timeout(8000) # Wait for API or sample mode
        
        await page.screenshot(path="docs/images/dashboard.png")
        print("Saved docs/images/dashboard.png")

        print("Opening Inspect Drawer...")
        try:
            # Click the Behavioral card to open the drawer
            # The dimension cards render text like "Behavioral (sample)" or "Behavioral"
            await page.click("text=Behavioral", timeout=5000)
            await page.wait_for_timeout(2000) # Wait for drawer animation
            await page.screenshot(path="docs/images/inspect_drawer.png")
            print("Saved docs/images/inspect_drawer.png")
        except Exception as e:
            print(f"Could not open inspect drawer: {e}")
            
            # fallback: screenshot as is if it fails
            await page.screenshot(path="docs/images/inspect_drawer.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
