"""Record a fresh public run and v2 takes without altering app state or UI text."""

# ruff: noqa: E501
import argparse
import asyncio
import json
import time
from decimal import Decimal

from playwright.async_api import async_playwright

from scripts.record_demo_scenes import BASE, CURSOR, ROOT, VIDEO, Recorder, group_ready, store_ready


class V2Recorder(Recorder):
    def save(self):
        (VIDEO / "scene-manifest-v2.json").write_text(json.dumps(self.manifest, indent=2) + "\n")


async def main():
    raw = ROOT / ".local/video-prep/raw-v2"
    raw.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            record_video_dir=str(raw),
            record_video_size={"width": 1440, "height": 900},
        )
        await ctx.add_init_script(CURSOR)
        r = V2Recorder(ctx, BASE)
        await r.open("v2-run", "#/", group_ready)
        await r.beat("map")
        await r.at(2)
        await r.point(r.page.get_by_role("button", name="Run tonight’s review now"), click=True)
        clicked = time.monotonic()
        await r.page.get_by_role("heading", name="Every rooftop. Working together.").wait_for()
        await r.at(5)
        tile = r.page.locator('.rooftop-tile[href="#/store/r02"]')
        await r.point(tile)
        await r.beat("tiles")
        await r.at(10)
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
        (VIDEO / "recording-facts-v2.json").write_text(json.dumps(facts, indent=2) + "\n")
        (ROOT / ".local/video-prep/v2-state.json").write_text(json.dumps(state))
        await r.open("v2-maria", "#/store/r02", store_ready)
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
            await r.point(dialog.locator(selector))
            await r.beat(name)
        await r.finish(26)
        await r.open("v2-approve", "#/store/r02", store_ready)
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
        await r.open("v2-group", "#/", group_ready)
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


async def ready_take():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            storage_state=str(ROOT / ".local/video-prep/scene-storage.json"),
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            record_video_dir=str(ROOT / ".local/video-prep/raw-v2"),
            record_video_size={"width": 1440, "height": 900},
        )
        await ctx.add_init_script(CURSOR)
        r = V2Recorder(ctx, BASE)
        r.manifest = json.loads((VIDEO / "scene-manifest-v2.json").read_text())
        r.manifest["scenes"] = [
            x for x in r.manifest["scenes"] if x["scene"] not in ("v2-ready", "v2-maria")
        ]
        r.manifest["beats"] = [
            x for x in r.manifest["beats"] if x["scene"] not in ("v2-ready", "v2-maria")
        ]
        r.manifest["retake_note"] = (
            "Same completed session; detail retakes after approval, no new inference or message edits."
        )
        await r.open("v2-ready", "#/store/r02", store_ready)
        await r.page.locator(".agent-trace summary").click()
        await r.page.locator(".handoff-panel.ready").wait_for()
        await r.point(r.page.locator(".handoff-panel"))
        await r.beat("collapsed")
        await r.finish(7)
        await r.open("v2-maria", "#/store/r02", store_ready)
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
            await r.point(dialog.locator(selector))
            await r.page.mouse.move(760, 850, steps=30)
            r.position = [760, 850]
            await r.beat(name)
        await r.finish(26)
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(ready_take() if args.ready_only else main())
