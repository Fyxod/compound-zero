"""Render the 03:40 Compound Zero product film from validated app captures."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
PRODUCTION_PATH = VIDEO / "production.json"
CAPTURES = VIDEO / "captures"
EDIT = VIDEO / "edit"
EXPORTS = VIDEO / "exports"
W, H = 2560, 1440
FPS = 30

BG = (7, 13, 12)
INK = (238, 245, 242)
MUTED = (159, 177, 170)
SAFE = (120, 233, 194)
WATCH = (235, 180, 88)
CRITICAL = (255, 101, 105)
LINE = (52, 72, 66)

FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
FONT_DISPLAY = Path("C:/Windows/Fonts/bahnschrift.ttf")
FONT_MONO = Path("C:/Windows/Fonts/consola.ttf")
FONT_MONO_BOLD = Path("C:/Windows/Fonts/consolab.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    fallback = FONT_BOLD if "b" in path.stem.lower() else FONT_REGULAR
    return ImageFont.truetype(str(path if path.exists() else fallback), size=size)


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, minimum: int = 30) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > minimum:
        candidate = font(FONT_DISPLAY, size)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
        size -= 2
    return font(FONT_DISPLAY, minimum)


PreparedOverlay = tuple[int, int, np.ndarray, np.ndarray]


def prepare_overlay(overlay: Image.Image) -> PreparedOverlay:
    """Trim a full-canvas RGBA graphic to its visible bounds once."""
    array = np.asarray(overlay, dtype=np.uint8)
    alpha_plane = array[:, :, 3]
    ys, xs = np.nonzero(alpha_plane)
    if not len(xs):
        return (0, 0, np.zeros((1, 1, 3), dtype=np.float32), np.zeros((1, 1, 1), dtype=np.float32))
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    bgr = array[y0:y1, x0:x1, :3][:, :, ::-1].astype(np.float32)
    alpha = alpha_plane[y0:y1, x0:x1, None].astype(np.float32) / 255.0
    return x0, y0, bgr, alpha


def blend_overlay(frame: np.ndarray, overlay: PreparedOverlay, opacity: float = 1.0) -> np.ndarray:
    x, y, bgr, base_alpha = overlay
    height, width = bgr.shape[:2]
    region = frame[y : y + height, x : x + width]
    alpha = base_alpha if opacity >= 0.999 else base_alpha * opacity
    region[:] = (region.astype(np.float32) * (1.0 - alpha) + bgr * alpha).astype(np.uint8)
    return frame


def tint_for(tone: str) -> tuple[int, int, int]:
    return {
        "safe": SAFE,
        "watch": WATCH,
        "critical": CRITICAL,
        "brand": SAFE,
    }.get(tone, SAFE)


def dim_and_grade(frame: np.ndarray, amount: float = 0.12) -> np.ndarray:
    graded = cv2.convertScaleAbs(frame, alpha=1.0 - amount, beta=-3)
    # Lift green slightly while keeping the native graphite UI intact.
    green = graded[:, :, 1].astype(np.int16) + 2
    graded[:, :, 1] = np.clip(green, 0, 255).astype(np.uint8)
    return graded


def ken_burns(image: np.ndarray, focus: list[float], zoom: list[float], progress: float) -> np.ndarray:
    eased = smoothstep(progress)
    current_zoom = lerp(float(zoom[0]), float(zoom[1]), eased)
    crop_w = max(2, int(W / current_zoom))
    crop_h = max(2, int(H / current_zoom))
    cx = int(float(focus[0]) * W)
    cy = int(float(focus[1]) * H)
    cx = min(W - crop_w // 2, max(crop_w // 2, cx))
    cy = min(H - crop_h // 2, max(crop_h // 2, cy))
    crop = cv2.getRectSubPix(image, (crop_w, crop_h), (float(cx), float(cy)))
    return cv2.resize(crop, (W, H), interpolation=cv2.INTER_CUBIC)


def rounded_tile(frame: np.ndarray, tile: np.ndarray, box: tuple[int, int, int, int], radius: int = 28) -> None:
    x0, y0, x1, y1 = box
    tile = cv2.resize(tile, (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=radius, fill=255)
    alpha = np.asarray(mask, dtype=np.float32)[:, :, None] / 255.0
    region = frame[y0:y1, x0:x1]
    region[:] = (region * (1 - alpha) + tile * alpha).astype(np.uint8)


def create_quad(images: list[np.ndarray], labels: list[str]) -> np.ndarray:
    frame = np.full((H, W, 3), BG[::-1], dtype=np.uint8)
    gradient = np.linspace(0, 15, H, dtype=np.uint8)[:, None]
    frame[:, :, 1] = np.clip(frame[:, :, 1] + gradient, 0, 255)
    foci = [(0.50, 0.37), (0.76, 0.42), (0.30, 0.67), (0.43, 0.78)]
    boxes = [(96, 176, 1260, 690), (1300, 176, 2464, 690), (96, 744, 1260, 1258), (1300, 744, 2464, 1258)]
    for image, focus, box in zip(images, foci, boxes):
        tile = ken_burns(image, list(focus), [1.75, 1.75], 0)
        rounded_tile(frame, tile, box)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_font = font(FONT_MONO_BOLD, 27)
    for box, label in zip(boxes, labels):
        x0, y0, x1, y1 = box
        draw.rounded_rectangle((x0 + 26, y0 + 22, x0 + 292, y0 + 72), radius=14, fill=(9, 18, 16, 226), outline=(*SAFE, 130), width=2)
        draw.text((x0 + 48, y0 + 32), label, font=label_font, fill=(*INK, 255))
    draw.text((96, 74), "FOUR FRAGMENTED WITNESSES", font=font(FONT_MONO_BOLD, 26), fill=(*SAFE, 255))
    return blend_overlay(frame, prepare_overlay(overlay))


def brand_mark(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, accent: tuple[int, int, int]) -> None:
    x, y = center
    r = int(44 * scale)
    width = max(2, int(5 * scale))
    draw.rounded_rectangle((x - r, y - r, x + r, y + r), radius=int(17 * scale), outline=(*accent, 255), width=width)
    draw.ellipse((x - int(14 * scale), y - int(14 * scale), x + int(14 * scale), y + int(14 * scale)), outline=(*accent, 230), width=max(2, int(3 * scale)))
    draw.line((x - int(31 * scale), y, x - int(12 * scale), y), fill=(*accent, 220), width=max(2, int(3 * scale)))
    draw.line((x + int(12 * scale), y, x + int(31 * scale), y), fill=(*accent, 220), width=max(2, int(3 * scale)))


def create_brand_frame(image: np.ndarray, end_card: bool = False) -> np.ndarray:
    pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    pil = pil.filter(ImageFilter.GaussianBlur(radius=8 if end_card else 5))
    dark = Image.new("RGBA", pil.size, (3, 9, 8, 205 if end_card else 188))
    pil = Image.alpha_composite(pil.convert("RGBA"), dark)
    draw = ImageDraw.Draw(pil)
    center_y = 520 if end_card else 555
    brand_mark(draw, (W // 2, center_y - 178), 1.25, SAFE)
    title_font = font(FONT_DISPLAY, 112 if end_card else 102)
    title = "COMPOUND ZERO"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((W - (bbox[2] - bbox[0])) / 2, center_y - 70), title, font=title_font, fill=(*INK, 255))
    tagline = "THE CONTEXT TO SEE RISK. THE TIME TO STOP IT." if end_card else "See the accident before the alarm."
    tag_font = font(FONT_DISPLAY, 42 if end_card else 46)
    bbox = draw.textbbox((0, 0), tagline, font=tag_font)
    draw.text(((W - (bbox[2] - bbox[0])) / 2, center_y + 75), tagline, font=tag_font, fill=(*SAFE, 255))
    if end_card:
        problem = "AI-POWERED INDUSTRIAL SAFETY INTELLIGENCE FOR ZERO-HARM OPERATIONS"
        pfont = font(FONT_MONO_BOLD, 24)
        bbox = draw.textbbox((0, 0), problem, font=pfont)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, center_y + 165), problem, font=pfont, fill=(*MUTED, 255))
        event = "ET AI HACKATHON 2026  ·  SIMULATED PROTOTYPE"
        bbox = draw.textbbox((0, 0), event, font=pfont)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, center_y + 214), event, font=pfont, fill=(*MUTED, 220))
    return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)


def create_callout(shot: dict[str, object]) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    title = str(shot.get("title", ""))
    subtitle = str(shot.get("subtitle", ""))
    accent = tint_for(str(shot.get("tone", "brand")))
    x, y, max_width = 110, 1042, 2240
    title_font = fit_font(draw, title, max_width - 105, 62, 40)
    title_height = draw.textbbox((0, 0), title, font=title_font)[3]
    subtitle_height = 45 if subtitle else 0
    height = max(150, 62 + title_height + subtitle_height)
    draw.rounded_rectangle((x, y, x + max_width, y + height), radius=28, fill=(5, 12, 11, 220), outline=(*LINE, 220), width=2)
    draw.rounded_rectangle((x, y, x + 12, y + height), radius=6, fill=(*accent, 255))
    draw.text((x + 52, y + 26), title, font=title_font, fill=(*INK, 255))
    if subtitle:
        draw.text((x + 54, y + 88), subtitle, font=font(FONT_REGULAR, 30), fill=(*MUTED, 255))
    return overlay


def create_disclosure() -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = "SIMULATED DATA · PROTOTYPE · NOT FIELD VALIDATION"
    mono = font(FONT_MONO_BOLD, 22)
    bbox = draw.textbbox((0, 0), text, font=mono)
    width = bbox[2] - bbox[0] + 74
    x, y = 110, H - 80
    draw.rounded_rectangle((x, y, x + width, y + 48), radius=18, fill=(4, 10, 9, 224), outline=(*SAFE, 105), width=2)
    draw.ellipse((x + 19, y + 18, x + 31, y + 30), fill=(*SAFE, 255))
    draw.text((x + 46, y + 12), text, font=mono, fill=(*INK, 255))
    return overlay


def create_brand_chip() -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y = W - 610, 52
    draw.rounded_rectangle((x, y, W - 92, y + 56), radius=18, fill=(4, 10, 9, 205), outline=(*LINE, 200), width=2)
    brand_mark(draw, (x + 34, y + 28), 0.35, SAFE)
    draw.text((x + 72, y + 15), "COMPOUND ZERO  /  CZ-2026-071", font=font(FONT_MONO_BOLD, 19), fill=(*INK, 242))
    return overlay


def draw_cursor(frame: np.ndarray, shot: dict[str, object], absolute_time: float) -> None:
    cursor = shot.get("cursor")
    if not isinstance(cursor, dict):
        return
    start = float(shot["start"])
    end = float(shot["end"])
    travel_start = start + min(1.0, (end - start) * 0.14)
    travel_end = min(end - 0.6, travel_start + 1.3)
    progress = smoothstep((absolute_time - travel_start) / max(0.1, travel_end - travel_start))
    source = cursor["from"]
    target = cursor["to"]
    x = int(lerp(float(source[0]), float(target[0]), progress) * W)
    y = int(lerp(float(source[1]), float(target[1]), progress) * H)

    click_time = float(cursor.get("click", -100))
    dt = absolute_time - click_time
    if 0 <= dt <= 0.62:
        ripple = smoothstep(dt / 0.62)
        radius = int(20 + 68 * ripple)
        alpha = 1.0 - ripple
        ring = frame.copy()
        cv2.circle(ring, (x, y), radius, SAFE[::-1], 5, cv2.LINE_AA)
        cv2.addWeighted(ring, alpha * 0.72, frame, 1 - alpha * 0.72, 0, frame)
        cv2.circle(frame, (x, y), 14, SAFE[::-1], -1, cv2.LINE_AA)

    points = np.array([[x, y], [x + 15, y + 47], [x + 25, y + 31], [x + 43, y + 49], [x + 52, y + 40], [x + 34, y + 23], [x + 50, y + 16]], dtype=np.int32)
    shadow = points + np.array([4, 5], dtype=np.int32)
    cv2.fillPoly(frame, [shadow], (0, 0, 0), cv2.LINE_AA)
    cv2.polylines(frame, [points], True, (5, 10, 9), 8, cv2.LINE_AA)
    cv2.fillPoly(frame, [points], (244, 250, 248), cv2.LINE_AA)
    cv2.line(frame, (x + 25, y + 31), (x + 43, y + 49), SAFE[::-1], 3, cv2.LINE_AA)


def build_thumbnail(image: np.ndarray, target: Path) -> None:
    frame = cv2.resize(image, (1280, 720), interpolation=cv2.INTER_AREA)
    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).filter(ImageFilter.GaussianBlur(radius=2.2)).convert("RGBA")
    pil = Image.alpha_composite(pil, Image.new("RGBA", pil.size, (2, 8, 7, 150)))
    draw = ImageDraw.Draw(pil)
    brand_mark(draw, (110, 105), 0.78, SAFE)
    draw.text((180, 73), "COMPOUND ZERO", font=font(FONT_DISPLAY, 48), fill=(*INK, 255))
    draw.text((78, 245), "BEFORE", font=font(FONT_DISPLAY, 100), fill=(*INK, 255))
    draw.text((78, 345), "THE ALARM", font=font(FONT_DISPLAY, 100), fill=(*SAFE, 255))
    draw.rounded_rectangle((78, 500, 760, 565), radius=20, fill=(5, 12, 11, 230), outline=(*CRITICAL, 180), width=2)
    draw.text((108, 518), "0 LEGACY ALARMS · COMPOUND RISK FOUND", font=font(FONT_MONO_BOLD, 25), fill=(*INK, 255))
    draw.rounded_rectangle((78, 628, 416, 678), radius=18, fill=(5, 12, 11, 225), outline=(*SAFE, 120), width=2)
    draw.text((104, 640), "SIMULATED PROTOTYPE", font=font(FONT_MONO_BOLD, 22), fill=(*MUTED, 255))
    target.parent.mkdir(parents=True, exist_ok=True)
    pil.convert("RGB").save(target, quality=96)


class Renderer:
    def __init__(self, production: dict[str, object]) -> None:
        self.production = production
        names: set[str] = set()
        for shot in production["shots"]:
            if "image" in shot:
                names.add(shot["image"])
            names.update(shot.get("images", []))
        self.images: dict[str, np.ndarray] = {}
        for name in names:
            path = CAPTURES / name
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(f"Capture missing or unreadable: {path}")
            if image.shape[:2] != (H, W):
                raise ValueError(f"Capture is not normalized to {W}×{H}: {path} -> {image.shape[1]}×{image.shape[0]}")
            self.images[name] = image
        self.callouts = [prepare_overlay(create_callout(shot)) for shot in production["shots"]]
        self.disclosure = prepare_overlay(create_disclosure())
        self.brand_chip = prepare_overlay(create_brand_chip())
        self.quad_cache: dict[int, np.ndarray] = {}
        self.brand_cache: dict[tuple[str, bool], np.ndarray] = {}
        for shot in production["shots"]:
            layout = str(shot.get("layout", "standard"))
            if layout in {"brand", "end"}:
                name = str(shot["image"])
                key = (name, layout == "end")
                if key not in self.brand_cache:
                    self.brand_cache[key] = create_brand_frame(self.images[name], end_card=layout == "end")

    def find_shot(self, time_s: float) -> tuple[int, dict[str, object]]:
        for index, shot in enumerate(self.production["shots"]):
            if float(shot["start"]) <= time_s < float(shot["end"]):
                return index, shot
        return len(self.production["shots"]) - 1, self.production["shots"][-1]

    def render(self, time_s: float) -> tuple[int, np.ndarray]:
        index, shot = self.find_shot(time_s)
        start, end = float(shot["start"]), float(shot["end"])
        progress = (time_s - start) / max(0.001, end - start)
        layout = str(shot.get("layout", "standard"))
        if layout == "quad":
            if index not in self.quad_cache:
                self.quad_cache[index] = create_quad([self.images[name] for name in shot["images"]], shot["labels"])
            frame = self.quad_cache[index].copy()
        else:
            image = self.images[str(shot["image"])]
            if layout in {"brand", "end"}:
                frame = self.brand_cache[(str(shot["image"]), layout == "end")].copy()
            else:
                frame = ken_burns(image, shot.get("focus", [0.5, 0.5]), shot.get("zoom", [1.0, 1.0]), progress)
                frame = dim_and_grade(frame, amount=0.08 if str(shot.get("tone")) == "safe" else 0.12)

        if layout not in {"brand", "end"}:
            fade = min(smoothstep(progress / 0.10), smoothstep((1.0 - progress) / 0.08))
            blend_overlay(frame, self.callouts[index], opacity=fade)
            blend_overlay(frame, self.brand_chip, opacity=min(1.0, fade + 0.2))
        if 12 <= time_s < 216 or layout == "end":
            disclosure_opacity = min(1.0, max(0.0, (time_s - 12) / 0.35))
            blend_overlay(frame, self.disclosure, opacity=disclosure_opacity)
        draw_cursor(frame, shot, time_s)

        # Subtle edge vignette, calculated as two translucent bars for speed.
        cv2.rectangle(frame, (0, 0), (W, 18), (2, 6, 5), -1)
        cv2.rectangle(frame, (0, H - 10), (W, H), (2, 6, 5), -1)
        return index, frame


def encoder_args(choice: str) -> list[str]:
    if choice == "nvenc" or (choice == "auto" and nvenc_works()):
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-profile:v", "high"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"]


def nvenc_works() -> bool:
    probe = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:r=1",
            "-frames:v",
            "1",
            "-c:v",
            "h264_nvenc",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return probe.returncode == 0


def make_previews(renderer: Renderer) -> Path:
    preview_dir = EDIT / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    sample_times = [2, 6, 10, 16, 26, 35, 43, 53, 61, 69, 78, 87, 94, 101, 112, 119, 125, 131, 140, 147, 153, 163, 170, 177, 188, 196, 201, 206, 209, 211, 213, 215, 218]
    thumbs: list[np.ndarray] = []
    for time_s in sample_times:
        _, frame = renderer.render(float(time_s))
        path = preview_dir / f"frame-{time_s:03d}.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 94])
        thumb = cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA)
        cv2.putText(thumb, f"{time_s // 60:02d}:{time_s % 60:02d}", (18, 252), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (245, 250, 248), 2, cv2.LINE_AA)
        thumbs.append(thumb)
    columns = 4
    rows = math.ceil(len(thumbs) / columns)
    montage = np.full((rows * 270, columns * 480, 3), (6, 12, 11), dtype=np.uint8)
    for index, thumb in enumerate(thumbs):
        y, x = divmod(index, columns)
        montage[y * 270 : (y + 1) * 270, x * 480 : (x + 1) * 480] = thumb
    montage_path = EDIT / "preview-montage.jpg"
    cv2.imwrite(str(montage_path), montage, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return montage_path


def render_visual(
    renderer: Renderer,
    output: Path,
    encoder: str,
    *,
    start_frame: int = 0,
) -> None:
    duration = float(renderer.production["duration_seconds"])
    total_frames = int(round(duration * FPS))
    if not 0 <= start_frame < total_frames:
        raise ValueError(f"start_frame must be within [0, {total_frames})")
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "warning",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        *encoder_args(encoder),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:
        raise RuntimeError("Could not open FFmpeg video pipe")
    current_shot = -1
    transition_from: np.ndarray | None = None
    last_frame: np.ndarray | None = None
    try:
        for frame_number in range(start_frame, total_frames):
            time_s = frame_number / FPS
            shot_index, frame = renderer.render(time_s)
            if shot_index != current_shot:
                transition_from = last_frame.copy() if last_frame is not None else None
                current_shot = shot_index
            if transition_from is not None:
                shot_start = float(renderer.production["shots"][shot_index]["start"])
                transition_progress = (time_s - shot_start) / 0.30
                if transition_progress < 1.0:
                    alpha = smoothstep(transition_progress)
                    frame = cv2.addWeighted(transition_from, 1.0 - alpha, frame, alpha, 0)
                else:
                    transition_from = None
            process.stdin.write(frame.tobytes())
            last_frame = frame
            if frame_number % (FPS * 10) == 0:
                print(f"Rendered {time_s:6.1f}s / {duration:.1f}s", flush=True)
    finally:
        process.stdin.close()
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"FFmpeg encoder failed with exit code {return_code}")


def mux_audio(visual: Path, audio: Path, output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-i",
            str(visual),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )


def make_under_50(master: Path, output: Path) -> None:
    passlog = EDIT / "under50-pass"
    common = [
        "-vf",
        "scale=1920:1080:flags=lanczos,fps=30",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-b:v",
        "1450k",
        "-maxrate",
        "1900k",
        "-bufsize",
        "2900k",
        "-passlogfile",
        str(passlog),
    ]
    subprocess.run(["ffmpeg", "-y", "-v", "warning", "-i", str(master), *common, "-pass", "1", "-an", "-f", "null", "NUL"], check=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "warning",
            "-i",
            str(master),
            *common,
            "-pass",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--skip-visual", action="store_true")
    parser.add_argument("--under-50", action="store_true")
    parser.add_argument("--encoder", choices=["auto", "nvenc", "x264"], default="auto")
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be available on PATH")
    production = json.loads(PRODUCTION_PATH.read_text(encoding="utf-8"))
    if production["canvas"] != [W, H] or production["fps"] != FPS:
        raise ValueError("Production manifest canvas or frame rate does not match renderer")
    EDIT.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    renderer = Renderer(production)
    montage = make_previews(renderer)
    thumbnail = EXPORTS / "compound-zero-thumbnail.png"
    build_thumbnail(renderer.images["command-t18.png"], thumbnail)
    shutil.copy2(thumbnail, ROOT / "submission" / "Compound_Zero_Video_Thumbnail.png")
    print(f"Preview montage: {montage}")
    print(f"Thumbnail: {thumbnail}")
    if args.preview_only:
        return

    visual = EDIT / "visual-master-1440p.mp4"
    if not args.skip_visual:
        render_visual(renderer, visual, args.encoder)
    if not visual.exists():
        raise FileNotFoundError(f"Visual master does not exist: {visual}")
    audio = VIDEO / "audio" / "compound-zero-film-mix.wav"
    if not audio.exists():
        raise FileNotFoundError(f"Generate audio first: {audio}")
    master = EXPORTS / "compound-zero-demo-drive-1440p.mp4"
    mux_audio(visual, audio, master, float(production["duration_seconds"]))
    print(f"Drive-quality master: {master}")
    if args.under_50:
        compact = EXPORTS / "compound-zero-demo-under-50mb.mp4"
        make_under_50(master, compact)
        print(f"Under-50 MiB candidate: {compact}")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        print("FFmpeg closed the render pipe early.", file=sys.stderr)
        raise
