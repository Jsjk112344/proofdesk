"""Record real public SalesDesk scenes, 2x stills and 30fps H.264 backup takes.

Run: uv run python -m scripts.record_demo_scenes
No mocked requests, counters, state, metrics, text or replay disclosures. The only
injected DOM is a pointer and click ring. A single fresh anonymous context owns the
whole journey. Closing a recorded page never stops server-side work.
"""

# ruff: noqa: E501

import argparse
import asyncio
import csv
import io
import json
import subprocess
import time
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "docs/video"
BASE = "https://salesdesk.149.28.51.139.sslip.io"
CURSOR = """(() => {
 const add=()=>{
  const pointer=document.createElement('div');pointer.id='recording-pointer';
  pointer.style.cssText='position:fixed;left:40px;top:800px;width:24px;height:30px;pointer-events:none;z-index:2147483647;filter:drop-shadow(0 2px 2px #0008)';
  pointer.innerHTML='<svg width="24" height="30" viewBox="0 0 24 30"><path d="M2 1L2 25L8 19L13 29L18 26L13 17L23 17Z" fill="white" stroke="#142e34" stroke-width="1.5"/></svg>';
  document.documentElement.append(pointer);
  document.addEventListener('mousemove',e=>{pointer.style.left=e.clientX+'px';pointer.style.top=e.clientY+'px'});
  document.addEventListener('mousedown',()=>{pointer.style.transform='scale(.86)'});
  document.addEventListener('mouseup',()=>{pointer.style.transform='scale(1)'});
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add);else add();
})()"""


def transcode(source, target, offset, duration):
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            str(max(0, offset)),
            "-i",
            str(source),
            "-vf",
            "fps=30,tpad=stop_mode=clone:stop_duration=30",
            "-t",
            str(duration),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ],
        check=True,
    )


class Recorder:
    def __init__(self, ctx, base):
        self.ctx, self.base = ctx, base
        self.manifest = {
            "base_url": base,
            "viewport": [1440, 900],
            "device_scale_factor": 2,
            "video_resolution": [1440, 900],
            "scenes": [],
            "beats": [],
        }
        self.errors = []
        self.position = [40, 800]

    async def open(self, name, route, ready):
        self.origin = time.monotonic()
        self.page = await self.ctx.new_page()
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.set_default_timeout(60000)
        await self.page.goto(self.base + "/" + route)
        await ready(self.page)
        await self.page.locator(".sample-badge").first.wait_for()
        await self.page.evaluate("document.fonts.ready")
        await self.page.locator("#recording-pointer").wait_for()
        self.name = name
        self.started = time.monotonic()
        self.offset = self.started - self.origin
        await self.page.mouse.move(*self.position)
        await self.beat("start")

    async def at(self, second):
        await asyncio.sleep(max(0, self.started + second - time.monotonic()))

    async def point(self, locator, click=False):
        await locator.wait_for(state="visible")
        await locator.scroll_into_view_if_needed()
        box = await locator.bounding_box()
        assert box
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        sx, sy = self.position
        for i in range(1, 31):
            q = 1 - (1 - i / 30) ** 3
            await self.page.mouse.move(sx + (x - sx) * q, sy + (y - sy) * q)
            await asyncio.sleep(0.016)
        self.position = [x, y]
        if click:
            await self.page.mouse.down()
            await asyncio.sleep(0.08)
            await self.page.mouse.up()

    async def beat(self, name):
        path = VIDEO / "stills" / f"{self.name}-{name}.png"
        await self.page.screenshot(path=str(path))
        self.manifest["beats"].append(
            {
                "scene": self.name,
                "beat": name,
                "seconds": round(time.monotonic() - self.started, 3),
                "screenshot": str(path.relative_to(ROOT)),
            }
        )

    async def finish(self, duration):
        await self.at(duration)
        video = self.page.video
        elapsed = time.monotonic() - self.started
        await self.page.close()
        raw = await video.path()
        target = VIDEO / "scenes" / (self.name + ".mp4")
        await asyncio.to_thread(transcode, raw, target, self.offset, duration)
        self.manifest["scenes"].append(
            {
                "scene": self.name,
                "file": str(target.relative_to(ROOT)),
                "seconds": duration,
                "captured_seconds": round(elapsed, 3),
                "trim_start_seconds": round(self.offset, 3),
                "raw": str(Path(raw).relative_to(ROOT)),
            }
        )
        self.save()
        await self.ctx.storage_state(path=str(ROOT / ".local/video-prep/scene-storage.json"))
        print(
            json.dumps({"scene": self.name, "seconds": duration, "page_errors": self.errors}),
            flush=True,
        )

    def save(self):
        (VIDEO / "scene-manifest.json").write_text(json.dumps(self.manifest, indent=2) + "\n")


