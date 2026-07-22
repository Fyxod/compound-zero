"""Generate paced sentence-level narration, captions, and a clear final mix."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts
from pydub import AudioSegment
from pydub.effects import normalize


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
MANIFEST = VIDEO / "live_production.json"
SAMPLE_RATE = 48_000


def duration_seconds(path: Path) -> float:
    value = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(value.strip())


def stamp(seconds: float, *, vtt: bool = False) -> str:
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    whole, millis = divmod(millis, 1000)
    separator = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{whole:02d}{separator}{millis:03d}"


async def synthesize(text: str, path: Path, voice: str, rate: str) -> None:
    communicator = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        volume="+0%",
        pitch="-1Hz",
    )
    await communicator.save(str(path))


async def build(force: bool) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    duration = float(manifest["duration_seconds"])
    voice = str(manifest["voice"])
    rate = str(manifest["voice_rate"])
    work = VIDEO / "live_capture" / "audio"
    work.mkdir(parents=True, exist_ok=True)

    narration = AudioSegment.silent(
        duration=round(duration * 1000), frame_rate=SAMPLE_RATE
    ).set_channels(2)
    cues: list[tuple[float, float, str]] = []
    entries = list(manifest["narration"])

    previous_end = -1.0
    for index, cue in enumerate(entries):
        requested_start = float(cue["start"])
        text = str(cue["text"])
        mp3 = work / f"cue-{index + 1:02d}.mp3"
        if force or not mp3.exists():
            await synthesize(text, mp3, voice, rate)
        clip = AudioSegment.from_file(mp3).set_frame_rate(SAMPLE_RATE).set_channels(2)
        clip = normalize(clip, headroom=1.4).fade_in(45).fade_out(90)
        measured = duration_seconds(mp3)
        # Preserve every sentence at its natural duration.  The requested starts
        # establish the editorial rhythm, but later cues move forward when the
        # previous phrase needs more room.  This prevents clipped words and the
        # unnatural mid-thought breaks that a rigid cue grid creates.
        start = max(requested_start, previous_end + 0.38)
        end = start + measured
        if end > duration - 0.20:
            raise RuntimeError(
                f"Cue {index + 1} exceeds the {duration:.1f}s programme: "
                f"{end:.2f}s > {duration - 0.20:.2f}s"
            )
        narration = narration.overlay(clip, position=round(start * 1000))
        cues.append((start, end, text))
        previous_end = end

    narration_path = work / "live-narration.wav"
    narration.export(narration_path, format="wav")

    score_path = VIDEO / "audio" / "original-score.wav"
    if score_path.exists():
        score = (
            AudioSegment.from_file(score_path)
            .set_frame_rate(SAMPLE_RATE)
            .set_channels(2)[: round(duration * 1000)]
            - 10.0
        )
    else:
        score = AudioSegment.silent(
            duration=round(duration * 1000), frame_rate=SAMPLE_RATE
        ).set_channels(2)
    premix = score.overlay(narration)
    premix_path = work / "live-premix.wav"
    premix.export(premix_path, format="wav")
    final_mix = work / "live-mix.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-i",
            str(premix_path),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=8",
            "-ar",
            str(SAMPLE_RATE),
            str(final_mix),
        ],
        check=True,
    )

    srt_lines: list[str] = []
    vtt_lines = ["WEBVTT", ""]
    for number, (start, end, text) in enumerate(cues, start=1):
        srt_lines.extend(
            [str(number), f"{stamp(start)} --> {stamp(end)}", text, ""]
        )
        vtt_lines.extend([f"{stamp(start, vtt=True)} --> {stamp(end, vtt=True)}", text, ""])
    (VIDEO / "Compound_Zero_Live_Demo_Captions.srt").write_text(
        "\n".join(srt_lines), encoding="utf-8"
    )
    (VIDEO / "Compound_Zero_Live_Demo_Captions.vtt").write_text(
        "\n".join(vtt_lines), encoding="utf-8"
    )
    report = {
        "voice": voice,
        "rate": rate,
        "cue_count": len(cues),
        "duration_seconds": duration,
        "mix": str(final_mix),
        "explicit_sentence_level_timing": True,
        "minimum_inter_sentence_pause_seconds": 0.38,
        "last_narration_end_seconds": round(previous_end, 3),
    }
    (work / "live-audio-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(build(args.force))


if __name__ == "__main__":
    main()
