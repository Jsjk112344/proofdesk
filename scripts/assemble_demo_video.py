"""Assemble a 180-second silent rough cut with real app footage, cards and captions.

Editorial crops and zooms operate on entire source frames. No UI values are composited.
Crossfade handles extend into the next slot, preserving every nominal timeline boundary.
"""

# ruff: noqa: E501

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "docs/video"
WORK = ROOT / ".local/video-prep/edit"
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"


def run(args):
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def probe(path):
    return json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
        )
    )


def captions():
    srt = (VIDEO / "subtitles.srt").read_text()
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter,42,&H00FFFFFF,&H00FFFFFF,&H66000000,&H66000000,0,0,0,0,100,100,0,0,3,12,0,2,100,100,56,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def stamp(t):
        h, m, s, ms = map(int, re.split("[:,]", t))
        return f"{h}:{m:02}:{s:02}.{ms // 10:02}"

    events = []
    for cue in re.split(r"\n\s*\n", srt.strip()):
        lines = cue.splitlines()
        begin, end = lines[1].split(" --> ")
        text = "\\N".join(lines[2:]).replace("{", "").replace("}", "")
        events.append(f"Dialogue: 0,{stamp(begin)},{stamp(end)},Default,,0,0,0,,{text}")
    (VIDEO / "subtitles.ass").write_text(header + "\n".join(events) + "\n")
    return len(events)


def main():
    global FFMPEG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default=FFMPEG)
    args = parser.parse_args()
    FFMPEG = shutil.which(args.ffmpeg) or args.ffmpeg
    filters = subprocess.check_output(
        [FFMPEG, "-hide_banner", "-filters"], stderr=subprocess.STDOUT
    ).decode()
    assert " subtitles " in filters, "Use an ffmpeg build with libass."
    WORK.mkdir(parents=True, exist_ok=True)
    # name, nominal length, duration of transition from this segment to the next
    segments = [
        ("scene1", 14, 0.4),
        ("title", 8, 1 / 30),
        ("scene3", 20, 0.4),
        ("jumpcut", 4, 0.4),
        ("scene4", 20, 1 / 30),
        ("scene5", 8, 1 / 30),
        ("scene6", 38, 1 / 30),
        ("scene7", 14, 1 / 30),
        ("scene7-csv", 3, 1 / 30),
        ("scene7-ready", 3, 1 / 30),
        ("scene8", 12, 0.4),
        ("before-after", 14, 0.4),
        ("architecture", 14, 0.4),
        ("end", 8, 0),
    ]
    cards = {
        "title": "01-title-composited",
        "jumpcut": "02-jumpcut",
        "before-after": "03-before-after",
        "end": "05-end",
    }
    paths = []
    for name, duration, handle in segments:
        output = WORK / (name + ".mp4")
        total = duration + handle
        if name in cards:
            inputs = [
                "-loop",
                "1",
                "-framerate",
                "30",
                "-i",
                str(VIDEO / "cards" / (cards[name] + ".png")),
            ]
            vf = "fps=30,setsar=1,format=yuv420p"
        elif name == "architecture":
            listing = WORK / "architecture.ffconcat"
            listing.write_text(
                "ffconcat version 1.0\n"
                + "".join(
                    f"file '{VIDEO / 'cards' / ('04-architecture-build-' + str(i) + '.png')}'\nduration {1 if i < 7 else 8}\n"
                    for i in range(1, 8)
                )
                + f"file '{VIDEO / 'cards' / '04-architecture-build-7.png'}'\n"
            )
            inputs = ["-safe", "0", "-f", "concat", "-i", str(listing)]
            vf = "fps=30,tpad=stop_mode=clone:stop_duration=1,setsar=1,format=yuv420p"
        else:
            inputs = (
                ["-ss", "14", "-i", str(VIDEO / "scenes/scene7.mp4")]
                if name == "scene7-ready"
                else ["-i", str(VIDEO / "scenes" / (name + ".mp4"))]
            )
            z = "1"
            if name == "scene1":
                z = "1+0.15*min(on/420,1)"
            elif name == "scene3":
                z = "if(lt(on,90),1,if(lt(on,102),1+(on-90)/12*.6,if(lt(on,288),1.6,if(lt(on,300),1.6-(on-288)/12*.6,1))))"
            elif name == "scene4":
                z = "if(lt(on,360),1.5,if(lt(on,450),1.5-(on-360)/90*.5,1))"
            elif name == "scene6":
                z = "if(lt(on,30),1+on/30*.4,if(lt(on,870),1.4,if(lt(on,900),1.4-(on-870)/30*.4,1)))"
            elif name == "scene8":
                z = "1.15"
            # Top/right anchoring keeps the app's actual sample-data label in frame,
            # including the sticky label in Maria's drawer. Padding preserves aspect.
            vf = (
                f"fps=30,zoompan=z='{z}':x='iw-iw/zoom':y=0:d=1:s=1728x1080:fps=30,"
                "pad=1920:1080:96:0:color=0x142e34,tpad=stop_mode=clone:stop_duration=1,setsar=1,format=yuv420p"
            )
        if name == "scene1":
            vf += ",fade=t=in:st=0:d=0.4"
        if name == "end":
            vf += ",fade=t=out:st=7.6:d=0.4"
        run(
            [
                *inputs,
                "-vf",
                vf,
                "-t",
                str(total),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "19",
                "-threads",
                "4",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        paths.append(output)
        print(
            json.dumps({"prepared": name, "slot_seconds": duration, "transition_handle": handle}),
            flush=True,
        )
    inputs = []
    for path in paths:
        inputs += ["-i", str(path)]
    graph = []
    previous = "0:v"
    offset = 0
    for i, (_, duration, handle) in enumerate(segments[:-1]):
        offset += duration
        output = f"x{i + 1}"
        graph.append(
            f"[{previous}][{i + 1}:v]xfade=transition=fade:duration={handle}:offset={offset}[{output}]"
        )
        previous = output
    nosubs = VIDEO / "rough-cut-nosubs.mp4"
    run(
        [
            *inputs,
            "-filter_complex_threads",
            "2",
            "-filter_complex",
            ";".join(graph),
            "-map",
            f"[{previous}]",
            "-t",
            "180",
            "-r",
            "30",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "19",
            "-threads",
            "4",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(nosubs),
        ]
    )
    cue_count = captions()
    subs = VIDEO / "rough-cut.mp4"
    run(
        [
            "-i",
            str(nosubs),
            "-vf",
            f"subtitles='{VIDEO / 'subtitles.ass'}':fontsdir='{VIDEO / 'fonts'}'",
            "-t",
            "180",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "19",
            "-threads",
            "4",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(subs),
        ]
    )
    report = {"timeline_seconds": 180, "subtitle_cues": cue_count, "files": {}}
    for path in (nosubs, subs):
        info = probe(path)
        stream = info["streams"][0]
        duration = float(info["format"]["duration"])
        assert duration <= 180.001 and duration >= 179.95, duration
        assert (stream["width"], stream["height"]) == (1920, 1080)
        assert stream["r_frame_rate"] == "30/1"
        assert stream["codec_name"] == "h264"
        assert len(info["streams"]) == 1 and stream["codec_type"] == "video"
        report["files"][path.name] = {
            "duration": duration,
            "codec": "h264",
            "size_bytes": path.stat().st_size,
            "resolution": [1920, 1080],
            "fps": 30,
            "audio": False,
        }
    (VIDEO / "rough-cut-check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
