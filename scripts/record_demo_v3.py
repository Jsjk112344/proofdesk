"""Record a fresh public run and v3 takes without altering app state or UI text."""

# ruff: noqa: E501
import argparse
import asyncio
import json
import math
import subprocess
import time
from decimal import Decimal
from pathlib import Path

from playwright.async_api import async_playwright

from scripts.record_demo_scenes import BASE, CURSOR, ROOT, VIDEO, Recorder, group_ready, store_ready


class V3Recorder(Recorder):
    def __init__(self, ctx, base):
        super().__init__(ctx, base)
        self.position = [40, 680]
        self.manifest.update(
            viewport=[1280, 720], device_scale_factor=1.5, video_resolution=[1920, 1080]
        )

    async def move_to(self, x, y, duration=0.9):
        """A paced cosine path with zero velocity at both ends."""
        sx, sy = self.position
        started = time.monotonic()
        frames = round(duration * 60)
        for frame in range(1, frames + 1):
            progress = frame / frames
            eased = (1 - math.cos(math.pi * progress)) / 2
            await self.page.mouse.move(sx + (x - sx) * eased, sy + (y - sy) * eased)
            await asyncio.sleep(max(0, started + duration * progress - time.monotonic()))
        self.position = [x, y]

    async def point(self, locator, click=False):
        await locator.wait_for(state="visible")
        box = await locator.bounding_box()
        assert box
        viewport = self.page.viewport_size
        if click and (box["y"] < 55 or box["y"] + box["height"] > viewport["height"]):
            await locator.scroll_into_view_if_needed()
            box = await locator.bounding_box()
        x = max(24, min(viewport["width"] - 24, box["x"] + box["width"] / 2))
        y = max(72, min(viewport["height"] - 24, box["y"] + min(box["height"] / 2, 80)))
        await self.move_to(x, y)
        if click:
            await self.page.mouse.down()
            await asyncio.sleep(0.1)
            await self.page.mouse.up()

    async def finish(self, duration):
        await self.at(duration)
        video = self.page.video
        elapsed = time.monotonic() - self.started
        await self.page.close()
        raw = await video.path()
        target = VIDEO / "scenes" / (self.name + ".mp4")
        # Playwright records CSS pixels, independent of screenshot device scale.
        # Match the CSS viewport, then scale the entire frame without padding.
        await asyncio.to_thread(
            subprocess.run,
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                str(self.offset),
                "-i",
                str(raw),
                "-vf",
                "fps=30,scale=1920:1080:flags=lanczos,tpad=stop_mode=clone:stop_duration=30",
                "-t",
                str(duration),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-threads",
                "4",
                "-pix_fmt",
                "yuv420p",
                str(target),
            ],
            check=True,
        )
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
        (VIDEO / "scene-manifest-v3.json").write_text(json.dumps(self.manifest, indent=2) + "\n")


