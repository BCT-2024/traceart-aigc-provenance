#!/usr/bin/env python3
"""Calibrate trust-score thresholds from positive and negative score distributions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

from attacks import apply_attack
from verify import build_database, verify_image
from watermark import load_rgb


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
META = DATASET_DIR / "metadata_all.csv"
OUT = SCRIPT_DIR / "results_threshold_calibration"

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


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_rows():
    with META.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_positive_scores(full_results, combined_results):
    scores = []
    for path in [
        Path(full_results) / "robustness_detail.csv",
        Path(combined_results) / "combined_detail.csv",
    ]:
        if not path.exists():
            continue
        for row in load_csv(path):
            scores.append(
                {
                    "attack": row["attack"],
                    "params": row["params"],
                    "score": float(row["score"]),
                }
            )
    return scores


def generate_negative_scores(limit_neg=0):
    rows = load_rows()
    negatives = [r for r in rows if r["sample_group"] in ("negative_ai", "natural")]
    if limit_neg > 0:
        negatives = negatives[:limit_neg]
    database = build_database(rows, DATASET_DIR)
    output = []
    for index, row in enumerate(negatives, 1):
        image = load_rgb(DATASET_DIR / row["relative_path"], size=512)
        for attack_name, params in SINGLE_ATTACKS + COMBINED_ATTACKS:
            attacked = apply_attack(image, attack_name, params)
            result = verify_image(
                attacked,
                database,
                seed=20260910,
                repeat=4,
                carrier="dwt_dct",
                mode="rs_repeat",
                verification_mode="joint",
            )
            output.append(
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
        if index % 10 == 0:
            print(f"negative {index}/{len(negatives)}")
    return output


def main(limit_neg=0, full_results=None, combined_results=None, output_dir=None):
    out_dir = Path(output_dir) if output_dir else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    positive = load_positive_scores(
        full_results or (SCRIPT_DIR / "results_full"),
        combined_results or (SCRIPT_DIR / "results_combined"),
    )
    negative_path = out_dir / "negative_scores.csv"
    if negative_path.exists():
        negative = load_csv(negative_path)
    else:
        negative = generate_negative_scores(limit_neg=limit_neg)
        with negative_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "generation_id",
                    "sample_group",
                    "attack",
                    "params",
                    "score",
                    "trust",
                    "false_positive",
                ],
            )
            writer.writeheader()
            writer.writerows(negative)

    y_positive = np.ones(len(positive))
    y_negative = np.zeros(len(negative))
    scores_positive = np.array([row["score"] for row in positive], dtype=float)
    scores_negative = np.array([row["score"] for row in negative], dtype=float)
    y_true = np.concatenate([y_positive, y_negative])
    y_score = np.concatenate([scores_positive, scores_negative])

    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    auc = roc_auc_score(y_true, y_score)

    target_fprs = [0.10, 0.05, 0.02, 0.01, 0.005, 0.001]
    calibration = []
    for target in target_fprs:
        threshold = float(np.quantile(scores_negative, 1 - target))
        achieved_fpr = float(np.mean(scores_negative >= threshold))
        achieved_tpr = float(np.mean(scores_positive >= threshold))
        calibration.append(
            {
                "target_fpr": target,
                "threshold": threshold,
                "achieved_fpr": achieved_fpr,
                "achieved_tpr": achieved_tpr,
            }
        )

    current = []
    for label, threshold in [("current_medium", 0.55), ("current_high", 0.75)]:
        current.append(
            {
                "threshold_name": label,
                "threshold": threshold,
                "fpr": float(np.mean(scores_negative >= threshold)),
                "tpr": float(np.mean(scores_positive >= threshold)),
            }
        )

    with (out_dir / "threshold_calibration.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "target_fpr",
                "threshold",
                "achieved_fpr",
                "achieved_tpr",
            ],
        )
        writer.writeheader()
        writer.writerows(calibration)

    calibrated = {
        "auc": float(auc),
        "positive_scores": len(scores_positive),
        "negative_scores": len(scores_negative),
        "high_threshold": next(
            row["threshold"] for row in calibration if row["target_fpr"] == 0.001
        ),
        "medium_threshold": next(
            row["threshold"] for row in calibration if row["target_fpr"] == 0.01
        ),
        "calibration": calibration,
        "current_thresholds": current,
    }
    (out_dir / "calibrated_thresholds.json").write_text(
        json.dumps(calibrated, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#4C78A8", label=f"AUC={auc:.6f}")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "roc_curve.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(scores_positive, bins=40, alpha=0.6, label="Positive", color="#54A24B")
    ax.hist(scores_negative, bins=40, alpha=0.6, label="Negative", color="#E45756")
    ax.set_xlabel("Trust score")
    ax.set_ylabel("Count")
    ax.set_title("Score distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "score_distribution.png", dpi=220)
    plt.close(fig)

    lines = [
        "# 阈值校准报告",
        "",
        f"- Positive score samples: {len(scores_positive)}",
        f"- Negative score samples: {len(scores_negative)}",
        f"- ROC AUC: {auc:.6f}",
        f"- Calibrated high threshold (target FPR 0.001): {calibrated['high_threshold']:.6f}",
        f"- Calibrated medium threshold (target FPR 0.01): {calibrated['medium_threshold']:.6f}",
        "",
        "## Target FPR",
        "",
        "| Target FPR | Threshold | Achieved FPR | Achieved TPR |",
        "|---:|---:|---:|---:|",
    ]
    for row in calibration:
        lines.append(
            f"| {row['target_fpr']:.3f} | {row['threshold']:.6f} | "
            f"{row['achieved_fpr']:.6f} | {row['achieved_tpr']:.6f} |"
        )
    lines += [
        "",
        "## Current thresholds",
        "",
        "| Threshold | FPR | TPR |",
        "|---|---:|---:|",
    ]
    for row in current:
        lines.append(
            f"| {row['threshold_name']}={row['threshold']:.2f} | "
            f"{row['fpr']:.6f} | {row['tpr']:.6f} |"
        )
    lines += [
        "",
        "## Figures",
        "",
        "![roc](roc_curve.png)",
        "",
        "![distribution](score_distribution.png)",
        "",
    ]
    (out_dir / "calibration_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(calibrated, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-neg", type=int, default=0)
    parser.add_argument(
        "--full-results",
        default=str(SCRIPT_DIR / "results_full"),
    )
    parser.add_argument(
        "--combined-results",
        default=str(SCRIPT_DIR / "results_combined"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUT),
    )
    args = parser.parse_args()
    main(
        limit_neg=args.limit_neg,
        full_results=args.full_results,
        combined_results=args.combined_results,
        output_dir=args.output_dir,
    )
