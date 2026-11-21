#!/usr/bin/env python3
"""Threshold sensitivity analysis for extremely flat images.

The analysis separates three questions:
1. Can a legitimate flat image still pass content binding after attacks?
2. Can a copied watermark on another flat image be rejected?
3. How does the threshold trade off TPR and FPR when ORB keypoints are scarce
   and the verifier falls back to the average hash?
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

from attacks import apply_attack
from payload import build_payload, encode_payload
from verify import (
    CONTENT_BINDING_FLAT_THRESHOLD,
    CONTENT_BINDING_THRESHOLD,
    DatabaseRecord,
    _orb_features,
    average_hash,
    content_binding_details,
    flat_signature,
    stable_hash_int,
    timestamp_hours,
)
from watermark import embed_bits


SCRIPT_DIR = Path(__file__).resolve().parent
OUT = SCRIPT_DIR / "results_flat_sensitivity"
CREATED_AT = "2026-09-15T12:00:00+08:00"
PLATFORM_ID = "FlatLab"
MODEL_VERSION = "flat-sim"
ATTACKS = [
    ("clean", {}),
    ("jpeg", {"quality": 70}),
    ("real_screen_capture", {}),
    ("print_scan", {}),
]


def solid(color):
    return np.full((512, 512, 3), color, dtype=np.uint8)


def gradient(start, end, direction="horizontal"):
    if direction == "horizontal":
        values = np.tile(
            np.linspace(0, 1, 512, dtype=np.float32)[None, :, None],
            (512, 1, 1),
        )
    elif direction == "vertical":
        values = np.tile(
            np.linspace(0, 1, 512, dtype=np.float32)[:, None, None],
            (1, 512, 1),
        )
    else:
        x = np.linspace(0, 1, 512, dtype=np.float32)[None, :, None]
        y = np.linspace(0, 1, 512, dtype=np.float32)[:, None, None]
        values = (x + y) / 2.0
    start = np.asarray(start, dtype=np.float32)[None, None, :]
    end = np.asarray(end, dtype=np.float32)[None, None, :]
    return np.clip(start + (end - start) * values, 0, 255).astype(np.uint8)


def large_blocks(colors):
    image = np.zeros((512, 512, 3), dtype=np.uint8)
    cells = 4
    size = 512 // cells
    for row in range(cells):
        for col in range(cells):
            color = colors[(row * cells + col) % len(colors)]
            image[row * size : (row + 1) * size, col * size : (col + 1) * size] = color
    return image


def simple_shapes():
    image = np.full((512, 512, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (80, 80), (240, 240), (180, 180, 180), thickness=-1)
    cv2.circle(image, (360, 340), 90, (210, 205, 200), thickness=-1)
    return image


def soft_sky():
    image = gradient((120, 160, 220), (230, 240, 250), "vertical")
    x = np.linspace(-1, 1, 512, dtype=np.float32)[None, :, None]
    image = np.clip(image.astype(np.float32) + 8.0 * x, 0, 255).astype(np.uint8)
    return image


def image_sha256(image):
    return hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()


def flatness_metrics(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    _, keypoints = _orb_features(image)
    return {
        "gray_std": float(gray.std()),
        "gray_range": int(gray.max() - gray.min()),
        "edge_density": float(np.count_nonzero(edges) / edges.size),
        "orb_keypoints": int(keypoints),
    }


def make_record(image, index):
    sha = image_sha256(image)
    descriptors, keypoints = _orb_features(image)
    return DatabaseRecord(
        generation_id=f"flat-{index:02d}",
        generation_id_hash=stable_hash_int(f"flat-{index:02d}", 48),
        platform_id=PLATFORM_ID,
        platform_hash=stable_hash_int(PLATFORM_ID, 8),
        model_version=MODEL_VERSION,
        model_hash=stable_hash_int(MODEL_VERSION, 8),
        created_at=CREATED_AT,
        timestamp=timestamp_hours(CREATED_AT),
        content_sha256=sha,
        content_hash=stable_hash_int(sha, 16),
        average_hash=average_hash(image),
        flat_signature=flat_signature(image),
        orb_descriptors=descriptors,
        orb_keypoint_count=keypoints,
    )


def build_flat_images():
    return [
        ("solid_white", solid((255, 255, 255))),
        ("solid_gray", solid((128, 128, 128))),
        ("solid_black", solid((0, 0, 0))),
        ("solid_red", solid((200, 60, 60))),
        ("solid_blue", solid((60, 100, 200))),
        ("low_gradient_gray", gradient((118, 118, 118), (132, 132, 132))),
        ("low_gradient_sky", gradient((180, 200, 220), (200, 215, 230), "vertical")),
        ("large_blocks_similar", large_blocks([(120, 120, 120), (126, 126, 126)])),
        ("large_blocks_distinct", large_blocks([(220, 60, 60), (60, 140, 220)])),
        ("simple_shapes", simple_shapes()),
        ("soft_sky", soft_sky()),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=28.0)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--repeat", type=int, default=4)
    parser.add_argument("--output-dir", default=str(OUT))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images = build_flat_images()
    records = [make_record(image, index) for index, (_, image) in enumerate(images)]

    positive_rows = []
    copy_rows = []
    for index, ((name, image), record) in enumerate(zip(images, records)):
        payload = build_payload(
            platform_id=PLATFORM_ID,
            generation_id=record.generation_id,
            model_version=MODEL_VERSION,
            created_at=CREATED_AT,
            content_sha256=record.content_sha256,
        )
        coded = encode_payload(payload, repeat=args.repeat, mode="rs_repeat")
        watermarked = embed_bits(
            image,
            coded,
            seed=args.seed,
            alpha=args.alpha,
            carrier="dwt_dct",
        )
        metrics = flatness_metrics(image)
        for attack_name, params in ATTACKS:
            attacked = apply_attack(watermarked, attack_name, params)
            details = content_binding_details(attacked, record)
            positive_rows.append(
                {
                    "image": name,
                    "attack": attack_name,
                    "score": details["score"],
                    "method": details["method"],
                    "query_keypoints": details["query_keypoints"],
                    "reference_keypoints": details["reference_keypoints"],
                    "good_matches": details["good_matches"],
                    **metrics,
                }
            )

        target_name, target = images[(index + 1) % len(images)]
        forged = embed_bits(
            target,
            coded,
            seed=args.seed,
            alpha=args.alpha,
            carrier="dwt_dct",
        )
        details = content_binding_details(forged, record)
        copy_rows.append(
            {
                "donor": name,
                "target": target_name,
                "score": details["score"],
                "method": details["method"],
                "query_keypoints": details["query_keypoints"],
                "reference_keypoints": details["reference_keypoints"],
                "good_matches": details["good_matches"],
                **metrics,
            }
        )

    thresholds = np.round(np.arange(0.05, 1.0, 0.05), 2)
    sensitivity = []
    positive_scores = np.array([row["score"] for row in positive_rows], dtype=float)
    copy_scores = np.array([row["score"] for row in copy_rows], dtype=float)
    for threshold in thresholds:
        tpr = float(np.mean(positive_scores >= threshold))
        fpr = float(np.mean(copy_scores >= threshold))
        sensitivity.append(
            {
                "threshold": float(threshold),
                "tpr": tpr,
                "fpr": fpr,
                "youden_j": tpr - fpr,
                "balanced_accuracy": (tpr + (1.0 - fpr)) / 2.0,
            }
        )
    best = max(sensitivity, key=lambda row: (row["youden_j"], row["threshold"]))

    with (output_dir / "flat_positive_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(positive_rows[0].keys()))
        writer.writeheader()
        writer.writerows(positive_rows)
    with (output_dir / "flat_copy_detail.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=list(copy_rows[0].keys()))
        writer.writeheader()
        writer.writerows(copy_rows)
    with (output_dir / "threshold_sensitivity.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["threshold", "tpr", "fpr", "youden_j", "balanced_accuracy"],
        )
        writer.writeheader()
        writer.writerows(sensitivity)

    fallback_rate = float(
        np.mean([row["method"] == "flat_signature_fallback" for row in positive_rows])
    )
    summary = {
        "config": {
            "images": len(images),
            "positive_samples": len(positive_rows),
            "copy_samples": len(copy_rows),
            "attacks": [name for name, _ in ATTACKS],
            "alpha": args.alpha,
            "repeat": args.repeat,
            "default_threshold": CONTENT_BINDING_THRESHOLD,
        },
        "flatness": {
            name: flatness_metrics(image) for name, image in images
        },
        "fallback_rate_positive": fallback_rate,
        "recommended_threshold": best,
        "adaptive_policy": {
            "normal_threshold": CONTENT_BINDING_THRESHOLD,
            "flat_threshold": CONTENT_BINDING_FLAT_THRESHOLD,
            "flat_result": next(
                row
                for row in sensitivity
                if abs(row["threshold"] - CONTENT_BINDING_FLAT_THRESHOLD) < 1e-9
            ),
        },
        "default_threshold_result": next(
            row
            for row in sensitivity
            if abs(row["threshold"] - CONTENT_BINDING_THRESHOLD) < 1e-9
        ),
        "score_ranges": {
            "positive_min": float(positive_scores.min()),
            "positive_max": float(positive_scores.max()),
            "copy_min": float(copy_scores.min()),
            "copy_max": float(copy_scores.max()),
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(thresholds, [row["tpr"] for row in sensitivity], marker="o", label="TPR")
    ax.plot(thresholds, [row["fpr"] for row in sensitivity], marker="s", label="FPR")
    ax.axvline(
        CONTENT_BINDING_THRESHOLD,
        color="#E45756",
        linestyle="--",
        label=f"default={CONTENT_BINDING_THRESHOLD}",
    )
    ax.set_xlabel("Content-binding threshold")
    ax.set_ylabel("Rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Flat-image threshold sensitivity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "threshold_sensitivity.png", dpi=220)
    plt.close(fig)

    lines = [
        "# 极端平坦图像内容绑定阈值敏感性",
        "",
        "## 实验配置",
        "",
        f"- 平坦图像：{len(images)} 张",
        f"- 正样本攻击测试：{len(positive_rows)} 条",
        f"- 复制攻击测试：{len(copy_rows)} 条",
        f"- 攻击类型：{', '.join(name for name, _ in ATTACKS)}",
        f"- 默认阈值：{CONTENT_BINDING_THRESHOLD}",
        "",
        "## ORB 回退情况",
        "",
        f"- 正样本使用平均哈希回退的比例：{fallback_rate:.4f}",
        "",
        "## 分数范围",
        "",
        f"- 正样本最低/最高：{positive_scores.min():.4f} / {positive_scores.max():.4f}",
        f"- 复制攻击最低/最高：{copy_scores.min():.4f} / {copy_scores.max():.4f}",
        "",
        "## 阈值推荐",
        "",
        f"- 推荐阈值：{best['threshold']:.2f}",
        f"- 对应 TPR：{best['tpr']:.4f}",
        f"- 对应 FPR：{best['fpr']:.4f}",
        f"- Youden J：{best['youden_j']:.4f}",
        "",
        "## 默认阈值结果",
        "",
        f"- 默认阈值：{CONTENT_BINDING_THRESHOLD}",
        f"- TPR：{summary['default_threshold_result']['tpr']:.4f}",
        f"- FPR：{summary['default_threshold_result']['fpr']:.4f}",
        "",
        "## 自适应策略",
        "",
        f"- 正常纹理图像阈值：{CONTENT_BINDING_THRESHOLD}",
        f"- 平坦图像回退阈值：{CONTENT_BINDING_FLAT_THRESHOLD}",
        f"- 平坦图像 TPR：{summary['adaptive_policy']['flat_result']['tpr']:.4f}",
        f"- 平坦图像 FPR：{summary['adaptive_policy']['flat_result']['fpr']:.4f}",
        "",
        "![sensitivity](threshold_sensitivity.png)",
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