async def main():
    raw = ROOT / ".local/video-prep/raw-v3"
    raw.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1.5,
            record_video_dir=str(raw),
            record_video_size={"width": 1280, "height": 720},
        )
        await ctx.add_init_script(CURSOR)
        r = V3Recorder(ctx, BASE)
        await r.open("v3-run", "#/", group_ready)
        await r.beat("map")
        await r.at(2)
        await r.point(r.page.get_by_role("button", name="Run tonight’s review now"), click=True)
        clicked = time.monotonic()
        await r.page.get_by_role("heading", name="Every rooftop. Working together.").wait_for()
        await r.at(5)
        tile = r.page.locator('.rooftop-tile[href="#/store/r02"]')
        await r.point(tile)
        await r.beat("tiles")
        await r.at(13)
        await r.point(tile, click=True)
        await r.page.locator(".agent-trace").wait_for()
        await r.beat("trace-live")
        observations = []
        last = None
        while time.monotonic() - clicked < 420:
            state = await (await ctx.request.get(BASE + "/api/dealer")).json()
            sandy = next(x for x in state["rooftops"] if x["id"] == "r02")
            stages = [e["stage"] for e in sandy["job"]["events"]]
            observations.append(
                {
                    "elapsed": round(time.monotonic() - clicked, 3),
                    "sandy_status": sandy["job"]["status"],
                    "stages": stages,
                }
            )
            if stages != last:
                await r.beat("trace-" + stages[-1])
                print(json.dumps(observations[-1]), flush=True)
                last = stages
            if state["review"]["status"] in ("succeeded", "failed"):
                break
            await asyncio.sleep(0.7)
        wall = round(time.monotonic() - clicked, 3)
        assert state["review"]["status"] == "succeeded" and not state["rollup"]["failures"]
        await store_ready(r.page)
        await r.beat("trace-done")
        await r.finish(round(time.monotonic() - r.started, 3))
        maria = next(x for x in sandy["result"]["queue"] if x["customer"] == "Maria G.")
        draft = next(x for x in sandy["followups"] if x["lead_id"] == maria["lead_id"])
        briefs = [x["result"]["brief"] for x in state["rooftops"]] + [state["rollup"]["brief"]]
        live = [b for b in briefs if b["receipt"]["provider"] != "saved_replay"]
        cost = sum(
            (
                Decimal(b["receipt"]["usage"]["prompt_tokens"]) * Decimal(".10")
                + Decimal(b["receipt"]["usage"]["completion_tokens"]) * Decimal(".20")
            )
            / Decimal(1000000)
            for b in live
        )
        facts = {
            "url": BASE,
            "reference_time": state["reference_time"],
            "review": state["review"],
            "wall_clock_seconds": wall,
            "inference_cost_usd": str(cost),
            "live_responses": len(live),
            "replayed_responses": len(briefs) - len(live),
            "cost_basis": "Provider-reported token usage, $0.10 input / $0.20 output per million; excludes compute. Replayed responses incur no new inference.",
            "group": state["rollup"]["totals"],
            "sandy": {
                "trace": sandy["result"]["trace"],
                "events": sandy["job"]["events"],
                "metrics": sandy["result"]["metrics"],
                "followups": len(sandy["followups"]),
                "qwen_followups": sum(
                    x["provenance"] in ("saved_replay", "live_model") for x in sandy["followups"]
                ),
            },
            "maria": maria,
            "maria_sms": draft["content"]["sms"],
            "maria_provenance": draft["provenance"],
            "observations": observations,
        }
        (VIDEO / "recording-facts-v3.json").write_text(json.dumps(facts, indent=2) + "\n")
        (ROOT / ".local/video-prep/v3-state.json").write_text(json.dumps(state))
        await r.open("v3-maria", "#/store/r02", store_ready)
        await r.point(r.page.get_by_role("button", name="Open Maria G. details"), click=True)
        dialog = r.page.get_by_role("dialog", name="Maria G. lead detail")
        await dialog.wait_for()
        for second, selector, name in [
            (2, ".lead-context", "wanted"),
            (5, ".lead-timeline .sold", "sold"),
            (8, ".candidate.chosen", "match"),
            (12, ".candidate.chosen details", "score"),
            (15, ".lead-context span", "trade"),
            (18, ".drawer-message", "sms"),
        ]:
            await r.at(second)
            if name == "score":
                await dialog.locator(selector).locator("summary").click()
            await r.point(dialog.locator(selector))
            await r.beat(name)
            if name == "score":
                await dialog.locator(selector).locator("summary").click()
        await r.finish(26)
        await r.open("v3-approve", "#/store/r02", store_ready)
        await r.point(r.page.locator(".store-queue"))
        await r.beat("queue")
        await r.at(2)
        await r.point(
            r.page.get_by_role("button", name="Approve all for Sandy", exact=True), click=True
        )
        await r.page.get_by_role("link", name="CRM tasks", exact=True).wait_for()
        await r.point(r.page.locator(".handoff-panel"))
        await r.beat("ready")
        await r.finish(12)
        await r.open("v3-group", "#/", group_ready)
        await r.beat("totals")
        await r.finish(3)
        assert not r.errors, r.errors
        await browser.close()
        print(
            json.dumps(
                {
                    k: v
                    for k, v in facts.items()
                    if k
                    in (
                        "wall_clock_seconds",
                        "inference_cost_usd",
                        "live_responses",
                        "replayed_responses",
                        "group",
                        "maria_sms",
                    )
                }
            ),
            flush=True,
        )


