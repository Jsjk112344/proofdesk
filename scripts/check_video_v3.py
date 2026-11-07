"""Check the final public recording session's readable desktop layout."""

# ruff: noqa: E501
import asyncio
import json

from playwright.async_api import async_playwright

from scripts.record_demo_scenes import BASE, ROOT, VIDEO


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            storage_state=str(ROOT / ".local/video-prep/scene-storage.json"),
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1.5,
        )
        page = await ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(BASE + "/#/store/r02")
        await page.get_by_role("button", name="Open Maria G. details").wait_for()
        trace = page.locator(".agent-trace")
        await trace.wait_for()
        if not await trace.get_attribute("open") == "":
            await trace.locator("summary").click()
        await page.evaluate("document.fonts.ready")
        # A completed approval adds the real Ready download panel. One short
        # scroll keeps that panel, the trace and the first follow-up together.
        if await page.locator(".handoff-panel.ready").count():
            await page.evaluate(
                "window.scrollTo(0,document.querySelector('.agent-trace').getBoundingClientRect().top-65)"
            )
        layout = await page.evaluate("""() => {
            const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return {top:r.top,bottom:r.bottom,width:r.width}};
            return {trace:box('.agent-trace'),first_followup:box('.followup-card'),
              trace_font:parseFloat(getComputedStyle(document.querySelector('.agent-trace li')).fontSize),
              horizontal_overflow:document.documentElement.scrollWidth>innerWidth};
        }""")
        await page.screenshot(path=str(VIDEO / "_review/v3-after-store.png"), scale="css")
        assert layout["trace_font"] >= 15
        assert layout["first_followup"]["bottom"] <= 720, layout
        assert not layout["horizontal_overflow"]
        await page.get_by_role("button", name="Open Maria G. details").click()
        await page.get_by_role("dialog").wait_for()
        drawer = await page.evaluate("""() => {
            const selectors=['.lead-context','.lead-timeline','.candidate.chosen','.drawer-message'];
            return Object.fromEntries(selectors.map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [s,{top:r.top,bottom:r.bottom}]}));
        }""")
        assert all(r["top"] >= 0 and r["bottom"] <= 720 for r in drawer.values()), drawer
        await page.screenshot(path=str(VIDEO / "_review/v3-after-maria.png"), scale="css")
        await page.get_by_role("button", name="Show alternatives", exact=False).click()
        assert await page.locator(".candidate-list.show-alternatives .candidate").count() > 1
        await page.get_by_role("button", name="Hide alternatives", exact=False).click()
        assert not errors, errors
        (VIDEO / "v3-layout-check.json").write_text(
            json.dumps(
                {
                    "url": BASE,
                    "viewport": [1280, 720],
                    "layout": layout,
                    "drawer": drawer,
                    "page_errors": errors,
                },
                indent=2,
            )
            + "\n"
        )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