async def group_ready(page):
    await page.get_by_role("heading", name="Good morning.", exact=False).wait_for()
    await page.locator(".rooftop-tile.ready").first.wait_for()


async def store_ready(page):
    await page.get_by_role("button", name="Open Maria G. details").wait_for()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=BASE)
    args = parser.parse_args()
    if not args.base_url.startswith("https://"):
        raise SystemExit("Product footage requires a deployed public HTTPS URL.")
    for folder in ("scenes", "stills"):
        (VIDEO / folder).mkdir(parents=True, exist_ok=True)
    raw_dir = ROOT / ".local/video-prep/raw-scenes"
    raw_dir.mkdir(parents=True, exist_ok=True)
    expected = json.loads((VIDEO / "measured-run.json").read_text())["totals"]
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            record_video_dir=str(raw_dir),
            record_video_size={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        await ctx.add_init_script(CURSOR)
        r = Recorder(ctx, args.base_url)
        await r.open("scene1", "#/", group_ready)
        assert await r.page.get_by_role("button", name="Run tonight’s review now").is_visible()
        initial = await (await ctx.request.get(args.base_url + "/api/dealer")).json()
        assert initial["saved_sample_review"] and initial["review"] is None
        assert initial["rollup"]["totals"] == expected
        assert len(set(roof["result"]["metrics"]["at_risk"] for roof in initial["rooftops"])) > 10
        assert "1007" in " ".join(initial["rollup"]["brief"]["rendered"]["findings"])
        await r.at(8)
        await r.beat("idle-group")
        await r.finish(14)

        await r.open("scene3", "#/", group_ready)
        await r.at(1)
        await r.point(r.page.get_by_role("button", name="Run tonight’s review now"))
        await r.at(2)
        clicked = time.monotonic()
        await r.page.mouse.click(*r.position)
        await r.page.get_by_role("heading", name="Every rooftop. Working together.").wait_for()
        await r.beat("real-reset")
        state = await (await ctx.request.get(args.base_url + "/api/dealer")).json()
        assert not state["saved_sample_review"]
        assert state["rollup"]["totals"]["open_leads"] < expected["open_leads"]
        await r.at(6)
        await r.point(r.page.locator(".d-live-progress"))
        await r.beat("counters")
        await r.at(10)
        # Smooth browser scroll, with the real sticky sample label retained.
        await r.page.evaluate('window.scrollTo({top:440,behavior:"smooth"})')
        await r.page.wait_for_function("() => window.scrollY > 400")
        await r.at(14)
        await r.point(r.page.locator(".rooftop-tile").nth(5))
        await r.beat("six-tiles")
        await r.at(19)
        await r.beat("real-progress")
        await r.finish(22)
        while time.monotonic() - clicked < 420:
            state = await (await ctx.request.get(args.base_url + "/api/dealer")).json()
            if state["review"]["status"] in ("failed", "succeeded"):
                break
            await asyncio.sleep(1)
        terminal_seconds = time.monotonic() - clicked
        assert state["review"]["status"] == "succeeded", state["review"]
        assert not state["rollup"]["failures"], state["rollup"]["failures"]
        assert state["rollup"]["totals"] == expected
        r.manifest["recorded_run"] = {
            "terminal_observed_seconds": round(terminal_seconds, 3),
            "review_id": state["review"]["id"],
            "totals": state["rollup"]["totals"],
            "brief_provenance": {
                roof["id"]: roof["result"]["brief"]["provenance"] for roof in state["rooftops"]
            },
            "group_brief": state["rollup"]["brief"]["rendered"],
        }
        await r.open("scene4", "#/", group_ready)
        r.manifest["recorded_run"]["visible_group_seconds"] = round(time.monotonic() - clicked, 3)
        await r.beat("stat-0")
        for second, idx in [(0, 1), (3, 2), (5, 3), (9, 4)]:
            await r.at(second)
            await r.point(r.page.locator(".d-stat-strip .d-stat").nth(idx))
            await r.beat(f"stat-{idx}")
        await r.at(15)
        await r.point(r.page.locator(".analyst-panel .d-analyst"))
        await r.beat("group-brief")
        await r.at(18)
        await r.point(r.page.locator('.rooftop-tile[href="#/store/r02"]'))
        await r.beat("sandy-tile")
        await r.finish(20)

        await r.open("scene5", "#/", group_ready)
        await r.point(r.page.locator('.rooftop-tile[href="#/store/r02"]'), click=True)
        await store_ready(r.page)
        await r.beat("sandy-queue")
        await r.finish(8)

        await r.open("scene6", "#/store/r02", store_ready)
        await r.point(r.page.get_by_role("button", name="Open Maria G. details"), click=True)
        dialog = r.page.get_by_role("dialog", name="Maria G. lead detail")
        await dialog.wait_for()
        assert await dialog.get_by_text("Sample dealer group", exact=True).is_visible()
        await r.point(dialog.locator(".lead-context"))
        await r.beat("wanted-trade")
        await r.at(5)
        await r.point(dialog.locator(".lead-timeline .sold"))
        await r.beat("sold-six-days")
        await r.at(14)
        await r.point(dialog.locator(".candidate.chosen"))
        await r.beat("best-match")
        await r.at(16)
        details = dialog.locator(".candidate.chosen details")
        # The UI opens this disclosure by default; preserve it rather than closing it.
        if await details.get_attribute("open") is None:
            await r.point(details.locator("summary"), click=True)
        else:
            await r.point(details.locator("summary"))
        await r.beat("match-breakdown")
        await r.at(25)
        await r.point(dialog.locator(".lead-context span"))
        await r.beat("crv-trade")
        await r.at(30)
        await r.point(dialog.locator(".drawer-message"))
        await r.beat("sms")
        await r.at(34)
        await r.point(dialog.get_by_role("tab", name="Email", exact=True), click=True)
        await r.beat("email")
        await r.at(36)
        await r.point(dialog.get_by_role("tab", name="SMS", exact=True), click=True)
        await r.beat("sms-return")
        await r.finish(38)

        await r.open("scene7", "#/store/r02", store_ready)
        await r.at(2)
        await r.point(
            r.page.get_by_role("button", name="Approve all for Sandy", exact=True), click=True
        )
        link = r.page.get_by_role("link", name="CRM tasks", exact=True)
        await link.wait_for(timeout=60000)
        await r.beat("ready")
        href = await link.get_attribute("href")
        data = await ctx.request.get(args.base_url + href)
        assert data.status == 200
        csv_bytes = await data.body()
        parsed = list(csv.DictReader(io.StringIO(csv_bytes.decode())))
        assert len(parsed) == 40 and "Maria" in csv_bytes.decode()
        (VIDEO / "scenes/crm-tasks.csv").write_bytes(csv_bytes)
        await r.at(13)
        async with r.page.expect_download() as downloaded:
            await r.point(link, click=True)
        download = await downloaded.value
        temp = ROOT / ".local/video-prep/downloaded-crm-tasks.csv"
        await download.save_as(temp)
        assert temp.read_bytes() == csv_bytes
        await r.beat("crm-download")
        other = await browser.new_context()
        refused = await other.request.get(args.base_url + href)
        assert refused.status in (401, 404)
        await other.close()
        await r.finish(17)
        # Byte-identical genuine export in Chromium's plain-text file viewer. This is
        # a downloaded artifact, not a mocked app or a fabricated spreadsheet UI.
        preview = ROOT / ".local/video-prep/crm-tasks.csv.txt"
        preview.write_bytes(csv_bytes)
        r.origin = time.monotonic()
        r.page = await ctx.new_page()
        await r.page.goto(preview.as_uri())
        await r.page.wait_for_function('() => document.body.innerText.includes("Maria")')
        r.name = "scene7-csv"
        r.started = time.monotonic()
        r.offset = r.started - r.origin
        await r.beat("actual-export")
        await r.finish(3)

        async def schedule_ready(page):
            await page.get_by_role("switch", name="Nightly review schedule").wait_for()

        await r.open("scene8", "#/schedule", schedule_ready)
        toggle = r.page.get_by_role("switch", name="Nightly review schedule")
        await r.point(toggle, click=True)
        await r.page.wait_for_function('() => document.querySelector("[role=switch]").checked')
        await r.beat("nightly-on")
        await r.at(6)
        await r.point(r.page.get_by_text("Runs every night at 2:00 AM MT on Vultr", exact=True))
        await r.beat("server-schedule")
        await r.at(8)
        r.manifest["schedule_tab_closed_at_seconds"] = 8
        await r.page.close()
        await r.finish(12)
        # Prove it survives closing the captured tab, then disable only our test schedule.
        page = await ctx.new_page()
        await page.goto(args.base_url + "/#/schedule")
        toggle = page.get_by_role("switch", name="Nightly review schedule")
        await toggle.wait_for()
        assert await toggle.is_checked()
        await toggle.click()
        await page.wait_for_function('() => !document.querySelector("[role=switch]").checked')
        await page.close()
        r.manifest["checks"] = {
            "fresh_saved_group": True,
            "run_available": True,
            "real_reset": True,
            "full_run_succeeded": True,
            "all_numbers_match": True,
            "sandy_40_export_rows": True,
            "byte_identical_download": True,
            "cross_session_refused": True,
            "schedule_survived_tab_close": True,
            "test_schedule_disabled": True,
            "page_errors": r.errors,
        }
        assert not r.errors, r.errors
        r.save()
        await ctx.close()
        await browser.close()
        print(json.dumps(r.manifest["checks"]), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
