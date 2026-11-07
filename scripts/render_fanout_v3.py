"""Render an editorial fan-out graphic, never composited onto product footage."""

# ruff: noqa: E501
import asyncio
import json
import subprocess

from playwright.async_api import async_playwright

from scripts.render_demo_assets import CSS, LOGO, ROOT, VIDEO


async def main():
    facts = json.loads((VIDEO / "recording-facts-v2.json").read_text())
    total = facts["group"]["open_leads"]
    stores = facts["fanout"]["store_count"]
    concurrency = facts["fanout"]["concurrency"]
    assert stores == 24 and concurrency == 6
    work = ROOT / ".local/video-prep/fanout-v3"
    work.mkdir(parents=True, exist_ok=True)
    nodes = []
    lines = []
    for i in range(stores):
        if i < 12:
            x = 260 + (i % 6) * 210
            y = 250 if i < 6 else 820
        else:
            j = i - 12
            x = [260, 470, 1100, 1310][j % 4]
            y = 390 + (j // 4) * 145
        nodes.append(
            f'<div class="store" data-i="{i}" data-x="{x}" data-y="{y}" style="left:{x}px;top:{y}px"><b>Store {i + 1:02}</b><span class="state">Queued</span><small>♙ Leads · ▱ Cars · ▤ Brief</small></div>'
        )
        lines.append(f'<line x1="810" y1="535" x2="{x}" y2="{y}"/>')
    html = (
        '<!doctype html><meta charset="utf-8"><style>'
        + CSS
        + """
section{background:#142e34;color:#f5f7f6}.heading{position:absolute;top:60px;left:90px;font-size:44px}.map{position:absolute;left:220px;top:195px;width:1170px;height:710px;opacity:.12;background:#7bdcba;clip-path:polygon(4% 25%,20% 8%,41% 15%,61% 2%,82% 19%,96% 40%,86% 67%,64% 94%,45% 80%,20% 92%,8% 60%)}svg.links{position:absolute;inset:0;width:1920px;height:1080px;stroke:#70ae9a;stroke-width:2;opacity:.35}.hub{position:absolute;left:715px;top:455px;width:190px;height:160px;border:2px solid #80dabb;border-radius:24px;display:flex;align-items:center;justify-content:center;flex-direction:column;background:#1d4449;font-size:25px;gap:15px}.hub .mark{width:42px;height:42px}.store{position:absolute;width:180px;padding:12px 8px;border:1px solid #557872;border-radius:12px;background:#19383e;transform:translate(-50%,-50%);text-align:center;transition:background .15s}.store b{font-size:19px}.store span{display:block;font-size:16px;margin:7px 0;color:#aac2b9}.store small{font-size:13px}.store.active{background:#176f61;border-color:#8ce0be}.store.done{background:#234f45;border-color:#80dabb}.counters{position:absolute;right:80px;top:390px;width:330px}.counters strong{font-size:90px;display:block;color:#87e3bb}.counters p{font-size:25px;margin:8px 0 35px}.compute{position:absolute;bottom:60px;left:600px;font-size:25px;border:1px solid #5f9c8c;border-radius:30px;padding:14px 35px}
</style><section><div class="heading">One group. Every store.</div><div class="map"></div><svg class="links">"""
        + "".join(lines)
        + '</svg><div class="hub">'
        + LOGO
        + "<b>SalesDesk</b><span>2 AM</span></div>"
        + "".join(nodes)
        + '<div class="counters"><strong id="stores">0</strong><p>stores reviewed</p><strong id="leads">0</strong><p>leads checked</p></div><div class="compute">Vultr · 6 parallel isolated sandboxes</div></section>'
    )
    path = VIDEO / "card-v3-fanout.html"
    path.write_text(html)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(path.as_uri())
        await page.evaluate("document.fonts.ready")
        for frame in range(360):
            await page.evaluate(
                """({t,total})=>{let progress=Math.max(0,Math.min(4,(t-1)/2.4));let batch=Math.floor(progress);document.querySelectorAll('.store').forEach((e,i)=>{let group=Math.floor(i/6);let done=group<batch;e.className='store '+(done?'done':group===batch?'active':'');e.querySelector('.state').innerText=done?'✓ Ready':group===batch?'Analysing on Vultr':'Queued';let a=Math.min(1,t/.7);e.style.opacity=a;e.style.transform=`translate(-50%,-50%) translate(${(810-Number(e.dataset.x))*(1-a)}px,${(535-Number(e.dataset.y))*(1-a)}px)`});document.querySelector('#stores').innerText=Math.min(24,batch*6);document.querySelector('#leads').innerText=Math.round(total*Math.min(1,progress/4)).toLocaleString('en-US')}""",
                {"t": frame / 30, "total": total},
            )
            await page.screenshot(path=str(work / f"{frame:03}.png"))
        await b.close()
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-framerate",
            "30",
            "-i",
            str(work / "%03d.png"),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(VIDEO / "cards-v3/fanout.mp4"),
        ],
        check=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
