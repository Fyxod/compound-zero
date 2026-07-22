"""Decode, inspect, measure, and frame-sheet the finished Compound Zero film."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from skimage.metrics import structural_similarity


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
EXPORTS = VIDEO / "exports"
QA = VIDEO / "qa"


def probe(path: Path) -> dict[str, object]:
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
    )


def decode(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "NUL"],
        check=True,
    )


def audio_loudness(path: Path) -> dict[str, float | None]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
    )
    matches_i = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", result.stderr)
    matches_peak = re.findall(r"Peak:\s+(-?\d+(?:\.\d+)?) dBFS", result.stderr)
    return {
        "integrated_lufs": float(matches_i[-1]) if matches_i else None,
        "true_peak_dbfs": float(matches_peak[-1]) if matches_peak else None,
    }


def frame_at(path: Path, time_s: float) -> np.ndarray:
    capture = cv2.VideoCapture(str(path))
    capture.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000)
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        raise RuntimeError(f"Could not decode frame at {time_s:.2f}s from {path}")
    return frame


def ocr_disclosure(frame: np.ndarray) -> str:
    height, width = frame.shape[:2]
    crop = frame[int(height * 0.925) : int(height * 0.992), int(width * 0.02) : int(width * 0.58)]
    crop = cv2.resize(crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharpened = cv2.convertScaleAbs(gray, alpha=2.1, beta=-72)
    return pytesseract.image_to_string(sharpened, config="--psm 7").strip()


def create_frame_sheet(path: Path, name: str, times: list[float]) -> tuple[Path, list[dict[str, object]]]:
    target = QA / name
    target.mkdir(parents=True, exist_ok=True)
    thumbs: list[np.ndarray] = []
    records: list[dict[str, object]] = []
    for time_s in times:
        frame = frame_at(path, time_s)
        image_path = target / f"frame-{int(time_s):03d}.jpg"
        cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 94])
        thumb = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumb, (0, 321), (140, 360), (4, 10, 9), -1)
        cv2.putText(thumb, f"{int(time_s) // 60:02d}:{int(time_s) % 60:02d}", (15, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (245, 250, 248), 2, cv2.LINE_AA)
        thumbs.append(thumb)
        records.append({"time_seconds": time_s, "frame": str(image_path.relative_to(ROOT)).replace("\\", "/")})
    columns = 4
    rows = (len(thumbs) + columns - 1) // columns
    sheet = np.full((rows * 360, columns * 640, 3), (6, 12, 11), dtype=np.uint8)
    for index, thumb in enumerate(thumbs):
        row, column = divmod(index, columns)
        sheet[row * 360 : (row + 1) * 360, column * 640 : (column + 1) * 640] = thumb
    sheet_path = QA / f"{name}-frame-sheet.jpg"
    cv2.imwrite(str(sheet_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 93])
    return sheet_path, records


def stream_map(metadata: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    streams = metadata.get("streams", [])
    video = next(stream for stream in streams if stream.get("codec_type") == "video")
    audio = next(stream for stream in streams if stream.get("codec_type") == "audio")
    return video, audio


def compare_compact(master: Path, compact: Path, times: list[float]) -> dict[str, object]:
    scores: list[float] = []
    ocr_results: list[dict[str, object]] = []
    for time_s in times:
        full = frame_at(master, time_s)
        small = frame_at(compact, time_s)
        full = cv2.resize(full, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA)
        full_gray = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        score = structural_similarity(full_gray, small_gray, data_range=255)
        scores.append(float(score))
        if time_s >= 12:
            text = ocr_disclosure(small)
            ocr_results.append(
                {
                    "time_seconds": time_s,
                    "text": text,
                    "passed": "SIMULATED" in text.upper() and "PROTOTYPE" in text.upper(),
                }
            )
    mean_ssim = float(np.mean(scores))
    accepted = mean_ssim >= 0.88 and all(item["passed"] for item in ocr_results)
    return {
        "mean_luma_ssim": round(mean_ssim, 6),
        "minimum_luma_ssim": round(float(min(scores)), 6),
        "disclosure_ocr": ocr_results,
        "accepted_for_form_upload": accepted,
        "decision": "Readable under-50 MiB companion" if accepted else "Use the 1440p Drive master; compact copy is not accepted",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", type=Path, default=EXPORTS / "compound-zero-demo-drive-1440p.mp4")
    parser.add_argument("--compact", type=Path, default=EXPORTS / "compound-zero-demo-under-50mb.mp4")
    parser.add_argument("--skip-decode", action="store_true")
    args = parser.parse_args()

    if not args.master.exists():
        raise FileNotFoundError(args.master)
    QA.mkdir(parents=True, exist_ok=True)
    metadata = probe(args.master)
    video, audio = stream_map(metadata)
    duration = float(metadata["format"]["duration"])
    size_bytes = int(metadata["format"]["size"])
    checks = {
        "duration_exact_220s": abs(duration - 220.0) <= 0.05,
        "video_h264": video.get("codec_name") == "h264",
        "resolution_2560x1440": [video.get("width"), video.get("height")] == [2560, 1440],
        "frame_rate_30fps": video.get("r_frame_rate") in {"30/1", "60/2"},
        "audio_aac": audio.get("codec_name") == "aac",
        "audio_48khz_stereo": audio.get("sample_rate") == "48000" and audio.get("channels") == 2,
    }
    if not args.skip_decode:
        decode(args.master)
        checks["full_decode"] = True
    loudness = audio_loudness(args.master)
    checks["integrated_loudness_near_minus16"] = loudness["integrated_lufs"] is not None and -18 <= float(loudness["integrated_lufs"]) <= -14
    checks["true_peak_below_minus0_5"] = loudness["true_peak_dbfs"] is not None and float(loudness["true_peak_dbfs"]) <= -0.5

    disclosure_checks = []
    for time_s in [13, 61, 140, 188, 215, 218]:
        text = ocr_disclosure(frame_at(args.master, time_s))
        passed = "SIMULATED" in text.upper() and "PROTOTYPE" in text.upper()
        disclosure_checks.append({"time_seconds": time_s, "text": text, "passed": passed})
    checks["persistent_disclosure_ocr"] = all(item["passed"] for item in disclosure_checks)

    frame_times = [2, 6, 10, 13, 26, 35, 43, 53, 61, 69, 78, 87, 101, 112, 119, 131, 140, 147, 153, 163, 170, 177, 188, 196, 201, 206, 209, 213, 215, 218]
    sheet, frame_records = create_frame_sheet(args.master, "master", frame_times)
    compact_report = None
    if args.compact.exists():
        compact_meta = probe(args.compact)
        compact_size = int(compact_meta["format"]["size"])
        compact_report = {
            "path": str(args.compact.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": compact_size,
            "size_mib": round(compact_size / 1024 / 1024, 3),
            "under_50_mib": compact_size < 50 * 1024 * 1024,
            **compare_compact(args.master, args.compact, [13, 43, 87, 153, 188, 215, 218]),
        }
        if not args.skip_decode:
            decode(args.compact)
            compact_report["full_decode"] = True

    captions = VIDEO / "Compound_Zero_Demo_Captions.srt"
    caption_text = captions.read_text(encoding="utf-8") if captions.exists() else ""
    checks["captions_present"] = bool(caption_text.strip())
    checks["truth_terms_present"] = all(term in caption_text for term in ["simulated", "process drift", "shadow validation"])

    report = {
        "master": {
            "path": str(args.master.relative_to(ROOT)).replace("\\", "/"),
            "duration_seconds": duration,
            "size_bytes": size_bytes,
            "size_mib": round(size_bytes / 1024 / 1024, 3),
            "video": video,
            "audio": audio,
            "loudness": loudness,
        },
        "checks": checks,
        "all_required_checks_passed": all(checks.values()),
        "persistent_disclosure_ocr": disclosure_checks,
        "frame_sheet": str(sheet.relative_to(ROOT)).replace("\\", "/"),
        "frames": frame_records,
        "compact": compact_report,
        "claim_boundary": "All product and benchmark data shown are simulated. No field validation, certification, autonomous actuation or production-safety guarantee is claimed.",
    }
    report_path = QA / "video-qa-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_path = QA / "video-qa-summary.md"
    lines = [
        "# Compound Zero video QA",
        "",
        f"- Master: `{report['master']['path']}`",
        f"- Duration: `{duration:.3f} s`",
        f"- Size: `{report['master']['size_mib']:.2f} MiB`",
        f"- Integrated loudness: `{loudness['integrated_lufs']} LUFS`",
        f"- True peak: `{loudness['true_peak_dbfs']} dBFS`",
        f"- Required checks: `{'PASS' if report['all_required_checks_passed'] else 'REVIEW'}`",
        f"- Frame sheet: `{report['frame_sheet']}`",
    ]
    if compact_report:
        lines.extend(
            [
                f"- Compact size: `{compact_report['size_mib']:.2f} MiB`",
                f"- Compact decision: `{compact_report['decision']}`",
            ]
        )
    lines.extend(["", report["claim_boundary"], ""])
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "frame_sheet": str(sheet), "passed": report["all_required_checks_passed"]}, indent=2))


if __name__ == "__main__":
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be available on PATH")
    main()
