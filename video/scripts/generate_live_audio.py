"""Generate paced sentence-level narration, captions, and a clear final mix."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts
from pydub import AudioSegment
from pydub.effects import normalize
from pydub.silence import detect_nonsilent


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
MANIFEST = VIDEO / "live_production.json"
SAMPLE_RATE = 48_000


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


def split_sentences(text: str) -> list[str]:
    """Split prose where the narrator should take an editorially controlled pause."""
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def trim_tts_edges(clip: AudioSegment) -> AudioSegment:
    """Remove Edge TTS lead/trail padding without touching silence inside a sentence."""
    ranges = detect_nonsilent(clip, min_silence_len=80, silence_thresh=-44)
    if not ranges:
        return clip
    start = max(0, ranges[0][0] - 55)
    end = min(len(clip), ranges[-1][1] + 75)
    return clip[start:end]


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
    caption_cues: list[tuple[float, float, str]] = []
    entries = list(manifest["narration"])

    previous_end = -1.0
    realised_pauses: list[float] = []
    for index, cue in enumerate(entries):
        requested_start = float(cue["start"])
        text = str(cue["text"])
        sentences = split_sentences(text)
        sentence_pauses = [float(value) for value in cue.get("sentence_pauses", [])]
        if len(sentence_pauses) != max(0, len(sentences) - 1):
            raise ValueError(
                f"Cue {index + 1} needs {len(sentences) - 1} sentence pauses, "
                f"got {len(sentence_pauses)}"
            )

        parts: list[AudioSegment] = []
        for sentence_index, sentence in enumerate(sentences):
            mp3 = work / f"cue-{index + 1:02d}-sentence-{sentence_index + 1:02d}.mp3"
            if force or not mp3.exists():
                await synthesize(sentence, mp3, voice, rate)
            sentence_clip = (
                AudioSegment.from_file(mp3)
                .set_frame_rate(SAMPLE_RATE)
                .set_channels(2)
            )
            sentence_clip = trim_tts_edges(sentence_clip)
            sentence_clip = normalize(sentence_clip, headroom=1.4).fade_in(35).fade_out(55)
            parts.append(sentence_clip)

        clip = AudioSegment.empty()
        for sentence_index, sentence_clip in enumerate(parts):
            clip += sentence_clip
            if sentence_index < len(sentence_pauses):
                pause = sentence_pauses[sentence_index]
                clip += AudioSegment.silent(
                    duration=round(pause * 1000), frame_rate=SAMPLE_RATE
                ).set_channels(2)

        gap_before = float(cue.get("gap_before", 0.42))
        if previous_end < 0:
            start = requested_start
        elif bool(cue.get("anchor", False)):
            start = max(requested_start, previous_end + gap_before)
        else:
            start = previous_end + gap_before
        end = start + len(clip) / 1000.0
        if end > duration - 0.20:
            raise RuntimeError(
                f"Cue {index + 1} exceeds the {duration:.1f}s programme: "
                f"{end:.2f}s > {duration - 0.20:.2f}s"
            )
        narration = narration.overlay(clip, position=round(start * 1000))
        cues.append((start, end, text))
        sentence_offset = 0.0
        for sentence_index, (sentence, sentence_clip) in enumerate(
            zip(sentences, parts, strict=True)
        ):
            sentence_start = start + sentence_offset
            sentence_end = sentence_start + len(sentence_clip) / 1000.0
            caption_cues.append((sentence_start, sentence_end, sentence))
            sentence_offset += len(sentence_clip) / 1000.0
            if sentence_index < len(sentence_pauses):
                sentence_offset += sentence_pauses[sentence_index]
        if previous_end >= 0:
            realised_pauses.append(start - previous_end)
        realised_pauses.extend(sentence_pauses)
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
    for number, (start, end, text) in enumerate(caption_cues, start=1):
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
        "narration_group_count": len(cues),
        "caption_cue_count": len(caption_cues),
        "duration_seconds": duration,
        "mix": str(final_mix),
        "explicit_sentence_level_timing": True,
        "pause_policy": "semantic variable cadence",
        "minimum_pause_seconds": round(min(realised_pauses), 3),
        "maximum_pause_seconds": round(max(realised_pauses), 3),
        "distinct_pause_count": len({round(value, 3) for value in realised_pauses}),
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