async def polish_take():
    """Retake reading holds and one real sample approval; no review/inference."""
    storage = ROOT / ".local/video-prep/scene-storage.json"
    original_storage = storage.read_bytes()
    facts = json.loads((VIDEO / "recording-facts-v3.json").read_text())
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        async def context(saved=False):
            ctx = await browser.new_context(
                **({"storage_state": str(storage)} if saved else {}),
                viewport={"width": 1280, "height": 720},
                device_scale_factor=1.5,
                record_video_dir=str(ROOT / ".local/video-prep/raw-v3"),
                record_video_size={"width": 1280, "height": 720},
            )
            await ctx.add_init_script(CURSOR)
            return ctx

        def settled(r):
            # Exclude page loading and preparation from the visible take.
            r.manifest["beats"] = [b for b in r.manifest["beats"] if b["scene"] != r.name]
            r.started = time.monotonic()
            r.offset = r.started - r.origin

        try:
            ctx = await context(saved=True)
            r = V3Recorder(ctx, BASE)
            r.manifest = json.loads((VIDEO / "scene-manifest-v3.json").read_text())
            names = {"v3-maria", "v3-match", "v3-approve", "v3-ready"}
            for key in ("scenes", "beats"):
                r.manifest[key] = [s for s in r.manifest[key] if s["scene"] not in names]
            await r.open("v3-maria", "#/store/r02", store_ready)
            await r.page.get_by_role("button", name="Open Maria G. details").click()
            drawer = r.page.get_by_role("dialog", name="Maria G. lead detail")
            await drawer.wait_for()
            assert (await drawer.locator(".drawer-message > p").inner_text()) == facts["maria_sms"]
            await r.page.mouse.move(500, 680)
            r.position = [500, 680]
            settled(r)
            for second, beat in [
                (0, "wanted"),
                (3, "sold"),
                (6, "match"),
                (10, "trade"),
                (14, "sms"),
            ]:
                await r.at(second)
                await r.beat(beat)
            await r.finish(26)

            await r.open("v3-match", "#/store/r02", store_ready)
            await r.page.get_by_role("button", name="Open Maria G. details").click()
            await r.page.locator(".candidate.chosen .score-details summary").click()
            await r.page.mouse.move(500, 680)
            r.position = [500, 680]
            settled(r)
            await r.beat("score")
            await r.finish(2)

            # A separate saved-sample session permits a genuine new approval click.
            # It reuses the accepted sample and schedules no analysis or inference.
            fresh = await context()
            r.ctx = fresh
            await r.open("v3-approve", "#/store/r02", store_ready)
            state = await (await fresh.request.get(BASE + "/api/dealer")).json()
            assert state["review"] is None and state["saved_sample_review"]
            sandy = next(s for s in state["rooftops"] if s["id"] == "r02")
            maria = next(s for s in sandy["result"]["queue"] if s["customer"] == "Maria G.")
            draft = next(d for d in sandy["followups"] if d["lead_id"] == maria["lead_id"])
            assert draft["content"]["sms"] == facts["maria_sms"]
            button = r.page.get_by_role("button", name="Approve all for Sandy", exact=True)
            box = await button.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            await r.page.mouse.move(x - 150, y + 45)
            r.position = [x - 150, y + 45]
            settled(r)
            await r.beat("queue")
            await r.at(1)
            await r.point(button, click=True)
            await r.page.get_by_role("link", name="CRM tasks", exact=True).wait_for()
            await r.beat("ready")
            await r.finish(6)

            await r.open("v3-ready", "#/store/r02", store_ready)
            await r.page.locator(".handoff-panel.ready").wait_for()
            await r.page.mouse.move(228, 680)
            r.position = [228, 680]
            settled(r)
            await r.beat("settled")
            await r.finish(7)
            r.manifest["polish_note"] = (
                "Locked Maria/score holds from the existing completed review, pointer parked off text. "
                "Approval and Ready retaken in a separate saved-sample session with identical Maria SMS; "
                "actual approval/handoff, no new review or inference. Group/trace footage retains the original measured run."
            )
            assert not r.errors, r.errors
            r.save()
        finally:
            storage.write_bytes(original_storage)
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-only", action="store_true")
    parser.add_argument("--polish-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(polish_take() if args.polish_only or args.ready_only else main())
