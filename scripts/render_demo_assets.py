"""Render reproducible 1080p cards and a PDF deck from public screenshots and run evidence."""

# ruff: noqa: E501

import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "docs/video"
BASE = "https://salesdesk.149.28.51.139.sslip.io"
LOGO = '<span class="mark"><svg viewBox="0 0 24 24"><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/></svg></span>'
CSS = """
@font-face{font-family:Inter;src:url('fonts/InterVariable.woff2')}*{box-sizing:border-box}
html,body{margin:0;font-family:Inter,sans-serif;color:#162d32;background:transparent}
section{width:1920px;height:1080px;position:relative;overflow:hidden;padding:100px 112px;background:#f5f7f6;break-after:page}
h1,h2,p{margin:0}h1{font-size:92px;font-weight:650;letter-spacing:-.04em;line-height:1.1}
h2{font-size:66px;font-weight:620;letter-spacing:-.035em;line-height:1.15}
p{font-size:32px;line-height:1.55}small{font-size:24px;line-height:1.6}
.dark{background:#142e34;color:#f5f7f6}.mint{color:#83dfbd}.brand{display:flex;align-items:center;gap:25px;justify-content:center}
.mark{display:inline-grid;place-items:center;background:#83dfbd;border-radius:24px;width:100px;height:100px}
.mark svg{width:70px;height:70px;fill:none;stroke:#142e34;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.center{display:flex;align-items:center;justify-content:center;text-align:center;flex-direction:column}
.title p{font-size:44px;margin-top:30px}.title h1{font-size:96px}.title.transparent{background:transparent;color:#fff}
.kicker{font-size:26px;margin-bottom:40px;color:#83dfbd}.footer{position:absolute;bottom:65px;left:112px;right:112px;font-size:24px;color:#526a6e}
.dark .footer{color:#b2cdc9}.columns{display:grid;grid-template-columns:1fr 1fr;gap:120px;margin-top:80px}
.col h2{font-size:48px;margin-bottom:35px}.col p{font-size:36px;line-height:1.9}.after{padding-left:80px;border-left:1px solid #cbdad4}
.after p{font-size:45px;font-weight:540;line-height:1.8}.after h2{color:#087e67}.before h2{color:#647c7a}
.bg{position:absolute;inset:-40px;width:2000px;height:1160px;object-fit:cover;filter:blur(20px) brightness(.36)}
.foreground{position:relative;z-index:1}.nodes{display:flex;align-items:center;gap:0;margin:160px -48px 0}
.node{width:190px;min-height:230px;flex-shrink:0;display:flex;justify-content:center;flex-direction:column;border:1px solid #4e686d;padding:22px 16px;border-radius:16px}
.node b{font-size:27px;line-height:1.3;font-weight:600}.node span{font-size:20px;line-height:1.5;margin-top:20px;color:#b2cdc9}
.arrow{width:30px;flex-shrink:0;text-align:center;font-size:30px;color:#83dfbd}.hidden{visibility:hidden}
.arch h2{max-width:1350px}.arch .note{font-size:25px;line-height:1.6;max-width:1450px;margin-top:50px;color:#b2cdc9}
.end .urls{font-size:33px;line-height:1.9;margin-top:60px}.end .event{font-size:26px;margin-top:50px;color:#83dfbd}
.screen{padding:58px 80px}.screen h2{font-size:42px;margin-bottom:28px}.screen img{width:1300px;height:812.5px;object-fit:contain;float:right}
.screen .aside{position:absolute;left:80px;top:250px;width:350px}.screen .aside p{font-size:30px;margin-bottom:30px}
.screen .caption{position:absolute;bottom:25px;font-size:22px;color:#526a6e}
@page{size:1920px 1080px;margin:0}@media print{body{background:#fff}section{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
"""


def doc(body):
    return '<!doctype html><meta charset="utf-8"><style>' + CSS + "</style>" + body


def section(body, cls=""):
    return f'<section class="{cls}">{body}</section>'


def architecture(build=7):
    nodes = [
        ("Browser", "Public HTTPS", 1),
        ("Caddy", "HTTPS gateway", 1),
        ("FastAPI + scheduler", "Vultr VM · EWR", 2),
        ("24 rooftop jobs", "Docker sandboxes<br>6 parallel", 3),
        ("Vultr Inference", "Qwen 3.8<br>Validated contracts", 4),
        ("Manager approval", "Exact draft version", 5),
        ("Worker", "Durable leased jobs", 6),
        ("Ready for review", "Drafts · CRM tasks<br>Transfer requests", 7),
    ]
    chunks = []
    for i, (title, detail, stage) in enumerate(nodes):
        visibility = " hidden" if stage > build else ""
        if i:
            chunks.append(f'<div class="arrow{visibility}">→</div>')
        chunks.append(f'<div class="node{visibility}"><b>{title}</b><span>{detail}</span></div>')
    return section(
        '<p class="kicker">Built on Vultr</p><h2>Every rooftop reviewed.<br>Every action approved.</h2>'
        + '<div class="nodes">'
        + "".join(chunks)
        + "</div>"
        + '<p class="note">Sandboxed analysis → reconciled metrics → Qwen briefs and drafts. '
        "The controller holds credentials and budgets. People approve the exact draft; "
        "the worker prepares downloads. No customer messages are sent.</p>"
        + '<div class="footer">SalesDesk · Powering the Future of Work · Vultr Agent Rush</div>',
        "dark arch",
    )


