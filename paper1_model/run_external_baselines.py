#!/usr/bin/env python3
"""Compare against external watermark implementations."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from imwatermark import WatermarkDecoder, WatermarkEncoder

from attacks import apply_attack
from payload import (
    REPEAT_FACTOR,
    bit_error_rate,
    decode_payload,
    stable_hash_int,
)
from verify import build_database, encode_for_row
from watermark import load_rgb, psnr, ssim


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
META = DATASET_DIR / "metadata_all.csv"
OUT = SCRIPT_DIR / "results_external_baselines"

ATTACKS = [
    ("clean", {}),
    ("jpeg", {"quality": 50}),
    ("crop", {"ratio": 0.9}),
    ("blur", {"ksize": 3}),
    ("screenshot", {}),
    ("crop_resize_jpeg", {"crop_ratio": 0.9, "scale": 0.8, "jpeg_quality": 70}),
]


def load_rows():
    with META.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def bits_to_string(bits):
    return "".join("1" if int(bit) else "0" for bit in bits)


def decode_external(image_rgb, method, num_bits):
    bgr = cv2.cvtColor(image_rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
    decoder = WatermarkDecoder("bits", num_bits)
    if method == "rivaGan":
        decoder.loadModel()
    return [int(x) for x in decoder.decode(bgr, method)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-pos", type=int, default=50)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    positives = [r for r in rows if r["sample_group"] == "positive"]
    if args.limit_pos > 0:
        positives = positives[: args.limit_pos]
    database = build_database(rows, DATASET_DIR)

    detail = []
    for index, row in enumerate(positives, 1):
        image = load_rgb(DATASET_DIR / row["relative_path"], size=512)
        _, coded_bits = encode_for_row(row, repeat=REPEAT_FACTOR, mode="rs_repeat")
        coded_string = bits_to_string(coded_bits)
        generation_hash = stable_hash_int(row["generation_id"], 48)
        payload32 = [
            int(bit) for bit in bits_to_string(
                [(stable_hash_int(row["generation_id"], 32) >> (31 - i)) & 1 for i in range(32)]
            )
        ]

        for method in ["dwtDct", "dwtDctSvd"]:
            encoder = WatermarkEncoder()
            encoder.set_by_bits(list(coded_bits))
            bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            encoded = encoder.encode(bgr, method)
            encoded_rgb = cv2.cvtColor(encoded, cv2.COLOR_BGR2RGB)
            for attack_name, params in ATTACKS:
                attacked = apply_attack(encoded_rgb, attack_name, params)
                extracted = decode_external(attacked, method, len(coded_bits))
                decoded = decode_payload(extracted, repeat=REPEAT_FACTOR, mode="rs_repeat")
                detail.append(
                    {
                        "generation_id": row["generation_id"],
                        "method": method,
                        "payload_bits": len(coded_bits),
                        "attack": attack_name,
                        "params": json.dumps(params, ensure_ascii=False),
                        "psnr": psnr(image, encoded_rgb) if attack_name == "clean" else "",
                        "ssim": ssim(image, encoded_rgb) if attack_name == "clean" else "",
                        "ber": bit_error_rate(coded_bits, extracted),
                        "rs_success": int(decoded.rs_success),
                        "crc_ok": int(decoded.crc_ok),
                        "generation_match": int(decoded.generation_id == generation_hash),
                        "success": int(
                            decoded.rs_success
                            and decoded.crc_ok
                            and decoded.generation_id == generation_hash
                        ),
                    }
                )

        encoder = WatermarkEncoder()
        encoder.set_by_bits(payload32)
        encoder.loadModel()
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        encoded = encoder.encode(bgr, "rivaGan")
        encoded_rgb = cv2.cvtColor(encoded, cv2.COLOR_BGR2RGB)
        for attack_name, params in ATTACKS:
            attacked = apply_attack(encoded_rgb, attack_name, params)
            extracted = decode_external(attacked, "rivaGan", 32)
            ber = bit_error_rate(payload32, extracted)
            detail.append(
                {
                    "generation_id": row["generation_id"],
                    "method": "rivaGan",
                    "payload_bits": 32,
                    "attack": attack_name,
                    "params": json.dumps(params, ensure_ascii=False),
                    "psnr": psnr(image, encoded_rgb) if attack_name == "clean" else "",
                    "ssim": ssim(image, encoded_rgb) if attack_name == "clean" else "",
                    "ber": ber,
                    "rs_success": "",
                    "crc_ok": "",
                    "generation_match": "",
                    "success": int(ber < 0.1),
                }
            )
        if index % 10 == 0:
            print(f"positive {index}/{len(positives)}")

    fields = [
        "generation_id",
        "method",
        "payload_bits",
        "attack",
        "params",
        "psnr",
        "ssim",
        "ber",
        "rs_success",
        "crc_ok",
        "generation_match",
        "success",
    ]
    with (OUT / "external_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(detail)

    grouped = defaultdict(list)
    for row in detail:
        grouped[(row["method"], row["attack"])].append(row)
    summary = {}
    for (method, attack), selected in grouped.items():
        summary[f"{method}:{attack}"] = {
            "count": len(selected),
            "mean_psnr": np.mean(
                [float(r["psnr"]) for r in selected if r["psnr"] != ""]
            )
            if any(r["psnr"] != "" for r in selected)
            else None,
            "mean_ssim": np.mean(
                [float(r["ssim"]) for r in selected if r["ssim"] != ""]
            )
            if any(r["ssim"] != "" for r in selected)
            else None,
            "mean_ber": float(np.mean([float(r["ber"]) for r in selected])),
            "success_rate": float(np.mean([int(r["success"]) for r in selected])),
        }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
