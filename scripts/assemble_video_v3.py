"""Assemble the exact 165-second v3 edit from real takes and HTML motion cards."""

# ruff: noqa: E501
import argparse
import json
import re
import subprocess

from scripts.assemble_demo_video import FFMPEG, ROOT, VIDEO, probe

WORK = ROOT / ".local/video-prep/edit-v3"


def run(args):
    subprocess.run([FFMPEG, "-v", "error", "-y", *args], check=True)


def encode(name, source, duration, offset=0, still=False, lower=None, fade=False):
    out = WORK / (name + ".mp4")
    inputs = ["-loop", "1", "-framerate", "30"] if still else ["-ss", str(offset)]
    vf = "fps=30,"
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
            str(VIDEO / "cards-v3" / f"lower-{index}.mp4"),
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


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((VIDEO / "scene-manifest-v3.json").read_text())
    beats = {b["scene"] + "-" + b["beat"]: b for b in manifest["beats"]}
    cards = VIDEO / "cards-v3"
    scenes = VIDEO / "scenes"
    stills = VIDEO / "stills"
    segments = []

    def add(n, source, duration, **kw):
        path = encode(n, source, duration, **kw)
        segments.append(path)
        return path

    # Whole platform frames: no editorial detail crops or transplanted badges.
    add("01a", cards / "opening.mp4", 3)
    add("01b", scenes / "v3-maria.mp4", 12, offset=2)
    add("02", cards / "scale.mp4", 8)
    add("03a", cards / "thesis.mp4", 8)
    add("03b", cards / "promise.mp4", 4)
    add("04", cards / "title.mp4", 3)
    add("05", cards / "fanout.mp4", 12, lower="Step 1 · Fan out")
    add("06a", scenes / "v3-run.mp4", 3, offset=5, lower="Step 1 · Fan out")
    start = beats["v3-run-trace-live"]["seconds"]
    done = beats["v3-run-trace-succeeded"]["seconds"]
    add(
        "06b",
        scenes / "v3-run.mp4",
        12,
        offset=max(start, done - 8),
        lower="Step 2 · Find who's slipping",
    )
    add("07a", scenes / "v3-run.mp4", 7, offset=done + 1, lower="Step 3 · Find the right car")
    add("07b", stills / "v3-maria-score.png", 8, still=True, lower="Step 3 · Find the right car")
    add(
        "08",
        scenes / "v3-run.mp4",
        11,
        offset=max(start, done - 5),
        lower="Step 4 · Write the brief",
    )
    add("09", cards / "skip.mp4", 4)
    add("10", scenes / "v3-maria.mp4", 26)
    add("11a", scenes / "v3-approve.mp4", 5)
    add("11b", scenes / "v3-ready.mp4", 7)
    add("12a", cards / "matched.mp4", 6)
    add("12b", cards / "gross.mp4", 6)
    add("13", cards / "architecture.mp4", 12)
    add("14", cards / "end.mp4", 8)
    listing = WORK / "concat.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in segments))
    finish()


def finish():
    listing = WORK / "concat.txt"
    raw = VIDEO / "salesdesk-v3-nosubs.mp4"
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

    for cue in re.split(r"\n\s*\n", (VIDEO / "subtitles-v3.srt").read_text().strip()):
        lines = cue.splitlines()
        a, b = lines[1].split(" --> ")
        sec = sum(v * k for v, k in zip(map(int, re.split("[:,]", a)), [3600, 60, 1, 0.001]))
        margin = 56
        text = "\\N".join(lines[2:])
        # SMS shot has no captions from 1:46 through the end of its read hold.
        if 109 <= sec < 121:
            continue
        events.append(f"Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,{margin},,{text}")
    ass = VIDEO / "subtitles-v3.ass"
    ass.write_text(header + "\n".join(events) + "\n")
    final = VIDEO / "salesdesk-v3.mp4"
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
    for i, moment in enumerate([13, 20, 27, 36, 46, 61, 70, 85, 93, 103, 128, 142, 154, 162]):
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
                str(VIDEO / "_review" / f"v3-scene-{i + 1:02}.png"),
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
            str(VIDEO / "_review/v3-contact.png"),
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
    (VIDEO / "v3-export-check.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finish-only", action="store_true")
    args = parser.parse_args()
    finish() if args.finish_only else main()
