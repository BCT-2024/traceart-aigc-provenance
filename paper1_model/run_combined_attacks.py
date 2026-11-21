#!/usr/bin/env python3
"""Evaluate combined attacks for the Paper 1 pipeline."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from attacks import apply_attack
from verify import build_database, encode_for_row, verify_image
from watermark import embed_bits, load_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
META = DATASET_DIR / "metadata_all.csv"
OUT = SCRIPT_DIR / "results_combined"

ATTACKS = [
    ("crop_jpeg", {"crop_ratio": 0.9, "jpeg_quality": 70}),
    ("resize_jpeg", {"scale": 0.75, "jpeg_quality": 70}),
    ("screenshot_noise", {"scale": 0.8, "jpeg_quality": 80, "sigma": 3}),
    ("blur_jpeg", {"ksize": 3, "jpeg_quality": 70}),
    ("crop_resize_jpeg", {"crop_ratio": 0.9, "scale": 0.8, "jpeg_quality": 70}),
    ("social_recompress", {"quality_1": 75, "scale": 0.9, "quality_2": 70}),
]


def load_rows():
    with META.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-pos", type=int, default=0)
    parser.add_argument("--limit-neg", type=int, default=0)
    parser.add_argument("--alpha", type=float, default=28.0)
    parser.add_argument("--repeat", type=int, default=4)
    parser.add_argument("--carrier", default="dwt_dct")
    parser.add_argument("--payload-mode", default="rs_repeat")
    parser.add_argument("--output-dir", default=str(OUT))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    database = build_database(rows, DATASET_DIR)
    positives = [r for r in rows if r["sample_group"] == "positive"]
    negatives = [r for r in rows if r["sample_group"] in ("negative_ai", "natural")]
    if args.limit_pos > 0:
        positives = positives[: args.limit_pos]
    if args.limit_neg > 0:
        negatives = negatives[: args.limit_neg]

    detail = []
    negative_detail = []
    for index, row in enumerate(positives, 1):
        image = load_rgb(DATASET_DIR / row["relative_path"], size=512)
        _, bits = encode_for_row(
            row, repeat=args.repeat, mode=args.payload_mode
        )
        watermarked = embed_bits(
            image,
            bits,
            seed=20260910,
            alpha=args.alpha,
            carrier=args.carrier,
        )
        for attack_name, params in ATTACKS:
            attacked = apply_attack(watermarked, attack_name, params)
            result = verify_image(
                attacked,
                database,
                seed=20260910,
                repeat=args.repeat,
                expected_bits=bits,
                carrier=args.carrier,
                mode=args.payload_mode,
                verification_mode="joint",
            )
            detail.append(
                {
                    "generation_id": row["generation_id"],
                    "attack": attack_name,
                    "params": json.dumps(params, ensure_ascii=False),
                    "ber": result["ber"],
                    "crc_ok": int(result["crc_ok"]),
                    "rs_success": int(result["rs_success"]),
                    "generation_match": int(result["generation_match"]),
                    "score": result["score"],
                    "trust": result["trust"],
                    "success": int(result["success"]),
                    "alignment": result["alignment"],
                }
            )
        if index % 20 == 0:
            print(f"positive {index}/{len(positives)}")

    for index, row in enumerate(negatives, 1):
        image = load_rgb(DATASET_DIR / row["relative_path"], size=512)
        for attack_name, params in ATTACKS:
            attacked = apply_attack(image, attack_name, params)
            result = verify_image(
                attacked,
                database,
                seed=20260910,
                repeat=args.repeat,
                carrier=args.carrier,
                mode=args.payload_mode,
                verification_mode="joint",
            )
            negative_detail.append(
                {
                    "generation_id": row["generation_id"],
                    "sample_group": row["sample_group"],
                    "attack": attack_name,
                    "params": json.dumps(params, ensure_ascii=False),
                    "score": result["score"],
                    "trust": result["trust"],
                    "false_positive": int(result["success"]),
                }
            )
        if index % 20 == 0:
            print(f"negative {index}/{len(negatives)}")

    with (out_dir / "combined_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        fields = [
            "generation_id",
            "attack",
            "params",
            "ber",
            "crc_ok",
            "rs_success",
            "generation_match",
            "score",
            "trust",
            "success",
            "alignment",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(detail)

    with (out_dir / "negative_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        fields = [
            "generation_id",
            "sample_group",
            "attack",
            "params",
            "score",
            "trust",
            "false_positive",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(negative_detail)

    summary = {}
    for attack_name, params in ATTACKS:
        selected = [r for r in detail if r["attack"] == attack_name]
        summary[attack_name] = {
            "count": len(selected),
            "success_rate": sum(r["success"] for r in selected) / len(selected),
            "mean_ber": sum(float(r["ber"]) for r in selected) / len(selected),
            "mean_score": sum(float(r["score"]) for r in selected) / len(selected),
            "trust_counts": dict(Counter(r["trust"] for r in selected)),
        }
    fp = sum(r["false_positive"] for r in negative_detail)
    summary["false_positive"] = {
        "count": len(negative_detail),
        "false_positive_count": fp,
        "false_positive_rate": fp / len(negative_detail) if negative_detail else None,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
