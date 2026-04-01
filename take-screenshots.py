"""Take screenshots of the MATPOWER Web application using Playwright."""
import asyncio
from playwright.async_api import async_playwright
import os

URL = "http://localhost:5173"
OUT = r"E:\matpower-web\docs"

async def main():
    os.makedirs(OUT, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="msedge",
            headless=True,
        )
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        print("Navigating to", URL)
        await page.goto(URL, wait_until="networkidle", timeout=60000)

        # Wait for simulation to finish and charts to render
        print("Waiting for data to load...")
        await page.wait_for_timeout(12000)  # up to 12s for Octave to finish
        await asyncio.sleep(3)

        # Check charts rendered
        charts = await page.evaluate("""document.querySelectorAll('div[_echarts_instance_]').length""")
        print(f"ECharts instances: {charts}")

        shots = {
            "dashboard": None,
            "topology": ".topology-panel",
            "voltage-chart": ".chart-item:first-child",
            "powerflow-chart": ".chart-item:last-child",
            "data-panel": ".data-panel",
            "bottom-panel": ".bottom-panel",
        }

        for name, selector in shots.items():
            path = os.path.join(OUT, f"{name}.png")
            if selector:
                el = await page.query_selector(selector)
                if el:
                    await el.screenshot(path=path)
                    print(f"  {name}.png saved ({os.path.getsize(path)} bytes)")
                else:
                    print(f"  {name}: element not found, using full page")
                    await page.screenshot(path=path)
            else:
                await page.screenshot(path=path)
                print(f"  {name}.png saved ({os.path.getsize(path)} bytes)")

        # Click alarm tab
        alarm_tab = await page.query_selector(".data-panel .ant-tabs-tab:nth-child(2)")
        if alarm_tab:
            await alarm_tab.click()
            await asyncio.sleep(0.5)
            el = await page.query_selector(".data-panel")
            if el:
                path = os.path.join(OUT, "alarm-panel.png")
                await el.screenshot(path=path)
                print(f"  alarm-panel.png saved ({os.path.getsize(path)} bytes)")

        await browser.close()
        print("\nAll screenshots saved to:", OUT)

asyncio.run(main())
