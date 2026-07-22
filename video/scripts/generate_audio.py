"""Create narration, captions, an original score, and the final 48 kHz mix."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
import numpy as np
from pydub import AudioSegment
from scipy.io import wavfile
from scipy.signal import butter, sosfilt


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
PRODUCTION = VIDEO / "production.json"
DEFAULT_VOICE = "en-IN-PrabhatNeural"
SAMPLE_RATE = 48_000


def run(command: list[str]) -> None:
    print(" ".join(command))
    subprocess.run(command, check=True)


def probe_duration(path: Path) -> float:
    output = subprocess.check_output(
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
    return float(output.strip())


def parse_timestamp(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def format_srt(value: float) -> str:
    value = max(0.0, value)
    millis = int(round(value * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def format_vtt(value: float) -> str:
    return format_srt(value).replace(",", ".")


def parse_edge_subtitles(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8-sig")
    # Communicate.save writes one JSON boundary record per line. The CLI can
    # emit SRT-like blocks, so accept both forms for reproducibility.
    if text.lstrip().startswith("{"):
        cues: list[tuple[float, float, str]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("type") != "SentenceBoundary" or not record.get("text"):
                continue
            start = float(record["offset"]) / 10_000_000
            end = start + float(record["duration"]) / 10_000_000
            cues.append((start, end, str(record["text"])))
        return cues
    blocks = re.split(r"\r?\n\r?\n", text.strip())
    cues: list[tuple[float, float, str]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        time_line = next((line for line in lines if " --> " in line), None)
        if not time_line:
            continue
        start_text, end_text = time_line.split(" --> ", 1)
        caption_lines = lines[lines.index(time_line) + 1 :]
        caption = " ".join(caption_lines).strip()
        if caption:
            cues.append((parse_timestamp(start_text), parse_timestamp(end_text), caption))
    return cues


async def synthesize_section(
    section: dict[str, object], voice: str, output_dir: Path, force: bool
) -> tuple[Path, Path]:
    stem = f"{int(section['start']):03d}_{section['id']}"
    media = output_dir / f"{stem}.mp3"
    subtitles = output_dir / f"{stem}.srt"
    if force or not media.exists() or not subtitles.exists():
        communicate = edge_tts.Communicate(
            str(section["text"]),
            voice,
            # Prabhat's native delivery is deliberately measured; +35% keeps
            # the dense sections inside their windows without trailer pacing.
            rate="+35%",
            volume="+0%",
            pitch="-2Hz",
        )
        await communicate.save(str(media), str(subtitles))
    return media, subtitles


def create_soundtrack(path: Path, duration: float) -> None:
    """Synthesize a deterministic 92 BPM industrial-electronic underscore."""
    sample_count = int(duration * SAMPLE_RATE)
    rng = np.random.default_rng(24001)
    left = np.zeros(sample_count, dtype=np.float32)
    right = np.zeros(sample_count, dtype=np.float32)
    beat = 60.0 / 92.0

    roots = [55.0, 49.0, 52.0, 46.25]
    section_length = duration / len(roots)
    for index, root in enumerate(roots):
        start = int(index * section_length * SAMPLE_RATE)
        end = sample_count if index == len(roots) - 1 else int((index + 1) * section_length * SAMPLE_RATE)
        local_t = np.arange(end - start, dtype=np.float32) / SAMPLE_RATE
        fade = np.ones_like(local_t)
        fade_samples = min(int(3 * SAMPLE_RATE), len(fade) // 3)
        if fade_samples:
            ramp = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
            if index:
                fade[:fade_samples] *= ramp
            if index < len(roots) - 1:
                fade[-fade_samples:] *= ramp[::-1]
        slow = 0.82 + 0.18 * np.sin(2 * np.pi * 0.027 * local_t + index)
        drone_l = (
            np.sin(2 * np.pi * root * local_t)
            + 0.42 * np.sin(2 * np.pi * root * 1.5 * local_t + 0.5)
            + 0.19 * np.sin(2 * np.pi * root * 2.0 * local_t + 1.3)
        )
        drone_r = (
            np.sin(2 * np.pi * root * local_t + 0.08)
            + 0.42 * np.sin(2 * np.pi * root * 1.5 * local_t + 0.67)
            + 0.19 * np.sin(2 * np.pi * root * 2.0 * local_t + 1.1)
        )
        left[start:end] += (0.026 * fade * slow * drone_l).astype(np.float32)
        right[start:end] += (0.026 * fade * slow * drone_r).astype(np.float32)

    # A restrained low pulse on every beat and a tiny filtered texture between beats.
    pulse_length = int(0.42 * SAMPLE_RATE)
    pulse_t = np.arange(pulse_length, dtype=np.float32) / SAMPLE_RATE
    pulse_env = np.exp(-8.5 * pulse_t)
    pulse_wave = np.sin(2 * np.pi * (62.0 - 14.0 * pulse_t) * pulse_t) * pulse_env
    tick_length = int(0.075 * SAMPLE_RATE)
    tick_env = np.exp(-55 * np.arange(tick_length, dtype=np.float32) / SAMPLE_RATE)
    for beat_index, time_s in enumerate(np.arange(0.65, duration, beat)):
        position = int(time_s * SAMPLE_RATE)
        stop = min(sample_count, position + pulse_length)
        body = pulse_wave[: stop - position]
        amplitude = 0.055 if beat_index % 4 == 0 else 0.027
        left[position:stop] += body * amplitude
        right[position:stop] += body * amplitude * 0.94
        if beat_index % 2:
            tick_position = position + int(0.5 * beat * SAMPLE_RATE)
            tick_stop = min(sample_count, tick_position + tick_length)
            texture = rng.normal(0, 1, tick_stop - tick_position).astype(np.float32)
            texture *= tick_env[: tick_stop - tick_position] * 0.006
            left[tick_position:tick_stop] += texture
            right[tick_position:tick_stop] += texture[::-1]

    # Air movement, heavily low-passed so it reads as environment rather than hiss.
    noise = rng.normal(0, 1, sample_count).astype(np.float32)
    sos = butter(3, 420 / (SAMPLE_RATE / 2), btype="low", output="sos")
    air = sosfilt(sos, noise).astype(np.float32)
    air /= max(float(np.max(np.abs(air))), 1e-6)
    left += air * 0.0055
    right += np.roll(air, int(0.013 * SAMPLE_RATE)) * 0.0052

    # Three honest UI accents: evidence, predictive case, human approval.
    accents = [(2.0, 392.0, 0.050), (39.5, 659.3, 0.045), (137.1, 523.3, 0.043)]
    for time_s, frequency, amplitude in accents:
        length = int(0.75 * SAMPLE_RATE)
        local_t = np.arange(length, dtype=np.float32) / SAMPLE_RATE
        envelope = np.sin(np.pi * np.minimum(local_t / 0.12, 1.0)) * np.exp(-3.5 * local_t)
        chime = (
            np.sin(2 * np.pi * frequency * local_t)
            + 0.45 * np.sin(2 * np.pi * frequency * 1.5 * local_t)
        ) * envelope * amplitude
        position = int(time_s * SAMPLE_RATE)
        stop = min(sample_count, position + length)
        left[position:stop] += chime[: stop - position]
        right[position:stop] += np.roll(chime, 120)[: stop - position]

    # Pull the score down under the dense robustness section.
    duck = np.ones(sample_count, dtype=np.float32)
    for start_s, end_s, gain_db in [(145, 168, -1.8), (168, 194, -3.2), (194, 208, -2.0)]:
        start = int(start_s * SAMPLE_RATE)
        end = int(end_s * SAMPLE_RATE)
        ramp = min(int(0.7 * SAMPLE_RATE), (end - start) // 3)
        gain = 10 ** (gain_db / 20)
        duck[start:end] = gain
        if ramp:
            duck[start - ramp : start] = np.linspace(1.0, gain, ramp, dtype=np.float32)
            duck[end : min(sample_count, end + ramp)] = np.linspace(
                gain, 1.0, min(sample_count, end + ramp) - end, dtype=np.float32
            )
    left *= duck
    right *= duck

    stereo = np.column_stack((left, right))
    peak = max(float(np.max(np.abs(stereo))), 1e-6)
    stereo *= min(1.0, 0.30 / peak)
    wavfile.write(path, SAMPLE_RATE, (stereo * 32767).astype(np.int16))


async def generate(args: argparse.Namespace) -> None:
    production = json.loads(PRODUCTION.read_text(encoding="utf-8"))
    duration = float(production["duration_seconds"])
    narration_dir = VIDEO / "audio" / "narration"
    narration_dir.mkdir(parents=True, exist_ok=True)
    edit_dir = VIDEO / "edit"
    edit_dir.mkdir(parents=True, exist_ok=True)

    combined_cues: list[tuple[float, float, str]] = []
    master_narration = AudioSegment.silent(duration=int(duration * 1000), frame_rate=SAMPLE_RATE).set_channels(2)
    report: list[dict[str, object]] = []

    for section in production["narration"]:
        media, raw_subtitles = await synthesize_section(section, args.voice, narration_dir, args.force)
        raw_duration = probe_duration(media)
        window = float(section["end"]) - float(section["start"])
        leading_pad = 0.42 if float(section["start"]) == 0 else 0.30
        target_max = window - leading_pad - 0.40
        speed = max(1.0, raw_duration / target_max)
        if speed > 1.18:
            raise RuntimeError(
                f"Narration section {section['id']} needs {speed:.2f}x speed; revise copy instead."
            )
        processed = narration_dir / f"{int(section['start']):03d}_{section['id']}.wav"
        filters = ["highpass=f=70", "acompressor=threshold=-20dB:ratio=2.5:attack=12:release=120"]
        if speed > 1.0005:
            filters.insert(0, f"atempo={speed:.6f}")
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=7")
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "warning",
                "-i",
                str(media),
                "-af",
                ",".join(filters),
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                "2",
                str(processed),
            ]
        )
        processed_duration = probe_duration(processed)
        clip = AudioSegment.from_file(processed).set_frame_rate(SAMPLE_RATE).set_channels(2)
        position_ms = int((float(section["start"]) + leading_pad) * 1000)
        master_narration = master_narration.overlay(clip, position=position_ms)

        for cue_start, cue_end, caption in parse_edge_subtitles(raw_subtitles):
            start = float(section["start"]) + leading_pad + cue_start / speed
            end = float(section["start"]) + leading_pad + cue_end / speed
            combined_cues.append((start, min(end, float(section["end"]) - 0.12), caption))
        report.append(
            {
                "id": section["id"],
                "window_seconds": window,
                "raw_seconds": round(raw_duration, 3),
                "speed_factor": round(speed, 6),
                "processed_seconds": round(processed_duration, 3),
                "start_seconds": float(section["start"]) + leading_pad,
            }
        )

    narration_master = VIDEO / "audio" / "narration-master.wav"
    master_narration.export(narration_master, format="wav")

    score_path = VIDEO / "audio" / "original-score.wav"
    score_path.parent.mkdir(parents=True, exist_ok=True)
    if args.force or not score_path.exists():
        create_soundtrack(score_path, duration)

    premix = edit_dir / "audio-premix.wav"
    mixed = VIDEO / "audio" / "compound-zero-film-mix.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-i",
            str(narration_master),
            "-i",
            str(score_path),
            "-filter_complex",
            "[1:a]volume=0.62[music];[0:a][music]amix=inputs=2:duration=longest:normalize=0",
            "-t",
            f"{duration:.3f}",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            str(premix),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-i",
            str(premix),
            "-af",
            "loudnorm=I=-16:TP=-1:LRA=10",
            "-t",
            f"{duration:.3f}",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            str(mixed),
        ]
    )

    srt_path = VIDEO / "Compound_Zero_Demo_Captions.srt"
    vtt_path = VIDEO / "Compound_Zero_Demo_Captions.vtt"
    srt_lines: list[str] = []
    vtt_lines = ["WEBVTT", ""]
    for index, (start, end, caption) in enumerate(combined_cues, start=1):
        safe_caption = caption.replace("L-L-M", "LLM").replace("A-P-I", "API").replace("C-C-T-V", "CCTV")
        srt_lines.extend([str(index), f"{format_srt(start)} --> {format_srt(end)}", safe_caption, ""])
        vtt_lines.extend([str(index), f"{format_vtt(start)} --> {format_vtt(end)}", safe_caption, ""])
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")
    (VIDEO / "audio" / "narration-report.json").write_text(
        json.dumps({"voice": args.voice, "sections": report}, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(mixed, edit_dir / "audio-master.wav")
    print(f"Narration: {narration_master}")
    print(f"Original score: {score_path}")
    print(f"Master mix: {mixed}")
    print(f"Captions: {srt_path} and {vtt_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be available on PATH")
    asyncio.run(generate(args))


if __name__ == "__main__":
    main()
