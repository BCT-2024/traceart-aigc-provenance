#!/usr/bin/env python3
"""Attribute accepted and rejected AIGC provenance cases to the first failing stage.

The experiment reuses the final alpha=28 watermarked carriers and re-runs the
complete joint verifier so that payload, registry, content-binding, trust, and
alignment evidence are stored together.  It never reconstructs missing
content-binding outcomes from older summary files.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from attacks import apply_attack
from payload import REPEAT_FACTOR
from verify import build_database, encode_for_row, verify_image
from watermark import load_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
METADATA_PATH = DATASET_DIR / "metadata_all.csv"
DEFAULT_WATERMARKED_DIR = SCRIPT_DIR / "results_full_capture_scan" / "watermarked"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "results_verification_attribution_alpha28"
SEED = 20260910

SINGLE_ATTACKS = [
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

COMBINED_ATTACKS = [
    ("crop_jpeg", {"crop_ratio": 0.9, "jpeg_quality": 70}),
    ("resize_jpeg", {"scale": 0.75, "jpeg_quality": 70}),
    ("screenshot_noise", {"scale": 0.8, "jpeg_quality": 80, "sigma": 3}),
    ("blur_jpeg", {"ksize": 3, "jpeg_quality": 70}),
    ("crop_resize_jpeg", {"crop_ratio": 0.9, "scale": 0.8, "jpeg_quality": 70}),
    ("social_recompress", {"quality_1": 75, "scale": 0.9, "quality_2": 70}),
]

STAGE_COLUMNS = [
    "crc_pass_rate",
    "rs_pass_rate",
    "generation_id_pass_rate",
    "field_consistency_pass_rate",
    "content_binding_pass_rate",
    "final_accept_rate",
]

FAILURE_ORDER = [
    "Accepted",
    "Payload integrity",
    "Registry mismatch",
    "Content binding",
    "Trust threshold",
]


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def attack_key(attack: str, params: dict) -> str:
    suffix = "_".join(f"{key}-{value}" for key, value in sorted(params.items()))
    return f"{attack}:{suffix}" if suffix else attack


def display_label(attack: str, params: dict) -> str:
    labels = {
        "clean": "Clean",
        "brightness_contrast": "Brightness/contrast",
        "screenshot": "Screenshot sim.",
        "real_screen_capture": "Screen-capture sim.",
        "print_scan": "Print-scan sim.",
        "crop_jpeg": "Crop+JPEG",
        "resize_jpeg": "Resize+JPEG",
        "screenshot_noise": "Screenshot+noise",
        "blur_jpeg": "Blur+JPEG",
        "crop_resize_jpeg": "Crop+Resize+JPEG",
        "social_recompress": "Social recompression",
    }
    dynamic_labels = {
        "jpeg": lambda: f"JPEG Q{params['quality']}",
        "resize": lambda: f"Resize {params['scale']:g}x",
        "crop": lambda: f"Crop {params['ratio']:g}",
        "gaussian_noise": lambda: f"Gaussian noise s={params['sigma']:g}",
        "salt_pepper": lambda: f"Salt-and-pepper {params['amount']:g}",
        "blur": lambda: f"Blur {params['ksize']}x{params['ksize']}",
    }
    if attack in dynamic_labels:
        return dynamic_labels[attack]()
    return labels.get(attack, attack.replace("_", " ").title())


def first_failure_stage(result: dict) -> str:
    """Assign a rejected sample to its earliest unmet verification gate."""

    if bool(result["success"]):
        return "Accepted"
    if not (bool(result["crc_ok"]) and bool(result["rs_success"])):
        return "Payload integrity"
    if (
        not bool(result["generation_match"])
        or float(result["field_score"]) < 1.0 - 1e-9
    ):
        return "Registry mismatch"
    if not bool(result["content_binding_ok"]):
        return "Content binding"
    return "Trust threshold"


def summarize_attacks(detail_rows):
    grouped = defaultdict(list)
    for row in detail_rows:
        grouped[row["attack_key"]].append(row)

    pass_rows = []
    failure_rows = []
    for key, rows in grouped.items():
        n = len(rows)
        crc = sum(int(row["crc_ok"]) for row in rows)
        rs = sum(
            int(row["crc_ok"]) and int(row["rs_success"]) for row in rows
        )
        generation = sum(
            int(row["crc_ok"])
            and int(row["rs_success"])
            and int(row["generation_match"])
            for row in rows
        )
        fields = sum(
            int(row["crc_ok"])
            and int(row["rs_success"])
            and int(row["generation_match"])
            and float(row["field_score"]) >= 1.0 - 1e-9
            for row in rows
        )
        content = sum(
            int(row["crc_ok"])
            and int(row["rs_success"])
            and int(row["generation_match"])
            and float(row["field_score"]) >= 1.0 - 1e-9
            and int(row["content_binding_ok"])
            for row in rows
        )
        accepted = sum(int(row["success"]) for row in rows)
        counts = [crc, rs, generation, fields, content, accepted]
        pass_rows.append(
            {
                "attack_key": key,
                "attack": rows[0]["attack"],
                "params": rows[0]["params"],
                "label": rows[0]["label"],
                "attack_group": rows[0]["attack_group"],
                "count": n,
                **{
                    column: value / n
                    for column, value in zip(STAGE_COLUMNS, counts)
                },
            }
        )

        failures = Counter(row["first_failure_stage"] for row in rows)
        failure_rows.append(
            {
                "attack_key": key,
                "attack": rows[0]["attack"],
                "params": rows[0]["params"],
                "label": rows[0]["label"],
                "attack_group": rows[0]["attack_group"],
                "count": n,
                **{
                    stage: failures.get(stage, 0) / n
                    for stage in FAILURE_ORDER
                },
            }
        )
    for row in pass_rows:
        cumulative = [float(row[column]) for column in STAGE_COLUMNS]
        if any(
            later > earlier + 1e-12
            for earlier, later in zip(cumulative, cumulative[1:])
        ):
            raise ValueError(
                f"Non-monotonic cumulative stages for {row['attack_key']}"
            )
    for row in failure_rows:
        attributed = sum(float(row[stage]) for stage in FAILURE_ORDER)
        if abs(attributed - 1.0) > 1e-12:
            raise ValueError(
                f"First-failure attribution does not sum to one for "
                f"{row['attack_key']}"
            )
    return pass_rows, failure_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--alpha", type=float, default=28.0)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--repeat", type=int, default=REPEAT_FACTOR)
    parser.add_argument("--carrier", default="dwt_dct")
    parser.add_argument("--payload-mode", default="rs_repeat")
    parser.add_argument("--content-binding-threshold", type=float, default=0.30)
    parser.add_argument(
        "--attack-set",
        choices=("all", "single", "combined"),
        default="all",
    )
    parser.add_argument(
        "--watermarked-dir",
        type=Path,
        default=DEFAULT_WATERMARKED_DIR,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    attacks = []
    if args.attack_set in ("all", "single"):
        attacks.extend(("single", name, params) for name, params in SINGLE_ATTACKS)
    if args.attack_set in ("all", "combined"):
        attacks.extend(
            ("combined", name, params) for name, params in COMBINED_ATTACKS
        )

    rows = read_csv(METADATA_PATH)
    positives = [row for row in rows if row.get("sample_group") == "positive"]
    if args.limit > 0:
        positives = positives[: args.limit]
    if not positives:
        raise RuntimeError("No registered positive images were selected.")

    missing = [
        row["generation_id"]
        for row in positives
        if not (args.watermarked_dir / f"{row['generation_id']}.png").exists()
    ]
    if missing:
        preview = ", ".join(missing[:5])
        raise FileNotFoundError(
            f"{len(missing)} final alpha=28 carriers are missing: {preview}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    database = build_database(rows, DATASET_DIR)
    detail_rows = []
    print(
        f"database={len(database)} positives={len(positives)} "
        f"attacks={len(attacks)} attack_set={args.attack_set}",
        flush=True,
    )

    for image_index, row in enumerate(positives, 1):
        watermarked = load_rgb(
            args.watermarked_dir / f"{row['generation_id']}.png",
            size=512,
        )
        _, coded_bits = encode_for_row(
            row, repeat=args.repeat, mode=args.payload_mode
        )
        for attack_group, attack_name, params in attacks:
            attacked = apply_attack(watermarked, attack_name, params)
            result = verify_image(
                attacked,
                database,
                seed=args.seed,
                repeat=args.repeat,
                expected_bits=coded_bits,
                carrier=args.carrier,
                mode=args.payload_mode,
                verification_mode="joint",
                content_binding_required=True,
                content_binding_threshold=args.content_binding_threshold,
            )
            detail_rows.append(
                {
                    "generation_id": row["generation_id"],
                    "category": row.get("category", ""),
                    "attack_group": attack_group,
                    "attack": attack_name,
                    "attack_key": attack_key(attack_name, params),
                    "label": display_label(attack_name, params),
                    "params": json.dumps(params, ensure_ascii=False),
                    "ber": result["ber"],
                    "crc_ok": int(result["crc_ok"]),
                    "rs_success": int(result["rs_success"]),
                    "generation_match": int(result["generation_match"]),
                    "matched_generation_id": result.get(
                        "matched_generation_id", ""
                    ),
                    "field_score": result["field_score"],
                    "hash_score": result["hash_score"],
                    "content_binding_score": result["content_binding_score"],
                    "content_binding_ok": int(result["content_binding_ok"]),
                    "content_binding_method": result["content_binding_method"],
                    "content_binding_effective_threshold": result[
                        "content_binding_effective_threshold"
                    ],
                    "content_binding_flat_mode": int(
                        result["content_binding_flat_mode"]
                    ),
                    "score": result["score"],
                    "trust": result["trust"],
                    "success": int(result["success"]),
                    "alignment": result["alignment"],
                    "first_failure_stage": first_failure_stage(result),
                }
            )
        if image_index % 10 == 0 or image_index == len(positives):
            print(
                f"registered image {image_index}/{len(positives)}",
                flush=True,
            )

    pass_rows, failure_rows = summarize_attacks(detail_rows)

    detail_fields = [
        "generation_id",
        "category",
        "attack_group",
        "attack",
        "attack_key",
        "label",
        "params",
        "ber",
        "crc_ok",
        "rs_success",
        "generation_match",
        "matched_generation_id",
        "field_score",
        "hash_score",
        "content_binding_score",
        "content_binding_ok",
        "content_binding_method",
        "content_binding_effective_threshold",
        "content_binding_flat_mode",
        "score",
        "trust",
        "success",
        "alignment",
        "first_failure_stage",
    ]
    write_csv(args.output_dir / "stage_detail.csv", detail_rows, detail_fields)
    write_csv(
        args.output_dir / "stage_pass_rates.csv",
        pass_rows,
        [
            "attack_key",
            "attack",
            "params",
            "label",
            "attack_group",
            "count",
            *STAGE_COLUMNS,
        ],
    )
    write_csv(
        args.output_dir / "first_failure_counts.csv",
        failure_rows,
        [
            "attack_key",
            "attack",
            "params",
            "label",
            "attack_group",
            "count",
            *FAILURE_ORDER,
        ],
    )

    summary = {
        "experiment": "verification_stage_failure_attribution",
        "alpha": args.alpha,
        "seed": args.seed,
        "repeat": args.repeat,
        "carrier": args.carrier,
        "payload_mode": args.payload_mode,
        "verification_mode": "joint",
        "content_binding_required": True,
        "content_binding_threshold": args.content_binding_threshold,
        "database_records": len(database),
        "registered_images": len(positives),
        "attacks": len(attacks),
        "observations": len(detail_rows),
        "attack_groups": dict(
            Counter(row["attack_group"] for row in detail_rows)
        ),
        "first_failure_overall": dict(
            Counter(row["first_failure_stage"] for row in detail_rows)
        ),
        "content_binding_methods": dict(
            Counter(row["content_binding_method"] for row in detail_rows)
        ),
        "accepted_with_incomplete_fields": sum(
            int(row["success"])
            and float(row["field_score"]) < 1.0 - 1e-9
            for row in detail_rows
        ),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report_lines = [
        "# Verification-stage failure attribution",
        "",
        f"- Registered images: {len(positives)}",
        f"- Database records: {len(database)}",
        f"- Attacks: {len(attacks)}",
        f"- Observations: {len(detail_rows)}",
        "- Alpha: 28; verification: joint; content binding: required "
        "(ORB threshold 0.30; flat fallback 0.90)",
        "",
        "| Attack | n | CRC | RS | Generation ID | Fields | Content | Accept |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in pass_rows:
        report_lines.append(
            "| {label} | {count} | {crc_pass_rate:.1%} | "
            "{rs_pass_rate:.1%} | {generation_id_pass_rate:.1%} | "
            "{field_consistency_pass_rate:.1%} | "
            "{content_binding_pass_rate:.1%} | {final_accept_rate:.1%} |".format(
                **row
            )
        )
    report_lines.extend(
        [
            "",
            "Pass rates are cumulative through each stage. "
            "`first_failure_counts.csv` assigns each rejection to the earliest "
            "unmet gate.",
            "",
        ]
    )
    (args.output_dir / "report.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
