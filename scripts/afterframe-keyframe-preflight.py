
#!/usr/bin/env python3
"""Validate ten approved AFTERFRAME keyframes are reachable and native 9:16 images."""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

MAX_BYTES = 20 * 1024 * 1024
MIN_WIDTH = 540
MIN_HEIGHT = 960
EXPECTED_RATIO = 9 / 16
RATIO_TOLERANCE = 0.012


def fail(message):
    print(f"PREFLIGHT: BLOCKED — {message}", file=sys.stderr)
    raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="keyframes-manifest.json")
    parser.add_argument("--output", default="keyframe-preflight-report.json")
    parser.add_argument("--download-dir", default="verified-keyframes")
    args = parser.parse_args()

    try:
        manifest = json.loads(
            Path(args.manifest).read_text(encoding="utf-8")
        )
    except Exception as exc:
        fail(f"cannot read manifest JSON: {exc}")

    shots = manifest.get("shots")
    if not isinstance(shots, list) or len(shots) != 10:
        fail("manifest must contain exactly 10 shots")

    title = manifest.get("episode_title")
    if not isinstance(title, str) or not title.strip():
        fail("episode_title is required")

    seen = set()
    for shot in shots:
        number = shot.get("shot_number")
        if not isinstance(number, int) or number in seen or not 1 <= number <= 10:
            fail("shot_number values must be unique integers from 1 to 10")
        seen.add(number)

        if shot.get("approved") is not True:
            fail(f"shot {number} has not been approved")

        url = shot.get("image_url")
        parsed = urlparse(url or "")
        if parsed.scheme != "https" or not parsed.netloc:
            fail(f"shot {number} image_url must be a valid HTTPS URL")

    if seen != set(range(1, 11)):
        fail("shot numbers must cover 1 through 10")

    out_dir = Path(args.download_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "episode_title": title,
        "status": "passed",
        "checks": []
    }

    import requests
    session = requests.Session()

    for shot in sorted(shots, key=lambda x: x["shot_number"]):
        number = shot["shot_number"]
        url = shot["image_url"]

        try:
            response = session.get(
                url,
                timeout=(15, 45),
                stream=True,
                headers={
                    "User-Agent": "AFTERFRAME-Keyframe-Preflight/1.0"
                }
            )
            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if not content_type.startswith("image/"):
                fail(
                    f"shot {number} URL did not return an image "
                    f"(Content-Type: {content_type})"
                )

            data = bytearray()
            for chunk in response.iter_content(1024 * 256):
                if chunk:
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        fail(f"shot {number} exceeds the 20 MB download limit")

            response.close()

            path = out_dir / f"shot-{number:02d}.image"
            path.write_bytes(data)

            try:
                with Image.open(path) as image:
                    image.verify()

                with Image.open(path) as image:
                    width, height = image.size
                    image_format = image.format

            except Exception as exc:
                fail(f"shot {number} is not a valid readable image: {exc}")

            ratio = width / height

            if width < MIN_WIDTH or height < MIN_HEIGHT:
                fail(
                    f"shot {number} is {width}x{height}; "
                    "minimum is 540x960"
                )

            if abs(ratio - EXPECTED_RATIO) > RATIO_TOLERANCE:
                fail(
                    f"shot {number} is {width}x{height} (not 9:16); "
                    "no crop or stretch was applied"
                )

            report["checks"].append({
                "shot_number": number,
                "approved": True,
                "reachable": True,
                "width": width,
                "height": height,
                "format": image_format,
                "aspect_ratio": round(ratio, 5),
                "status": "passed"
            })

        except requests.RequestException as exc:
            fail(f"shot {number} image is unavailable: {exc}")

    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(
        "PREFLIGHT: PASSED — all 10 approved keyframes "
        "are reachable and 9:16."
    )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
