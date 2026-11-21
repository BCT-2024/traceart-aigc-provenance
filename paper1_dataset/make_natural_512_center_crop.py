#!/usr/bin/env python3
"""Create 512x512 natural images with short-side resize and center crop."""

import csv
import hashlib
import io
import os
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR / "images_natural"
OUTPUT_DIR = SCRIPT_DIR / "images_natural_512"
SOURCE_METADATA = SCRIPT_DIR / "metadata_natural.csv"
OUTPUT_METADATA = SCRIPT_DIR / "metadata_natural_512.csv"
PARAMS_PATH = SCRIPT_DIR / "resize_params_natural_512.csv"
COMBINED_PATH = SCRIPT_DIR / "metadata_all.csv"

TARGET = 512
JPEG_QUALITY = 95


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def backup_existing():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if OUTPUT_DIR.exists():
        backup_dir = SCRIPT_DIR / f"images_natural_512_stretch_backup_{stamp}"
        shutil.move(str(OUTPUT_DIR), str(backup_dir))
        print(f"Backed up old image folder: {backup_dir}")
    if PARAMS_PATH.exists():
        backup_params = SCRIPT_DIR / f"resize_params_natural_512_stretch_backup_{stamp}.csv"
        shutil.copy2(str(PARAMS_PATH), str(backup_params))
        print(f"Backed up old parameter file: {backup_params}")


def load_metadata():
    with SOURCE_METADATA.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row["filename"]: row for row in rows}


def process_image(src, dst):
    with Image.open(src) as original:
        exif_orientation = original.getexif().get(274, 1)
        source_mode = original.mode
        source_format = original.format or ""
        source_width, source_height = original.size
        upright = ImageOps.exif_transpose(original)
        upright_width, upright_height = upright.size
        rotation_applied = "yes" if (upright_width, upright_height) != (source_width, source_height) else "no"
        upright = upright.convert("RGB")

        scale = TARGET / min(upright_width, upright_height)
        resized_width = max(TARGET, round(upright_width * scale))
        resized_height = max(TARGET, round(upright_height * scale))
        resized = upright.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

        left = (resized_width - TARGET) // 2
        top = (resized_height - TARGET) // 2
        right = left + TARGET
        bottom = top + TARGET
        cropped = resized.crop((left, top, right, bottom))

        buffer = io.BytesIO()
        cropped.save(
            buffer,
            format="JPEG",
            quality=JPEG_QUALITY,
            subsampling=0,
            optimize=True,
        )
        raw = buffer.getvalue()
        dst.write_bytes(raw)

        return {
            "source_mode": source_mode,
            "source_format": source_format,
            "source_width": source_width,
            "source_height": source_height,
            "source_aspect": f"{source_width / source_height:.6f}",
            "exif_orientation": exif_orientation,
            "rotation_applied": rotation_applied,
            "upright_width": upright_width,
            "upright_height": upright_height,
            "mode": "RGB",
            "resample": "LANCZOS",
            "target_width": TARGET,
            "target_height": TARGET,
            "scale": f"{scale:.6f}",
            "resized_width": resized_width,
            "resized_height": resized_height,
            "crop_left": left,
            "crop_top": top,
            "crop_right": right,
            "crop_bottom": bottom,
            "crop_width": TARGET,
            "crop_height": TARGET,
            "out_width": TARGET,
            "out_height": TARGET,
            "jpeg_quality": JPEG_QUALITY,
            "jpeg_subsampling": "4:4:4",
            "output_bytes": len(raw),
            "output_sha256": sha256_bytes(raw),
        }


def main():
    backup_existing()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = load_metadata()
    params_output_path = PARAMS_PATH
    try:
        with params_output_path.open("w", encoding="utf-8-sig", newline=""):
            pass
    except PermissionError:
        params_output_path = SCRIPT_DIR / "resize_params_natural_512_center_crop.csv"
        print(f"Original parameter file is locked; writing to {params_output_path}")

    param_fields = [
        "index",
        "filename",
        "source_relative_path",
        "output_relative_path",
        "source_bytes",
        "source_sha256",
        "source_mode",
        "source_format",
        "source_width",
        "source_height",
        "source_aspect",
        "exif_orientation",
        "rotation_applied",
        "upright_width",
        "upright_height",
        "mode",
        "resize_mode",
        "resample",
        "target_width",
        "target_height",
        "scale",
        "resized_width",
        "resized_height",
        "crop_left",
        "crop_top",
        "crop_right",
        "crop_bottom",
        "crop_width",
        "crop_height",
        "out_width",
        "out_height",
        "jpeg_quality",
        "jpeg_subsampling",
        "output_bytes",
        "output_sha256",
    ]

    params = []
    output_metadata_rows = []

    for index, src in enumerate(sorted(SOURCE_DIR.glob("*.jpg")), 1):
        dst = OUTPUT_DIR / src.name
        source_raw = src.read_bytes()
        info = process_image(src, dst)
        row = {
            "index": index,
            "filename": src.name,
            "source_relative_path": str(src.relative_to(SCRIPT_DIR)),
            "output_relative_path": str(dst.relative_to(SCRIPT_DIR)),
            "source_bytes": len(source_raw),
            "source_sha256": sha256_bytes(source_raw),
            "resize_mode": "short_side_resize_center_crop",
            **info,
        }
        params.append(row)

        meta = dict(metadata.get(src.name, {}))
        if not meta:
            print(f"Warning: no source metadata for {src.name}")
            continue
        meta["relative_path"] = row["output_relative_path"]
        meta["width"] = TARGET
        meta["height"] = TARGET
        meta["sha256"] = row["output_sha256"]
        meta["resize_mode"] = row["resize_mode"]
        meta["resize_params_file"] = str(params_output_path.name)
        output_metadata_rows.append(meta)

    with params_output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=param_fields)
        writer.writeheader()
        writer.writerows(params)

    metadata_fields = list(output_metadata_rows[0].keys())
    with OUTPUT_METADATA.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metadata_fields)
        writer.writeheader()
        writer.writerows(output_metadata_rows)

    combined_fields = list(metadata_fields)
    for extra in ["sample_group"]:
        if extra not in combined_fields:
            combined_fields.append(extra)

    combined_rows = []
    for path, group in [
        (SCRIPT_DIR / "metadata_positive_general.csv", "positive"),
        (SCRIPT_DIR / "images_negative_other_corrected.csv", "negative_ai"),
        (OUTPUT_METADATA, "natural"),
    ]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                clean = {field: "" for field in combined_fields}
                for key, value in row.items():
                    if key in clean:
                        clean[key] = value
                clean["sample_group"] = group
                combined_rows.append(clean)

    with COMBINED_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=combined_fields)
        writer.writeheader()
        writer.writerows(combined_rows)

    print(f"Processed images: {len(params)}")
    print(f"Output folder: {OUTPUT_DIR}")
    print(f"Resize params: {params_output_path}")
    print(f"Natural metadata: {OUTPUT_METADATA}")
    print(f"Combined metadata rows: {len(combined_rows)}")


if __name__ == "__main__":
    main()
