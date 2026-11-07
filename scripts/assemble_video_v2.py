"""Assemble the exact 165-second v2 edit from real takes and HTML motion cards."""

# ruff: noqa: E501
import argparse
import json
import re
import subprocess

from scripts.assemble_demo_video import FFMPEG, ROOT, VIDEO, probe

WORK = ROOT / ".local/video-prep/edit-v2"


def run(args):
    subprocess.run([FFMPEG, "-v", "error", "-y", *args], check=True)


def encode(name, source, duration, offset=0, still=False, crop=None, lower=None, fade=False):
    out = WORK / (name + ".mp4")
    inputs = ["-loop", "1", "-framerate", "30"] if still else ["-ss", str(offset)]
    vf = "fps=30,"
    if crop:
        # Source crops include the real sticky sample badge. Never overlay UI values.
        x, y, w, h = crop
        vf += f"crop={w}:{h}:'{x}':'{y}',scale=1920:1080:flags=lanczos,"
    else:
        vf += "scale=1920:1080:flags=lanczos,"
    vf += f"tpad=stop_mode=clone:stop_duration={duration},setsar=1,format=yuv420p"
    if fade:
        vf += ",fade=t=in:st=0:d=.25"
    filters = ["-vf", vf]
    if lower:
        index = {
            "Step 1 · Fan out": 1,
            "Step 2 · Find who's slipping": 2,
            "Step 3 · Find the right car": 3,
            "Step 4 · Write the brief": 4,
        }[lower]
        filters = [
            "-i",
            str(VIDEO / "cards-v2" / f"lower-{index}.mp4"),
            "-filter_complex",
            f"[0:v]{vf}[base];[1:v]chromakey=0xFF00FF:0.25:0.12[title];[base][title]overlay=0:0:shortest=1,format=yuv420p[out]",
            "-map",
            "[out]",
        ]
    run(
        [
            *inputs,
            "-i",
            str(source),
            *filters,
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
            str(out),
        ]
    )
    return out


