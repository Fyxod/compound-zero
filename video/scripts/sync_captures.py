"""Normalize the browser-validated Compound Zero plates for the film timeline."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "submission" / "assets"
DEFAULT_TARGET = ROOT / "video" / "captures"
PRODUCTION = ROOT / "video" / "production.json"
TARGET_SIZE = (2560, 1440)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(source: Path, target: Path) -> dict[str, object]:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        source_size = image.size
        source_ratio = source_size[0] / source_size[1]
        target_ratio = TARGET_SIZE[0] / TARGET_SIZE[1]
        if abs(source_ratio - target_ratio) > 0.02:
            raise ValueError(f"{source.name} is not a 16:9 capture: {source_size}")
        normalized = ImageOps.fit(
            image,
            TARGET_SIZE,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(target, format="PNG", optimize=True)
    return {
        "name": source.name,
        "source": str(source.relative_to(ROOT)).replace("\\", "/"),
        "source_size": list(source_size),
        "normalized_size": list(TARGET_SIZE),
        "source_sha256": sha256(source),
        "normalized_sha256": sha256(target),
        "source_modified_utc": datetime.fromtimestamp(
            source.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    production = json.loads(PRODUCTION.read_text(encoding="utf-8"))
    required: set[str] = set()
    for shot in production["shots"]:
        if "image" in shot:
            required.add(shot["image"])
        required.update(shot.get("images", []))

    missing = [name for name in sorted(required) if not (args.source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required captures: {', '.join(missing)}")

    records = [normalize(args.source / name, args.target / name) for name in sorted(required)]
    manifest = {
        "classification": "SIMULATED PROTOTYPE CAPTURE",
        "field_validation": False,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "target_size": list(TARGET_SIZE),
        "required_disclosure": production["disclosure"],
        "captures": records,
    }
    manifest_path = args.target / "capture-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Normalized {len(records)} captures into {args.target}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
