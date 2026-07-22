"""Assemble the browser-driven Compound Zero demo into a 1440p master."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
MANIFEST = VIDEO / "live_production.json"
CAPTIONS = VIDEO / "Compound_Zero_Live_Demo_Captions.srt"
AUDIO = VIDEO / "live_capture" / "audio" / "live-mix.wav"
WORK = VIDEO / "live_capture" / "assembled"
EXPORTS = VIDEO / "exports"
OUTPUT = EXPORTS / "compound-zero-live-demo-drive-1440p.mp4"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def ffmpeg_path(path: Path) -> str:
    """Escape an absolute Windows path for an ffmpeg filter argument."""
    return path.resolve().as_posix().replace(":", r"\:")


def render_scene(scene: dict[str, object], capture: dict[str, object], force: bool) -> Path:
    target = WORK / f"{scene['id']}.mp4"
    if target.exists() and not force:
        return target

    source = ROOT / str(scene["source"])
    if not source.exists():
        raise FileNotFoundError(source)

    crop_x, crop_y, crop_w, crop_h = [int(v) for v in capture["app_crop"]]
    output_w, output_h = [int(v) for v in capture["output"]]
    fps = int(capture["fps"])
    content_h = 1154
    pad_y = (output_h - content_h) // 2
    speed = float(scene["speed"])
    source_duration = float(scene["source_duration"])
    duration = float(scene["duration"])
    # Pad in source time before retiming.  Applying tpad after a setpts slowdown
    # does not reliably extend some NVENC screen-capture streams.  This ordering
    # also supplies a reserve for interrupted containers whose final timestamps
    # overstate their decodable tail by a few frames.
    source_hold_duration = max(0.0, duration / speed - source_duration) + 3.0

    filters = [
        f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}",
        f"scale={output_w}:{content_h}:flags=lanczos",
        f"pad={output_w}:{output_h}:0:{pad_y}:black",
        f"fps={fps}",
        "setsar=1",
    ]
    filters.append(
        f"tpad=stop_mode=clone:stop_duration={source_hold_duration:.6f}"
    )
    if speed != 1.0:
        filters.append(f"setpts={speed:.6f}*PTS")
    # Re-quantize slowed footage to the delivery frame rate, then include one
    # endpoint frame so ffprobe reports the declared duration exactly.
    filters.extend(
        [
            f"fps={fps}",
            f"trim=duration={duration + 1 / fps:.6f}",
            "setpts=PTS-STARTPTS",
        ]
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-ss",
            f"{float(scene['source_start']):.6f}",
            "-t",
            f"{source_duration:.6f}",
            "-i",
            str(source),
            "-an",
            "-vf",
            ",".join(filters),
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-tune",
            "hq",
            "-cq",
            "18",
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            str(target),
        ]
    )
    return target


def assemble(force: bool) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    capture = dict(manifest["capture"])
    scenes = list(manifest["scenes"])
    expected = float(manifest["duration_seconds"])
    actual = sum(float(scene["duration"]) for scene in scenes)
    if abs(actual - expected) > 0.001:
        raise RuntimeError(f"Scene durations total {actual:.3f}s, expected {expected:.3f}s")
    if not CAPTIONS.exists() or not AUDIO.exists():
        raise FileNotFoundError("Generate narration and captions before assembly")

    WORK.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    rendered = [render_scene(scene, capture, force) for scene in scenes]

    concat_list = WORK / "scene-list.txt"
    concat_list.write_text(
        "".join(f"file '{path.resolve().as_posix()}'\n" for path in rendered),
        encoding="utf-8",
    )
    base = WORK / "compound-zero-live-base.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(base),
        ]
    )

    font_bold = ffmpeg_path(Path(r"C:\Windows\Fonts\arialbd.ttf"))
    font_regular = ffmpeg_path(Path(r"C:\Windows\Fonts\arial.ttf"))
    filters = [
        "drawbox=x=0:y=0:w=iw:h=143:color=0x050907@1:t=fill",
        "drawbox=x=0:y=1297:w=iw:h=143:color=0x050907@1:t=fill",
        (
            f"drawtext=fontfile='{font_bold}':text='COMPOUND ZERO':"
            "fontcolor=0xE9FFF7:fontsize=40:x=58:y=24"
        ),
        (
            f"drawtext=fontfile='{font_regular}':"
            "text='SIMULATED DATA  |  WORKING PROTOTYPE  |  NOT FIELD VALIDATION':"
            "fontcolor=0x76E7C5:fontsize=22:x=w-tw-58:y=46"
        ),
    ]

    cursor = 0.0
    for scene in scenes:
        end = cursor + float(scene["duration"])
        label = str(scene["label"]).replace("'", r"\'")
        filters.append(
            f"drawtext=fontfile='{font_regular}':text='{label}':"
            f"fontcolor=0x91AFA5:fontsize=23:x=60:y=91:enable='between(t,{cursor:.3f},{end:.3f})'"
        )
        cursor = end

    filters.extend(
        [
            "drawbox=x=0:y=143:w=iw:h=1154:color=black@0.58:t=fill:enable='between(t,214,220)'",
            (
                f"drawtext=fontfile='{font_bold}':text='CONTEXT.  TIME.  HUMAN CONTROL.':"
                "fontcolor=white:fontsize=54:x=(w-tw)/2:y=610:enable='between(t,214,220)'"
            ),
            (
                f"drawtext=fontfile='{font_regular}':text='COMPOUND ZERO':"
                "fontcolor=0x76E7C5:fontsize=30:x=(w-tw)/2:y=684:enable='between(t,214,220)'"
            ),
            (
                f"subtitles='{ffmpeg_path(CAPTIONS)}':"
                "force_style='FontName=Arial,FontSize=34,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H70000000,BorderStyle=3,BackColour=&H88000000,"
                "Outline=1,Shadow=0,Alignment=2,MarginL=150,MarginR=150,MarginV=38'"
            ),
        ]
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-i",
            str(base),
            "-i",
            str(AUDIO),
            "-filter_complex",
            f"[0:v]{','.join(filters)}[v]",
            "-map",
            "[v]",
            "-map",
            "1:a:0",
            "-t",
            f"{expected:.3f}",
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            "18",
            "-b:v",
            "12M",
            "-maxrate",
            "24M",
            "-bufsize",
            "48M",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            "-metadata",
            "title=Compound Zero - Live Prototype Walkthrough",
            "-metadata",
            "comment=Simulated data; working prototype; not field validation",
            str(OUTPUT),
        ]
    )
    print(OUTPUT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    assemble(args.force)


if __name__ == "__main__":
    main()