def focus(name, source, duration, y, h, offset=0, still=False, x=790, width=650, badge_x=815):
    """Editorial detail crop plus the same source frame's genuine sample badge.

    The badge sits in the edit's border, never over UI data. No UI text is generated.
    """
    scale = 2 if still else 1
    out = WORK / (name + ".mp4")
    inputs = ["-loop", "1", "-framerate", "30"] if still else ["-ss", str(offset)]
    height = round(h * 1760 / width / 2) * 2
    top = max(110, (1080 - height) // 2)
    graph = (
        "[0:v]split[detail][badge];"
        f"[detail]crop={width * scale}:{h * scale}:{x * scale}:{y * scale},"
        f"scale=1760:{height}:flags=lanczos,pad=1920:1080:80:{top}:color=0x142e34[body];"
        f"[badge]crop={140 * scale}:{32 * scale}:{badge_x * scale}:{24 * scale},scale=280:64[label];"
        f"[body][label]overlay=80:24,fps=30,tpad=stop_mode=clone:stop_duration={duration},setsar=1,format=yuv420p[out]"
    )
    if name == "01c":
        graph = graph.replace(
            "[out]",
            "[marked];[marked]drawbox=x=158:y=594:w=34:h=34:color=0xf0ad55@0.6:t=3:enable='lt(mod(t,1),0.55)'[out]",
        )
    if name == "01d":
        graph = graph.replace(
            "[out]", "[marked];[marked]drawbox=x=525:y=545:w=210:h=42:color=0xf0ad55@0.7:t=3[out]"
        )
    run(
        [
            *inputs,
            "-i",
            str(source),
            "-filter_complex",
            graph,
            "-map",
            "[out]",
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
            str(out),
        ]
    )
    return out


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((VIDEO / "scene-manifest-v2.json").read_text())
    beats = {b["scene"] + "-" + b["beat"]: b for b in manifest["beats"]}
    cards = VIDEO / "cards-v2"
    scenes = VIDEO / "scenes"
    stills = VIDEO / "stills"
    segments = []
    scene_files = []

    def add(n, source, duration, **kw):
        path = encode(n, source, duration, **kw)
        segments.append(path)
        return path

    # Maria story: exact 2x stills, preserving the drawer's sample label.
    add("01a", cards / "opening.mp4", 3)
    for suffix, name, length, y, h in [
        ("b", "wanted", 4, 110, 130),
        ("c", "sold", 4, 210, 83),
        ("d", "match", 4, 360, 105),
    ]:
        segments.append(
            focus("01" + suffix, stills / f"v2-maria-{name}.png", length, y, h, still=True)
        )
    scene_files.append(segments[2])
    for num, name, duration in [(2, "scale", 8), (3, "thesis", 8), (4, "title", 7)]:
        scene_files.append(add(f"{num:02}", cards / f"{name}.mp4", duration))
    scene_files.append(
        add("05", scenes / "v2-run.mp4", 12, crop=(412, 0, 1028, 578), lower="Step 1 · Fan out")
    )
    # Real child footage stays at normal speed; editorial cuts select actual stages.
    start = beats["v2-run-trace-live"]["seconds"]
    validated = beats["v2-run-trace-comparing_previous_night"]["seconds"]
    done = beats["v2-run-trace-succeeded"]["seconds"]
    scene_files.append(
        focus(
            "06",
            scenes / "v2-run.mp4",
            12,
            295,
            95,
            offset=max(start, done - 8),
            x=250,
            width=960,
            badge_x=1040,
        )
    )
    segments.append(scene_files[-1])
    scene_files.append(
        focus(
            "07a",
            scenes / "v2-run.mp4",
            7,
            385,
            90,
            offset=done + 2,
            x=250,
            width=960,
            badge_x=1040,
        )
    )
    segments.append(scene_files[-1])
    segments.append(focus("07b", stills / "v2-maria-score.png", 8, 460, 135, still=True))
    scene_files.append(
        focus(
            "08a",
            scenes / "v2-run.mp4",
            6,
            470,
            110,
            offset=max(validated, done - 5),
            x=250,
            width=960,
            badge_x=1040,
        )
    )
    segments.append(scene_files[-1])
    segments.append(
        focus("08b", scenes / "v2-run.mp4", 5, 150, 60, offset=done, x=250, width=960, badge_x=1040)
    )
    # The HTML lower-thirds are rendered once and composited only into the edit border.
    for item, chapter, offset in [
        ("06", 2, 0),
        ("07a", 3, 0),
        ("07b", 3, 7),
        ("08a", 4, 0),
        ("08b", 4, 6),
    ]:
        path = WORK / (item + ".mp4")
        temp = WORK / (item + "-titled.mp4")
        run(
            [
                "-i",
                str(path),
                "-ss",
                str(offset),
                "-i",
                str(cards / f"lower-{chapter}.mp4"),
                "-filter_complex",
                "[1:v]chromakey=0xFF00FF:0.25:0.12[title];[0:v][title]overlay=0:0:shortest=1,format=yuv420p[out]",
                "-map",
                "[out]",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                str(temp),
            ]
        )
        temp.replace(path)
    scene_files.append(add("09", cards / "skip.mp4", 4))
    # Genuine drawer details, with the actual sample badge retained in the edit border.
    scene_files.append(focus("10a", stills / "v2-maria-match.png", 10, 360, 105, still=True))
    segments.append(scene_files[-1])
    segments.append(focus("10b", stills / "v2-maria-trade.png", 4, 115, 100, still=True))
    segments.append(focus("10c", stills / "v2-maria-sms.png", 12, 735, 110, still=True))
    scene_files.append(add("11a", scenes / "v2-approve.mp4", 5, crop=(412, 0, 1028, 578)))
    add("11b", scenes / "v2-ready.mp4", 7, crop=("240+172*min(t/7,1)", 0, 1028, 578))
    scene_files.append(add("12a", cards / "matched.mp4", 6))
    add("12b", cards / "gross.mp4", 6)
    scene_files.append(add("13", cards / "architecture.mp4", 12))
    scene_files.append(add("14", cards / "end.mp4", 11))
    listing = WORK / "concat.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in segments))
    finish()


def finish():
    listing = WORK / "concat.txt"
    raw = VIDEO / "salesdesk-v2-nosubs.mp4"
    run(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(raw),
        ]
    )
    # Reuse existing ASS style, with raised captions for chapter lower-thirds.
    header = (VIDEO / "subtitles.ass").read_text().split("[Events]")[0]
    events = [
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def stamp(t):
        h, m, s, ms = map(int, re.split("[:,]", t))
        return f"{h}:{m:02}:{s:02}.{ms // 10:02}"

    for cue in re.split(r"\n\s*\n", (VIDEO / "subtitles-v2.srt").read_text().strip()):
        lines = cue.splitlines()
        a, b = lines[1].split(" --> ")
        sec = sum(v * k for v, k in zip(map(int, re.split("[:,]", a)), [3600, 60, 1, 0.001]))
        margin = 180 if 38 <= sec < 88 else 150 if sec >= 154 else 56
        text = "\\N".join(lines[2:])
        # SMS shot has no captions from 1:46 through the end of its read hold.
        if 106 <= sec < 118:
            continue
        events.append(f"Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,{margin},,{text}")
    ass = VIDEO / "subtitles-v2.ass"
    ass.write_text(header + "\n".join(events) + "\n")
    final = VIDEO / "salesdesk-v2.mp4"
    run(
        [
            "-i",
            str(raw),
            "-vf",
            f"subtitles='{ass}':fontsdir='{VIDEO / 'fonts'}'",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-threads",
            "4",
            "-movflags",
            "+faststart",
            str(final),
        ]
    )
    for i, moment in enumerate([13, 20, 27, 35, 46, 60, 67, 82, 90, 100, 125, 139, 151, 161]):
        frame = WORK / f"review-{i + 1:02}.png"
        font = VIDEO / "fonts/Inter-SemiBold.ttf"
        (VIDEO / "_review").mkdir(exist_ok=True)
        run(
            [
                "-ss",
                str(moment),
                "-i",
                str(final),
                "-frames:v",
                "1",
                str(VIDEO / "_review" / f"v2-scene-{i + 1:02}.png"),
            ]
        )
        run(
            [
                "-ss",
                str(moment),
                "-i",
                str(final),
                "-vf",
                f"scale=480:270,drawtext=fontfile='{font}':text='Scene {i + 1}':fontcolor=white:fontsize=18:box=1:boxcolor=0x142e34:x=w-tw-8:y=h-th-8",
                "-frames:v",
                "1",
                str(frame),
            ]
        )
    (VIDEO / "_review").mkdir(exist_ok=True)
    run(
        [
            "-framerate",
            "1",
            "-start_number",
            "1",
            "-i",
            str(WORK / "review-%02d.png"),
            "-vf",
            "tile=4x4:nb_frames=14:padding=8:margin=8:color=0x142e34",
            "-frames:v",
            "1",
            str(VIDEO / "_review/v2-contact.png"),
        ]
    )
    checks = {}
    for path in (raw, final):
        info = probe(path)
        v = info["streams"][0]
        assert v["width"] == 1920 and v["height"] == 1080 and v["r_frame_rate"] == "30/1"
        assert abs(float(info["format"]["duration"]) - 165) < 0.1
        assert len(info["streams"]) == 1
        checks[path.name] = {
            "duration": info["format"]["duration"],
            "bytes": info["format"]["size"],
            "video": "1920x1080 30fps H.264",
            "audio": "none",
        }
    (VIDEO / "v2-export-check.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finish-only", action="store_true")
    args = parser.parse_args()
    finish() if args.finish_only else main()
