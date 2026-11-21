#!/usr/bin/env python3
"""Copy/transplant attack evaluation with and without content binding.

Threat model:
    The attacker takes a valid structured payload from a registered positive
    image and embeds it into an unregistered negative image.  Without content
    binding, CRC/RS/generation matching can still accept the forged image.
    With content binding, the verifier must also match local image content to
    the registration record.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from itertools import cycle
from pathlib import Path

from attacks import apply_attack
from verify import (
    CONTENT_BINDING_THRESHOLD,
    build_database,
    encode_for_row,
    verify_image,
)
from watermark import embed_bits, load_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
META = DATASET_DIR / "metadata_all.csv"
OUT = SCRIPT_DIR / "results_copy_attack"

POSITIVE_CONTROL_ATTACKS = [
    ("clean", {}),
    ("jpeg", {"quality": 70}),
    ("crop", {"ratio": 0.9}),
    ("screenshot", {}),
    ("real_screen_capture", {}),
    ("print_scan", {}),
    ("crop_resize_jpeg", {"crop_ratio": 0.9, "scale": 0.8, "jpeg_quality": 70}),
]


def load_rows():
    with META.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def serialize_attack(params: dict) -> str:
    return json.dumps(params, ensure_ascii=False, sort_keys=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-pos", type=int, default=50)
    parser.add_argument("--limit-neg", type=int, default=50)
    parser.add_argument("--alpha", type=float, default=28.0)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--repeat", type=int, default=4)
    parser.add_argument("--carrier", default="dwt_dct")
    parser.add_argument("--payload-mode", default="rs_repeat")
    parser.add_argument("--content-binding-threshold", type=float, default=CONTENT_BINDING_THRESHOLD)
    parser.add_argument("--output-dir", default=str(OUT))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows()
    database = build_database(rows, DATASET_DIR)
    positives = [r for r in rows if r["sample_group"] == "positive"]
    negatives = [
        r for r in rows if r["sample_group"] in ("negative_ai", "natural")
    ]
    if args.limit_pos > 0:
        positives = positives[: args.limit_pos]
    if args.limit_neg > 0:
        negatives = negatives[: args.limit_neg]
    if not positives or not negatives:
        raise RuntimeError("Both positive donors and negative targets are required.")

    copy_detail = []
    for index, negative in enumerate(negatives, 1):
        donor = positives[(index - 1) % len(positives)]
        _, coded_bits = encode_for_row(
            donor, repeat=args.repeat, mode=args.payload_mode
        )
        target = load_rgb(DATASET_DIR / negative["relative_path"], size=512)
        forged = embed_bits(
            target,
            coded_bits,
            seed=args.seed,
            alpha=args.alpha,
            carrier=args.carrier,
        )
        for content_binding_required in (False, True):
            for verification_mode in ("watermark_only", "db_only", "joint"):
                result = verify_image(
                    forged,
                    database,
                    seed=args.seed,
                    repeat=args.repeat,
                    expected_bits=coded_bits,
                    carrier=args.carrier,
                    mode=args.payload_mode,
                    verification_mode=verification_mode,
                    content_binding_required=content_binding_required,
                    content_binding_threshold=args.content_binding_threshold,
                )
                copy_detail.append(
                    {
                        "target_generation_id": negative["generation_id"],
                        "target_group": negative["sample_group"],
                        "donor_generation_id": donor["generation_id"],
                        "content_binding_required": int(content_binding_required),
                        "verification_mode": verification_mode,
                        "accepted": int(bool(result["success"])),
                        "trust": result["trust"],
                        "score": float(result["score"]),
                        "crc_ok": int(bool(result["crc_ok"])),
                        "rs_success": int(bool(result["rs_success"])),
                        "generation_match": int(bool(result["generation_match"])),
                        "field_score": float(result["field_score"]),
                        "hash_score": float(result["hash_score"]),
                        "content_binding_score": float(result["content_binding_score"]),
                        "content_binding_ok": int(bool(result["content_binding_ok"])),
                        "matched_generation_id": result.get("matched_generation_id", ""),
                    }
                )
        if index % 10 == 0:
            print(f"copy attack {index}/{len(negatives)}")

    positive_control = []
    for index, positive in enumerate(positives, 1):
        image = load_rgb(DATASET_DIR / positive["relative_path"], size=512)
        _, coded_bits = encode_for_row(
            positive, repeat=args.repeat, mode=args.payload_mode
        )
        watermarked = embed_bits(
            image,
            coded_bits,
            seed=args.seed,
            alpha=args.alpha,
            carrier=args.carrier,
        )
        for attack_name, params in POSITIVE_CONTROL_ATTACKS:
            attacked = apply_attack(watermarked, attack_name, params)
            for content_binding_required in (False, True):
                result = verify_image(
                    attacked,
                    database,
                    seed=args.seed,
                    repeat=args.repeat,
                    expected_bits=coded_bits,
                    carrier=args.carrier,
                    mode=args.payload_mode,
                    verification_mode="joint",
                    content_binding_required=content_binding_required,
                    content_binding_threshold=args.content_binding_threshold,
                )
                positive_control.append(
                    {
                        "generation_id": positive["generation_id"],
                        "attack": attack_name,
                        "params": serialize_attack(params),
                        "content_binding_required": int(content_binding_required),
                        "success": int(bool(result["success"])),
                        "trust": result["trust"],
                        "score": float(result["score"]),
                        "content_binding_score": float(result["content_binding_score"]),
                        "content_binding_ok": int(bool(result["content_binding_ok"])),
                        "ber": result["ber"],
                    }
                )
        if index % 10 == 0:
            print(f"positive control {index}/{len(positives)}")

    copy_fields = [
        "target_generation_id",
        "target_group",
        "donor_generation_id",
        "content_binding_required",
        "verification_mode",
        "accepted",
        "trust",
        "score",
        "crc_ok",
        "rs_success",
        "generation_match",
        "field_score",
        "hash_score",
        "content_binding_score",
        "content_binding_ok",
        "matched_generation_id",
    ]
    control_fields = [
        "generation_id",
        "attack",
        "params",
        "content_binding_required",
        "success",
        "trust",
        "score",
        "content_binding_score",
        "content_binding_ok",
        "ber",
    ]
    with (output_dir / "copy_attack_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=copy_fields)
        writer.writeheader()
        writer.writerows(copy_detail)
    with (output_dir / "positive_control_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=control_fields)
        writer.writeheader()
        writer.writerows(positive_control)

    copy_summary = {}
    for binding in (0, 1):
        for mode in ("watermark_only", "db_only", "joint"):
            selected = [
                row
                for row in copy_detail
                if row["content_binding_required"] == binding
                and row["verification_mode"] == mode
            ]
            scores = [row["content_binding_score"] for row in selected]
            copy_summary[f"binding_{binding}:{mode}"] = {
                "count": len(selected),
                "acceptance_rate": sum(row["accepted"] for row in selected)
                / len(selected),
                "mean_score": sum(row["score"] for row in selected) / len(selected),
                "mean_content_binding_score": sum(scores) / len(scores),
                "min_content_binding_score": min(scores),
                "max_content_binding_score": max(scores),
                "trust_counts": dict(Counter(row["trust"] for row in selected)),
            }

    control_summary = {}
    for attack_name, params in POSITIVE_CONTROL_ATTACKS:
        key = f"{attack_name}:{serialize_attack(params)}"
        for binding in (0, 1):
            selected = [
                row
                for row in positive_control
                if row["attack"] == attack_name
                and row["params"] == serialize_attack(params)
                and row["content_binding_required"] == binding
            ]
            control_summary[f"{key}:binding_{binding}"] = {
                "count": len(selected),
                "success_rate": sum(row["success"] for row in selected)
                / len(selected),
                "mean_content_binding_score": sum(
                    row["content_binding_score"] for row in selected
                )
                / len(selected),
            }

    summary = {
        "config": {
            "alpha": args.alpha,
            "repeat": args.repeat,
            "carrier": args.carrier,
            "payload_mode": args.payload_mode,
            "content_binding_threshold": args.content_binding_threshold,
            "positive_donors": len(positives),
            "negative_targets": len(negatives),
        },
        "copy_attack": copy_summary,
        "positive_control": control_summary,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 复制攻击与内容绑定实验",
        "",
        "## 实验配置",
        "",
        f"- 正样本水印供体：{len(positives)} 张",
        f"- 负样本复制目标：{len(negatives)} 张",
        f"- 内容绑定阈值：{args.content_binding_threshold}",
        f"- 载体/编码：{args.carrier} / {args.payload_mode} / repeat={args.repeat} / alpha={args.alpha}",
        "",
        "## 复制攻击",
        "",
        "| 内容绑定 | 验证模式 | 接受率 | 平均分数 | 平均内容绑定分 | 最小/最大内容绑定分 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for binding in (0, 1):
        for mode in ("watermark_only", "db_only", "joint"):
            item = copy_summary[f"binding_{binding}:{mode}"]
            lines.append(
                f"| {'on' if binding else 'off'} | {mode} | "
                f"{item['acceptance_rate']:.4f} | {item['mean_score']:.4f} | "
                f"{item['mean_content_binding_score']:.4f} | "
                f"{item['min_content_binding_score']:.4f}/{item['max_content_binding_score']:.4f} |"
            )
    lines += [
        "",
        "## 正样本对照",
        "",
        "| 攻击 | 内容绑定 | 成功率 | 平均内容绑定分 |",
        "|---|---:|---:|---:|",
    ]
    for attack_name, params in POSITIVE_CONTROL_ATTACKS:
        key = f"{attack_name}:{serialize_attack(params)}"
        for binding in (0, 1):
            item = control_summary[f"{key}:binding_{binding}"]
            lines.append(
                f"| {attack_name} | {'on' if binding else 'off'} | "
                f"{item['success_rate']:.4f} | {item['mean_content_binding_score']:.4f} |"
            )
    lines += [
        "",
        "## 结论",
        "",
        "- 内容绑定关闭时，复制攻击会被数据库联合验证接受，说明仅靠 CRC/RS/generation_id 不足以证明水印属于当前图像。",
        "- 内容绑定开启后，复制攻击应被拒绝，同时正样本在常见攻击下保持可用。",
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