async def capture(browser):
    """Only navigation and normal UI actions, with no response interception."""
    ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    page = await ctx.new_page()
    page.set_default_timeout(60000)
    await page.goto(BASE)
    await page.get_by_role("heading", name="Good morning.", exact=False).wait_for()
    await page.screenshot(path=str(ROOT / "docs/assets/salesdesk-group.png"))
    await page.get_by_label("View role").select_option("r02")
    await page.get_by_role("button", name="Open Maria G. details").wait_for()
    await page.screenshot(path=str(ROOT / "docs/assets/salesdesk-store.png"))
    await page.get_by_role("button", name="Open Maria G. details").click()
    await page.get_by_role("dialog").wait_for()
    await page.screenshot(path=str(ROOT / "docs/assets/salesdesk-maria.png"))
    await ctx.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    report = json.loads((VIDEO / "measured-run.json").read_text())
    runtime = report["wall_clock_seconds"]
    minutes = runtime / 60
    timing = f"{runtime:.1f} seconds ({minutes:.1f} minutes)"
    title = (
        '<div class="foreground"><div class="brand">'
        + LOGO
        + '<h1>SalesDesk<span class="mint">.</span></h1></div><p>Sell more: your AI sales analyst.</p></div>'
    )
    cards = {
        "01-title": section(title, "center title transparent"),
        "01-title-composited": section(
            '<img class="bg" src="../assets/salesdesk-group.png">' + title, "dark center title"
        ),
        "02-jumpcut": section(
            '<p class="kicker">Same review · later</p><h2>Full 24-store review:<br>'
            + f'{minutes:.1f} minutes on Vultr</h2><p class="mint" style="margin-top:45px">shortened for this video</p><div class="footer">Measured public run: {runtime:.3f} s · Actual app footage at normal speed</div>',
            "dark center",
        ),
        "03-before-after": section(
            '<h1>A morning queue. Ready to approve.</h1><div class="columns"><div class="col before"><h2>Before</h2><p>Search the CRM for cold leads<br>Check if their car sold<br>Call other stores for stock<br>Write every follow-up</p></div><div class="col after"><h2>After</h2><p>Open SalesDesk<br>Approve a ranked queue</p></div></div><div class="footer">Full 24-store review: '
            + timing
            + " on Vultr, measured.<br>Sample dealer group · No measured human time savings or sales uplift claimed.</div>"
        ),
        "04-architecture": architecture(),
        "05-end": section(
            title
            + '<div class="urls">salesdesk.149.28.51.139.sslip.io<br>github.com/Jsjk112344/salesdesk</div><p class="event">Built for Vultr Agent Rush</p>',
            "dark center title end",
        ),
    }
    for i in range(1, 8):
        cards[f"04-architecture-build-{i}"] = architecture(i)
    (VIDEO / "cards").mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        if args.capture:
            await capture(browser)
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, device_scale_factor=1
        )
        page = await ctx.new_page()
        for name, body in cards.items():
            path = VIDEO / (name + ".html")
            path.write_text(doc(body))
            await page.goto(path.as_uri())
            await page.evaluate("document.fonts.ready")
            await page.screenshot(
                path=str(VIDEO / "cards" / (name + ".png")), omit_background=name == "01-title"
            )
            path.unlink()
        total = report["totals"]
        pages = [cards["01-title-composited"], cards["03-before-after"]]
        for image, heading, copy in [
            (
                "group",
                "Leadership sees the whole group.",
                f"{total['open_leads']:,} leads reviewed.<br>{total['at_risk']:,} at risk.<br>{total['matched_in_stock']:,} best matches in stock.<br>{total['aged_matched']:,} distinct aged units matched.",
            ),
            (
                "store",
                "Store managers get a ranked queue.",
                "Sandy: 40 follow-ups.<br>Risk, available inventory and trade context together.",
            ),
            (
                "maria",
                "A fresh reason to follow up.",
                "Maria G.<br>Silver RAV4 Hybrid XLE.<br>74 days on lot.<br>2017 Honda CR-V trade.",
            ),
        ]:
            pages.append(
                section(
                    f'<h2>{heading}</h2><div class="aside"><p>{copy}</p></div><img src="../assets/salesdesk-{image}.png"><p class="caption">Actual public app capture · Sample dealer group · Fictional people and data</p>',
                    "screen",
                )
            )
        pages += [
            architecture(),
            section(
                '<p class="kicker">Measured, inspectable work</p><h1>AI drafts.<br>People approve.</h1><p style="margin-top:60px">CSV input today. CRM / DMS connections next.<br>Exact version approvals; editing clears approval.<br>Revalidated replay is labelled. New inputs use bounded live inference.<br>Nothing is sent to customers.</p><div class="footer">Measured live inference: $'
                + report["inference_cost_usd"]
                + " per complete 24-store run.<br>25 provider responses at catalog token rates; VM billing separate. Not a billing receipt.</div>",
                "dark",
            ),
            cards["05-end"],
        ]
        deck = VIDEO / "SalesDesk-slides.html"
        deck.write_text(doc("".join(pages)))
        await page.goto(deck.as_uri())
        await page.evaluate("document.fonts.ready")
        await page.pdf(
            path=str(VIDEO / "SalesDesk-slides.pdf"),
            width="1920px",
            height="1080px",
            print_background=True,
            prefer_css_page_size=True,
        )
        await browser.close()
    print(
        json.dumps(
            {
                "cards": len(cards),
                "deck_pages": len(pages),
                "resolution": "1920x1080",
                "device_scale_factor": 1,
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
