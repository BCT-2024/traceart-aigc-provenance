#!/usr/bin/env python3
"""Forgery-based verification ablation.

Embeds a validly formatted but unregistered watermark into negative images,
then compares watermark-only, database-only, and joint verification.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import uuid
from pathlib import Path

from payload import build_payload, encode_payload
from verify import build_database, verify_image
from watermark import embed_bits, load_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
META = DATASET_DIR / "metadata_all.csv"
OUT = SCRIPT_DIR / "results_verification_ablation"


def load_rows():
    with META.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(limit_per_group: int = 10):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    database = build_database(rows, DATASET_DIR)
    negatives = [
        row for row in rows if row["sample_group"] in ("negative_ai", "natural")
    ][: limit_per_group * 2]

    results = []
    for index, row in enumerate(negatives, 1):
        image_path = DATASET_DIR / row["relative_path"]
        image = load_rgb(image_path, size=512)
        fake_generation_id = uuid.uuid4().hex
        payload = build_payload(
            platform_id="Impersonator",
            generation_id=fake_generation_id,
            model_version="fake-model",
            created_at="2026-09-10T12:00:00+08:00",
            content_sha256=sha256_file(image_path),
        )
        bits = encode_payload(payload, repeat=4, mode="rs_repeat")
        forged = embed_bits(image, bits, seed=20260910, alpha=24, carrier="dwt_dct")

        for mode in ["watermark_only", "db_only", "joint"]:
            result = verify_image(
                forged,
                database,
                seed=20260910,
                repeat=4,
                expected_bits=bits,
                carrier="dwt_dct",
                mode="rs_repeat",
                verification_mode=mode,
            )
            results.append(
                {
                    "sample_group": row["sample_group"],
                    "source_generation_id": row["generation_id"],
                    "fake_generation_id": fake_generation_id,
                    "verification_mode": mode,
                    "accepted": int(result["success"]),
                    "crc_ok": int(result["crc_ok"]),
                    "rs_success": int(result["rs_success"]),
                    "generation_match": int(result["generation_match"]),
                    "score": result["score"],
                    "trust": result["trust"],
                }
            )
        print(f"[{index}/{len(negatives)}] forged {row['generation_id']}")

    csv_path = OUT / "forgery_verification_detail.csv"
    fields = [
        "sample_group",
        "source_generation_id",
        "fake_generation_id",
        "verification_mode",
        "accepted",
        "crc_ok",
        "rs_success",
        "generation_match",
        "score",
        "trust",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    summary = {}
    for mode in ["watermark_only", "db_only", "joint"]:
        selected = [row for row in results if row["verification_mode"] == mode]
        summary[mode] = {
            "count": len(selected),
            "acceptance_rate": sum(row["accepted"] for row in selected) / len(selected),
            "mean_score": sum(row["score"] for row in selected) / len(selected),
        }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
