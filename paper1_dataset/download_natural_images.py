#!/usr/bin/env python3
"""Download 50 CC-licensed natural images from Wikimedia Commons."""

import csv
import hashlib
import io
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "images_natural"
METADATA_PATH = SCRIPT_DIR / "metadata_natural.csv"
COMBINED_PATH = SCRIPT_DIR / "metadata_all.csv"

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {
    "User-Agent": "Codex-Research/1.0 (AIGC provenance dataset preparation)"
}

CATEGORIES = [
    ("landscape", "nature landscape filetype:bitmap"),
    ("animal", "wild animal filetype:bitmap"),
    ("plant", "flower plant filetype:bitmap"),
    ("food", "food dish filetype:bitmap"),
    ("architecture", "historic architecture building filetype:bitmap"),
]

CORE_FIELDS = [
    "generation_id",
    "filename",
    "relative_path",
    "platform_id",
    "model_name",
    "model_version",
    "prompt",
    "prompt_sha256",
    "negative_prompt",
    "seed",
    "sampler",
    "steps",
    "cfg_scale",
    "width",
    "height",
    "created_at",
    "sha256",
    "category",
    "is_platform_sample",
]

EXTRA_FIELDS = [
    "sample_group",
    "source",
    "source_url",
    "source_file_title",
    "artist",
    "license",
    "license_url",
    "attribution_required",
    "image_description",
]

FIELDS = CORE_FIELDS + EXTRA_FIELDS


def strip_html(value):
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_images(query, limit=40):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": "1024",
    }
    response = requests.get(API, params=params, headers=HEADERS, timeout=60)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    return list(pages.values())


def download_image(url, path):
    response = requests.get(url, headers=HEADERS, timeout=120)
    response.raise_for_status()
    path.write_bytes(response.content)
    return response.content


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    seen_titles = set()

    for category, query in CATEGORIES:
        print(f"Searching: {category}")
        candidates = search_images(query)
        count = 0
        for page in candidates:
            if count >= 10:
                break
            title = page.get("title") or ""
            if title in seen_titles:
                continue
            info = (page.get("imageinfo") or [{}])[0]
            mime = info.get("mime") or ""
            if mime not in ("image/jpeg", "image/png"):
                continue
            width = int(info.get("width") or 0)
            height = int(info.get("height") or 0)
            if width < 640 or height < 480:
                continue
            thumburl = info.get("thumburl")
            if not thumburl:
                continue
            ext = ".jpg" if mime == "image/jpeg" else ".png"
            generation_id = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
            filename = f"natural_{category}_{generation_id}{ext}"
            path = OUT_DIR / filename
            try:
                raw = download_image(thumburl, path)
            except Exception as exc:
                print(f"  skip {title}: {exc}")
                continue

            try:
                with Image.open(io.BytesIO(raw)) as img:
                    actual_width, actual_height = img.size
            except Exception:
                path.unlink(missing_ok=True)
                continue

            meta = info.get("extmetadata") or {}
            license_name = strip_html(meta.get("LicenseShortName", {}).get("value"))
            license_url = strip_html(meta.get("LicenseUrl", {}).get("value"))
            artist = strip_html(meta.get("Artist", {}).get("value"))
            description = strip_html(meta.get("ImageDescription", {}).get("value"))
            attribution = strip_html(meta.get("AttributionRequired", {}).get("value"))

            rows.append(
                {
                    "generation_id": generation_id,
                    "filename": filename,
                    "relative_path": str(path.relative_to(SCRIPT_DIR)),
                    "platform_id": "Natural-Image",
                    "model_name": "",
                    "model_version": "",
                    "prompt": "",
                    "prompt_sha256": "",
                    "negative_prompt": "",
                    "seed": "",
                    "sampler": "",
                    "steps": "",
                    "cfg_scale": "",
                    "width": actual_width,
                    "height": actual_height,
                    "created_at": datetime.now().astimezone().isoformat(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "category": category,
                    "is_platform_sample": 0,
                    "sample_group": "natural",
                    "source": "Wikimedia Commons",
                    "source_url": info.get("descriptionurl", ""),
                    "source_file_title": title,
                    "artist": artist,
                    "license": license_name,
                    "license_url": license_url,
                    "attribution_required": attribution,
                    "image_description": description,
                }
            )
            seen_titles.add(title)
            count += 1
            print(f"  [{count}/10] {filename}")
            time.sleep(0.2)

    with METADATA_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    combined_rows = []
    for metadata_file, group in [
        (SCRIPT_DIR / "metadata_positive_general.csv", "positive"),
        (SCRIPT_DIR / "images_negative_other.csv", "negative_ai"),
        (METADATA_PATH, "natural"),
    ]:
        if not metadata_file.exists():
            continue
        with metadata_file.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                clean = {field: "" for field in FIELDS}
                for key, value in row.items():
                    if key in clean:
                        clean[key] = value
                clean["sample_group"] = group
                if group == "negative_ai":
                    clean["platform_id"] = "Other-Platform"
                    clean["is_platform_sample"] = 0
                if group in ("positive", "negative_ai"):
                    clean["source"] = ""
                    clean["source_url"] = ""
                    clean["source_file_title"] = ""
                    clean["artist"] = ""
                    clean["license"] = ""
                    clean["license_url"] = ""
                    clean["attribution_required"] = ""
                    clean["image_description"] = ""
                combined_rows.append(clean)

    with COMBINED_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(combined_rows)

    print(f"Natural images: {len(rows)}")
    print(f"Natural metadata: {METADATA_PATH}")
    print(f"Combined metadata: {COMBINED_PATH}")


if __name__ == "__main__":
    main()
