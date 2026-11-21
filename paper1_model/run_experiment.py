#!/usr/bin/env python3
"""Run Paper 1 watermark experiments on the prepared 300-image dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from attacks import apply_attack
from payload import REPEAT_FACTOR, bit_error_rate, decode_payload
from verify import build_database, encode_for_row, verify_image
from watermark import embed_bits, extract_bits, load_rgb, psnr, save_rgb, ssim


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
METADATA_PATH = DATASET_DIR / "metadata_all.csv"

ATTACKS = [
    ("clean", {}),
    ("jpeg", {"quality": 90}),
    ("jpeg", {"quality": 70}),
    ("jpeg", {"quality": 50}),
    ("resize", {"scale": 0.75}),
    ("resize", {"scale": 1.5}),
    ("crop", {"ratio": 0.9}),
    ("gaussian_noise", {"sigma": 3}),
    ("gaussian_noise", {"sigma": 8}),
    ("salt_pepper", {"amount": 0.002}),
    ("brightness_contrast", {}),
    ("blur", {"ksize": 3}),
    ("screenshot", {}),
    ("real_screen_capture", {}),
    ("print_scan", {}),
]


def load_rows():
    with METADATA_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def select_rows(rows, group, limit):
    selected = [row for row in rows if row.get("sample_group") == group]
    return selected if limit <= 0 else selected[:limit]


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-pos", type=int, default=5)
    parser.add_argument("--limit-neg", type=int, default=5)
    parser.add_argument("--limit-natural", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=28.0)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--repeat", type=int, default=REPEAT_FACTOR)
    parser.add_argument("--carrier", default="dwt_dct")
    parser.add_argument("--payload-mode", default="rs_repeat")
    parser.add_argument("--verification-mode", default="joint")
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR / "results"))
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    if args.full:
        args.limit_pos = 0
        args.limit_neg = 0
        args.limit_natural = 0

    rows = load_rows()
    database = build_database(rows, DATASET_DIR)
    positives = select_rows(rows, "positive", args.limit_pos)
    negatives = select_rows(rows, "negative_ai", args.limit_neg)
    naturals = select_rows(rows, "natural", args.limit_natural)

    output_dir = Path(args.output_dir)
    watermarked_dir = output_dir / "watermarked"
    quality_rows = []
    robustness_rows = []
    negative_rows = []

    print(
        f"Database={len(database)} positives, "
        f"test positives={len(positives)}, negatives={len(negatives)}, "
        f"natural={len(naturals)}"
    )

    for index, row in enumerate(positives, 1):
        source_path = DATASET_DIR / row["relative_path"]
        original = load_rgb(source_path, size=512)
        payload_bytes, coded_bits = encode_for_row(
            row, repeat=args.repeat, mode=args.payload_mode
        )
        watermarked = embed_bits(
            original,
            coded_bits,
            seed=args.seed,
            alpha=args.alpha,
            carrier=args.carrier,
        )
        watermarked_path = watermarked_dir / f"{row['generation_id']}.png"
        save_rgb(watermarked_path, watermarked)
        quality_rows.append(
            {
                "generation_id": row["generation_id"],
                "category": row.get("category", ""),
                "alpha": args.alpha,
                "psnr": psnr(original, watermarked),
                "ssim": ssim(original, watermarked),
                "watermarked_path": str(watermarked_path),
            }
        )

        for attack_name, params in ATTACKS:
            attacked = apply_attack(watermarked, attack_name, params)
            result = verify_image(
                attacked,
                database,
                seed=args.seed,
                repeat=args.repeat,
                expected_bits=coded_bits,
                carrier=args.carrier,
                mode=args.payload_mode,
                verification_mode=args.verification_mode,
            )
            robustness_rows.append(
                {
                    "generation_id": row["generation_id"],
                    "category": row.get("category", ""),
                    "attack": attack_name,
                    "params": json.dumps(params, ensure_ascii=False),
                    "ber": result["ber"],
                    "rs_success": int(result["rs_success"]),
                    "crc_ok": int(result["crc_ok"]),
                    "generation_match": int(result["generation_match"]),
                    "field_score": result["field_score"],
                    "hash_score": result["hash_score"],
                    "score": result["score"],
                    "trust": result["trust"],
                    "success": int(result["success"]),
                }
            )
        print(f"[positive {index}/{len(positives)}] {row['generation_id']}")

    for group_name, group_rows in [("negative_ai", negatives), ("natural", naturals)]:
        for index, row in enumerate(group_rows, 1):
            image = load_rgb(DATASET_DIR / row["relative_path"], size=512)
            result = verify_image(
                image,
                database,
                seed=args.seed,
                repeat=args.repeat,
                carrier=args.carrier,
                mode=args.payload_mode,
                verification_mode=args.verification_mode,
            )
            negative_rows.append(
                {
                    "generation_id": row["generation_id"],
                    "sample_group": group_name,
                    "rs_success": int(result["rs_success"]),
                    "crc_ok": int(result["crc_ok"]),
                    "generation_match": int(result["generation_match"]),
                    "field_score": result["field_score"],
                    "hash_score": result["hash_score"],
                    "score": result["score"],
                    "trust": result["trust"],
                    "false_positive": int(result["success"]),
                }
            )
            print(f"[{group_name} {index}/{len(group_rows)}] {row['generation_id']}")

    quality_fields = [
        "generation_id",
        "category",
        "alpha",
        "psnr",
        "ssim",
        "watermarked_path",
    ]
    robustness_fields = [
        "generation_id",
        "category",
        "attack",
        "params",
        "ber",
        "rs_success",
        "crc_ok",
        "generation_match",
        "field_score",
        "hash_score",
        "score",
        "trust",
        "success",
    ]
    negative_fields = [
        "generation_id",
        "sample_group",
        "rs_success",
        "crc_ok",
        "generation_match",
        "field_score",
        "hash_score",
        "score",
        "trust",
        "false_positive",
    ]

    write_csv(output_dir / "quality_metrics.csv", quality_rows, quality_fields)
    write_csv(output_dir / "robustness_detail.csv", robustness_rows, robustness_fields)
    write_csv(output_dir / "negative_fpr_detail.csv", negative_rows, negative_fields)

    attack_summary = {}
    for attack_name, params in ATTACKS:
        selected = [
            row
            for row in robustness_rows
            if row["attack"] == attack_name and json.loads(row["params"]) == params
        ]
        if not selected:
            continue
        attack_summary[f"{attack_name}:{params}"] = {
            "count": len(selected),
            "success_rate": sum(r["success"] for r in selected) / len(selected),
            "mean_ber": sum(float(r["ber"]) for r in selected) / len(selected),
            "mean_score": sum(float(r["score"]) for r in selected) / len(selected),
            "trust_counts": dict(Counter(r["trust"] for r in selected)),
        }

    summary = {
        "database_records": len(database),
        "quality": {
            "count": len(quality_rows),
            "mean_psnr": sum(row["psnr"] for row in quality_rows) / len(quality_rows)
            if quality_rows
            else None,
            "mean_ssim": sum(row["ssim"] for row in quality_rows) / len(quality_rows)
            if quality_rows
            else None,
        },
        "robustness": attack_summary,
        "false_positive": {
            "count": len(negative_rows),
            "false_positive_count": sum(row["false_positive"] for row in negative_rows),
            "false_positive_rate": sum(row["false_positive"] for row in negative_rows)
            / len(negative_rows)
            if negative_rows
            else None,
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
