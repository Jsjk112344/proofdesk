"""Render animated 1080p HTML cards with exact measured figures."""

# ruff: noqa: E501
import asyncio
import json
import subprocess

from playwright.async_api import async_playwright

from scripts.render_demo_assets import CSS, LOGO, ROOT, VIDEO


async def main():
    facts = json.loads((VIDEO / "recording-facts-v2.json").read_text())
    out = VIDEO / "cards-v2"
    out.mkdir(exist_ok=True)
    work = ROOT / ".local/video-prep/cards-v2"
    work.mkdir(parents=True, exist_ok=True)
    seconds = round(facts["wall_clock_seconds"])
    minute, sec = divmod(seconds, 60)
    elapsed = f"{minute} min {sec} sec later"
    cards = {
        "opening": ("Nine days ago…", "", 3),
        "scale": (str(facts["group"]["at_risk"]), "leads at risk this morning", 8),
        "thesis": (
            "Dealers don't lose these sales<br>for lack of cars.",
            "They lose them because nobody connects<br>the lead to the car in time.",
            8,
        ),
        "title": ("Your AI sales analyst", "Connects every lead to the right car. Every night.", 7),
        "skip": (elapsed, "All 24 stores reviewed on Vultr", 4),
        "matched": (
            str(facts["group"]["matched_in_stock"]),
            "customers matched to a car in stock",
            6,
        ),
        "gross": (
            "$" + format(facts["group"]["recoverable_gross"], ",.0f"),
            "estimated gross back in play",
            6,
        ),
        "end": ("Every lead. Every store.<br>Every morning.", "", 11),
    }
    for i, label in enumerate(
        ["Fan out", "Find who's slipping", "Find the right car", "Write the brief"], 1
    ):
        cards[f"lower-{i}"] = (f"Step {i} · {label}", "", [12, 12, 15, 11][i - 1])
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        for name, (title, sub, duration) in cards.items():
            bg = ""
            if name in ("title", "scale"):
                bg = '<img class="bg" src="stills/v2-run-map.png">'
            urls = (
                '<div class="urls">salesdesk.149.28.51.139.sslip.io<br>github.com/Jsjk112344/salesdesk</div>'
                if name == "end"
                else ""
            )
            footer = (
                "<footer>Sample dealer group · SalesDesk drafts; people send.</footer>"
                if name == "end"
                else ""
            )
            count = facts["group"].get(
                {
                    "scale": "at_risk",
                    "matched": "matched_in_stock",
                    "gross": "recoverable_gross",
                }.get(name, "")
            )
            body = f'{bg}<div class="motion"><div class="brand">{LOGO}<b>SalesDesk.</b></div><h1 id="number">{title}</h1><p>{sub}</p>{urls}</div>{footer}'
            style = (
                CSS
                + """
section{padding:90px; background:#142e34;color:#f5f7f6}.brand{font-size:48px;margin-bottom:65px}.mark{width:64px;height:64px;border-radius:16px}.mark svg{width:46px;height:46px}h1{font-size:88px;line-height:1.18}p{font-size:40px;margin-top:38px;line-height:1.45}.motion{position:relative;opacity:var(--alpha,1);transform:translateY(var(--rise,0px))}.urls{font-size:29px;line-height:1.8;margin-top:45px}footer{position:absolute;bottom:48px;font-size:22px;color:#b2cdc9}
"""
            )
            if name.startswith("lower-"):
                style += "section{background:#ff00ff}.brand{display:none}.motion{position:absolute;left:70px;bottom:70px;background:#142e34;padding:24px 30px;border-radius:8px}h1{font-size:36px;letter-spacing:0}p{display:none}"
            if name == "scale":
                # Real map and real sample badge are cropped from the recorded screenshot.
                body = f'<div class="brand" style="position:absolute;top:70px;left:90px">{LOGO}<b>SalesDesk.</b></div><div class="map-window"><img id="map-pull" src="stills/v2-run-map.png"></div><div class="sample-window"><img src="stills/v2-run-map.png"></div><div class="motion scale-copy"><h1 id="number">{title}</h1><p>{sub}</p></div>'
                style += ".map-window{position:absolute;left:80px;top:300px;width:1080px;height:510px;overflow:hidden;border-radius:18px}.map-window img{position:absolute;width:2016px;max-width:none;left:-347px;top:-483px;transform-origin:880px 730px}.sample-window{position:absolute;right:90px;top:60px;width:235px;height:55px;overflow:hidden}.sample-window img{position:absolute;width:2880px;max-width:none;left:-2085px;top:-45px}.scale-copy{position:absolute;right:90px;top:390px;width:560px}.scale-copy h1{font-size:142px}.scale-copy p{font-size:40px}"
            html = (
                '<!doctype html><meta charset="utf-8"><style>'
                + style
                + '</style><section class="center">'
                + body
                + "</section>"
            )
            path = VIDEO / f"card-v2-{name}.html"
            path.write_text(html)
            await page.goto(path.as_uri())
            await page.evaluate("document.fonts.ready")
            frames = work / name
            frames.mkdir(exist_ok=True)
            for frame in range(31):
                t = frame / 30
                await page.evaluate(
                    """({t,n,money})=>{document.documentElement.style.setProperty('--alpha',Math.min(1,t/.25));document.documentElement.style.setProperty('--rise',(8*(1-Math.min(1,t/.25)))+'px'); if(n!==null)document.querySelector('#number').innerText=(money?'$':'')+Math.round(n*(1-Math.pow(1-Math.min(1,t),3))).toLocaleString('en-US')}""",
                    {"t": t, "n": count, "money": name == "gross"},
                )
                if name == "scale":
                    await page.evaluate(
                        "t=>document.querySelector('#map-pull').style.transform=`scale(${1+.7*(1-t)})`",
                        t,
                    )
                await page.screenshot(path=str(frames / f"{frame:03}.png"))
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-framerate",
                    "30",
                    "-i",
                    str(frames / "%03d.png"),
                    "-vf",
                    f"tpad=stop_mode=clone:stop_duration={duration},format=yuv420p",
                    "-t",
                    str(duration),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    str(out / f"{name}.mp4"),
                ],
                check=True,
            )
            print(name, flush=True)
        # Four honest architecture nodes, revealed from left to right.
        nodes = [
            ("Nightly scheduler", "Vultr VM"),
            ("24 store jobs", "Docker · 6 parallel"),
            ("Qwen", "Vultr Serverless Inference"),
            ("Manager approval", "Tasks and drafts"),
        ]
        body = (
            '<h1>Built on Vultr</h1><div class="nodes">'
            + "".join(
                ('<div class="arrow">→</div>' if i else "")
                + f'<div class="node" data-i="{i}"><b>{a}</b><span>{b}</span></div>'
                for i, (a, b) in enumerate(nodes)
            )
            + "</div>"
        )
        html = (
            '<!doctype html><meta charset="utf-8"><style>'
            + CSS
            + '.nodes{margin:100px 0}.node{width:350px;min-height:260px}.node b{font-size:36px}.node span{font-size:27px}.arrow{width:60px}.node,.arrow{opacity:0}</style><section class="dark center">'
            + body
            + "</section>"
        )
        path = VIDEO / "card-v2-architecture.html"
        path.write_text(html)
        await page.goto(path.as_uri())
        await page.evaluate("document.fonts.ready")
        frames = work / "architecture"
        frames.mkdir(exist_ok=True)
        for frame in range(121):
            await page.evaluate(
                't=>document.querySelectorAll(".node,.arrow").forEach((e,i)=>{let p=Math.min(1,Math.max(0,(t-Math.ceil(i/2))/.25));e.style.opacity=p;e.style.transform=`translateY(${8*(1-p)}px)`})',
                frame / 30,
            )
            await page.screenshot(path=str(frames / f"{frame:03}.png"))
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-framerate",
                "30",
                "-i",
                str(frames / "%03d.png"),
                "-vf",
                "tpad=stop_mode=clone:stop_duration=12,format=yuv420p",
                "-t",
                "12",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                str(out / "architecture.mp4"),
            ],
            check=True,
        )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
