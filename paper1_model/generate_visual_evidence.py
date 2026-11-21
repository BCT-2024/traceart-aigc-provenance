#!/usr/bin/env python3
"""Generate visual-comparison and end-to-end verification evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import numpy as np
from imwatermark import WatermarkEncoder

from attacks import apply_attack
from payload import REPEAT_FACTOR, stable_hash_int
from verify import build_database, encode_for_row, verify_image
from watermark import embed_bits, load_rgb, psnr, save_rgb, ssim


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
OUT_DIR = SCRIPT_DIR / "results_visual_evidence"
META = DATASET_DIR / "metadata_all.csv"
QUALITY = SCRIPT_DIR / "results_full_capture_scan" / "quality_metrics.csv"
ROBUSTNESS = SCRIPT_DIR / "results_full_capture_scan" / "robustness_detail.csv"

ALPHA = 28.0
SEED = 20260910


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def select_representatives(quality_rows):
    by_category = {}
    for category in ("landscape", "portrait"):
        candidates = sorted(
            (row for row in quality_rows if row["category"] == category),
            key=lambda row: float(row["psnr"]),
        )
        by_category[category] = candidates[len(candidates) // 2]
    return by_category


def encode_external(image, coded_bits, method, generation_id):
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    encoder = WatermarkEncoder()
    if method == "rivaGan":
        bits = [
            int(bit)
            for bit in format(stable_hash_int(generation_id, 32), "032b")
        ]
        encoder.set_by_bits(bits)
        encoder.loadModel()
        payload_bits = 32
    else:
        encoder.set_by_bits(list(coded_bits))
        payload_bits = len(coded_bits)
    encoded = encoder.encode(bgr, method)
    return cv2.cvtColor(encoded, cv2.COLOR_BGR2RGB), payload_bits


def make_multimethod_examples(rows_by_id):
    quality = read_csv(QUALITY)
    representatives = select_representatives(quality)
    methods = [
        ("original", "Original"),
        ("ours", "Ours"),
        ("dwtDct", "DWT-DCT"),
        ("dwtDctSvd", "DWT-DCT-SVD"),
        ("rivaGan", "RivaGAN"),
    ]
    output_rows = []
    for category, row in representatives.items():
        image = load_rgb(DATASET_DIR / rows_by_id[row["generation_id"]]["relative_path"], size=512)
        _, coded_bits = encode_for_row(
            rows_by_id[row["generation_id"]],
            repeat=REPEAT_FACTOR,
            mode="rs_repeat",
        )
        for method, display_name in methods:
            if method == "original":
                encoded = image
                payload_bits = 0
            elif method == "ours":
                encoded = embed_bits(
                    image,
                    coded_bits,
                    seed=SEED,
                    alpha=ALPHA,
                    carrier="dwt_dct",
                )
                payload_bits = len(coded_bits)
            else:
                encoded, payload_bits = encode_external(
                    image,
                    coded_bits,
                    method,
                    row["generation_id"],
                )
            relative_output = Path("paper1_model") / "results_visual_evidence" / "multimethod" / (
                f"{category}_{method}.png"
            )
            save_rgb(SCRIPT_DIR.parent / relative_output, encoded)
            output_rows.append(
                {
                    "category": category,
                    "generation_id": row["generation_id"],
                    "method": method,
                    "display_name": display_name,
                    "payload_bits": payload_bits,
                    "psnr": "" if method == "original" else f"{psnr(image, encoded):.6f}",
                    "ssim": "" if method == "original" else f"{ssim(image, encoded):.9f}",
                    "relative_path": str(relative_output),
                }
            )
    write_csv(
        OUT_DIR / "multimethod_examples.csv",
        output_rows,
        [
            "category",
            "generation_id",
            "method",
            "display_name",
            "payload_bits",
            "psnr",
            "ssim",
            "relative_path",
        ],
    )
    return representatives


def choose_case_source(quality, robustness):
    by_id = {}
    for row in robustness:
        key = (
            row["attack"],
            json.dumps(json.loads(row["params"]), sort_keys=True),
        )
        by_id.setdefault(row["generation_id"], {})[key] = row
    required = [
        ("clean", "{}"),
        ("jpeg", '{"quality": 70}'),
        ("crop", '{"ratio": 0.9}'),
    ]
    valid_ids = {
        image_id
        for image_id, attacks in by_id.items()
        if all(
            key in attacks and attacks[key]["success"] == "1"
            for key in required
        )
    }
    quality_sorted = sorted(
        (row for row in quality if row["generation_id"] in valid_ids),
        key=lambda row: float(row["psnr"]),
    )
    return quality_sorted[len(quality_sorted) // 2]


def make_case_gallery(rows_by_id, quality, robustness):
    selected = choose_case_source(quality, robustness)
    row = rows_by_id[selected["generation_id"]]
    image = load_rgb(DATASET_DIR / row["relative_path"], size=512)
    payload, coded_bits = encode_for_row(row, repeat=REPEAT_FACTOR, mode="rs_repeat")
    watermarked = embed_bits(
        image,
        coded_bits,
        seed=SEED,
        alpha=ALPHA,
        carrier="dwt_dct",
    )
    database = build_database(list(rows_by_id.values()), DATASET_DIR)
    cases = [
        ("clean", {}),
        ("jpeg", {"quality": 70}),
        ("crop", {"ratio": 0.9}),
        ("print_scan", {}),
    ]
    output_rows = []
    for attack, params in cases:
        attacked = apply_attack(watermarked, attack, params)
        relative_output = (
            Path("paper1_model")
            / "results_visual_evidence"
            / "case_gallery"
            / f"{attack}.png"
        )
        save_rgb(SCRIPT_DIR.parent / relative_output, attacked)
        result = verify_image(
            attacked,
            database,
            seed=SEED,
            repeat=REPEAT_FACTOR,
            expected_bits=coded_bits,
            carrier="dwt_dct",
            mode="rs_repeat",
            verification_mode="joint",
            content_binding_required=True,
            content_binding_threshold=0.30,
        )
        decoded_id = f"{result.get('generation_id', 0):012x}".upper()
        expected_id = f"{stable_hash_int(row['generation_id'], 48):012x}".upper()
        matched_id = result.get("matched_generation_id", "")
        output_rows.append(
            {
                "generation_id": row["generation_id"],
                "category": row["category"],
                "attack": attack,
                "params": json.dumps(params, sort_keys=True),
                "relative_path": str(relative_output),
                "decoded_id_prefix": decoded_id[:8],
                "expected_id_prefix": expected_id[:8],
                "generation_match": int(result["generation_match"]),
                "crc_ok": int(result["crc_ok"]),
                "rs_success": int(result["rs_success"]),
                "ber": f"{result['ber']:.9f}",
                "content_binding_score": f"{result['content_binding_score']:.9f}",
                "content_binding_ok": int(result["content_binding_ok"]),
                "alignment": result["alignment"],
                "score": f"{result['score']:.9f}",
                "trust": result["trust"],
                "success": int(result["success"]),
                "matched_generation_id": matched_id,
            }
        )
    write_csv(
        OUT_DIR / "case_gallery.csv",
        output_rows,
        list(output_rows[0]),
    )
    return output_rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = read_csv(META)
    rows_by_id = {row["generation_id"]: row for row in metadata}
    quality = read_csv(QUALITY)
    robustness = read_csv(ROBUSTNESS)
    make_multimethod_examples(rows_by_id)
    cases = make_case_gallery(rows_by_id, quality, robustness)
    print(f"output={OUT_DIR}")
    print(json.dumps(cases, indent=2))


if __name__ == "__main__":
    main()
