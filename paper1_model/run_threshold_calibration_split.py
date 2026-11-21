#!/usr/bin/env python3
"""Image-disjoint calibration and held-out evaluation for trust thresholds."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
META = DATASET_DIR / "metadata_all.csv"
DEFAULT_OUT = SCRIPT_DIR / "results_threshold_calibration_split_alpha28"
TARGET_FPRS = (0.10, 0.05, 0.02, 0.01, 0.005, 0.001)


def load_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def stratified_ids(id_to_stratum, calibration_fraction, seed):
    """Split unique image IDs into image-disjoint calibration and test sets."""

    strata = defaultdict(list)
    for image_id, stratum in id_to_stratum.items():
        strata[stratum].append(image_id)

    rng = np.random.default_rng(seed)
    target_calibration = int(round(len(id_to_stratum) * calibration_fraction))
    quotas = {}
    remainders = []
    for stratum in sorted(strata):
        ids = sorted(strata[stratum])
        rng.shuffle(ids)
        strata[stratum] = ids
        exact = len(ids) * calibration_fraction
        quota = int(np.floor(exact))
        quotas[stratum] = quota
        remainders.append((exact - quota, stratum))

    remaining = target_calibration - sum(quotas.values())
    for _, stratum in sorted(remainders, reverse=True)[:remaining]:
        quotas[stratum] += 1

    calibration = set()
    for stratum in sorted(strata):
        calibration.update(strata[stratum][: quotas[stratum]])
    evaluation = set(id_to_stratum) - calibration
    return calibration, evaluation, quotas


def scores_for(rows, metric="score"):
    return np.asarray([float(row[metric]) for row in rows], dtype=float)


def grouped_scores(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["generation_id"]].append(float(row["score"]))
    return {
        image_id: np.asarray(values, dtype=float)
        for image_id, values in grouped.items()
    }


def bootstrap_auc(positive_groups, negative_groups, seed, replicates):
    rng = np.random.default_rng(seed)
    positive_ids = np.asarray(sorted(positive_groups))
    negative_ids = np.asarray(sorted(negative_groups))
    aucs = []
    for _ in range(replicates):
        sampled_positive = rng.choice(positive_ids, size=len(positive_ids), replace=True)
        sampled_negative = rng.choice(negative_ids, size=len(negative_ids), replace=True)
        positive_scores = np.concatenate(
            [positive_groups[image_id] for image_id in sampled_positive]
        )
        negative_scores = np.concatenate(
            [negative_groups[image_id] for image_id in sampled_negative]
        )
        labels = np.concatenate(
            [
                np.ones(len(positive_scores), dtype=int),
                np.zeros(len(negative_scores), dtype=int),
            ]
        )
        scores = np.concatenate([positive_scores, negative_scores])
        aucs.append(float(roc_auc_score(labels, scores)))
    return np.asarray(aucs, dtype=float)


def operating_point(positive_scores, negative_scores, threshold):
    return {
        "threshold": float(threshold),
        "tpr": float(np.mean(positive_scores >= threshold)),
        "fpr": float(np.mean(negative_scores >= threshold)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full-results",
        default=str(SCRIPT_DIR / "results_full_capture_scan"),
    )
    parser.add_argument(
        "--combined-results",
        default=str(SCRIPT_DIR / "results_combined_alpha28"),
    )
    parser.add_argument(
        "--negative-scores",
        default=str(
            SCRIPT_DIR
            / "results_threshold_calibration_alpha28"
            / "negative_scores.csv"
        ),
    )
    parser.add_argument("--calibration-fraction", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    if not 0.0 < args.calibration_fraction < 1.0:
        raise ValueError("--calibration-fraction must be between 0 and 1")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_csv(META)
    positive_strata = {
        row["generation_id"]: row.get("category", "unknown")
        for row in metadata
        if row["sample_group"] == "positive"
    }
    negative_strata = {
        row["generation_id"]: row["sample_group"]
        for row in metadata
        if row["sample_group"] in ("negative_ai", "natural")
    }
    positive_cal_ids, positive_test_ids, positive_quotas = stratified_ids(
        positive_strata, args.calibration_fraction, args.seed
    )
    negative_cal_ids, negative_test_ids, negative_quotas = stratified_ids(
        negative_strata, args.calibration_fraction, args.seed + 1
    )

    positive_rows = []
    for path in (
        Path(args.full_results) / "robustness_detail.csv",
        Path(args.combined_results) / "combined_detail.csv",
    ):
        positive_rows.extend(load_csv(path))
    positive_rows = [
        row
        for row in positive_rows
        if row["attack"] not in {"real_screen_capture", "print_scan"}
    ]
    negative_rows = load_csv(args.negative_scores)

    positive_cal = [
        row for row in positive_rows if row["generation_id"] in positive_cal_ids
    ]
    positive_test = [
        row for row in positive_rows if row["generation_id"] in positive_test_ids
    ]
    negative_cal = [
        row for row in negative_rows if row["generation_id"] in negative_cal_ids
    ]
    negative_test = [
        row for row in negative_rows if row["generation_id"] in negative_test_ids
    ]

    calibration = {
        "positive_scores": scores_for(positive_cal),
        "negative_scores": scores_for(negative_cal),
    }
    evaluation = {
        "positive_scores": scores_for(positive_test),
        "negative_scores": scores_for(negative_test),
    }

    summary = {
        "config": {
            "alpha": 28.0,
            "calibration_fraction": args.calibration_fraction,
            "split_seed": args.seed,
            "bootstrap_replicates": args.bootstrap_replicates,
            "positive_images_calibration": len(positive_cal_ids),
            "positive_images_test": len(positive_test_ids),
            "negative_images_calibration": len(negative_cal_ids),
            "negative_images_test": len(negative_test_ids),
            "positive_score_observations_calibration": len(positive_cal),
            "positive_score_observations_test": len(positive_test),
            "negative_score_observations_calibration": len(negative_cal),
            "negative_score_observations_test": len(negative_test),
            "positive_stratum_quotas": positive_quotas,
            "negative_stratum_quotas": negative_quotas,
        },
        "calibration": {},
        "held_out": {},
        "threshold_transfer": [],
        "operational_thresholds": [],
    }

    for split_name, split in (("calibration", calibration), ("held_out", evaluation)):
        labels = np.concatenate(
            [
                np.ones(len(split["positive_scores"]), dtype=int),
                np.zeros(len(split["negative_scores"]), dtype=int),
            ]
        )
        scores = np.concatenate(
            [split["positive_scores"], split["negative_scores"]]
        )
        fpr, tpr, _ = roc_curve(labels, scores)
        auc = float(roc_auc_score(labels, scores))
        summary[split_name]["auc"] = auc
        summary[split_name]["roc"] = [
            {"fpr": float(x), "tpr": float(y)} for x, y in zip(fpr, tpr)
        ]

        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        ax.plot(fpr, tpr, color="#4C78A8", label=f"AUC={auc:.6f}")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title(f"ROC: {split_name.replace('_', '-')}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / f"roc_{split_name}.png", dpi=300)
        plt.close(fig)

    for target in TARGET_FPRS:
        threshold = float(
            np.quantile(
                calibration["negative_scores"],
                1.0 - target,
                method="higher",
            )
        )
        calibration_point = operating_point(
            calibration["positive_scores"],
            calibration["negative_scores"],
            threshold,
        )
        held_out_point = operating_point(
            evaluation["positive_scores"],
            evaluation["negative_scores"],
            threshold,
        )
        summary["threshold_transfer"].append(
            {
                "target_fpr": target,
                "threshold": threshold,
                "calibration_tpr": calibration_point["tpr"],
                "calibration_fpr": calibration_point["fpr"],
                "held_out_tpr": held_out_point["tpr"],
                "held_out_fpr": held_out_point["fpr"],
            }
        )

    for name, threshold in (("operational_high", 0.55), ("operational_medium", 0.32)):
        summary["operational_thresholds"].append(
            {
                "name": name,
                **operating_point(
                    evaluation["positive_scores"],
                    evaluation["negative_scores"],
                    threshold,
                ),
            }
        )

    positive_groups_cal = grouped_scores(positive_cal)
    negative_groups_cal = grouped_scores(negative_cal)
    positive_groups_test = grouped_scores(positive_test)
    negative_groups_test = grouped_scores(negative_test)
    bootstrap_cal = bootstrap_auc(
        positive_groups_cal,
        negative_groups_cal,
        args.seed + 10,
        args.bootstrap_replicates,
    )
    bootstrap_test = bootstrap_auc(
        positive_groups_test,
        negative_groups_test,
        args.seed + 11,
        args.bootstrap_replicates,
    )
    summary["calibration"]["auc_cluster_bootstrap_95ci"] = [
        float(np.quantile(bootstrap_cal, 0.025)),
        float(np.quantile(bootstrap_cal, 0.975)),
    ]
    summary["held_out"]["auc_cluster_bootstrap_95ci"] = [
        float(np.quantile(bootstrap_test, 0.025)),
        float(np.quantile(bootstrap_test, 0.975)),
    ]

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fields = [
        "generation_id",
        "sample_kind",
        "stratum",
        "split",
        "score_observations",
    ]
    split_rows = []
    for image_id, stratum in sorted(positive_strata.items()):
        split_rows.append(
            {
                "generation_id": image_id,
                "sample_kind": "positive",
                "stratum": stratum,
                "split": "calibration"
                if image_id in positive_cal_ids
                else "held_out",
                "score_observations": sum(
                    row["generation_id"] == image_id for row in positive_rows
                ),
            }
        )
    for image_id, stratum in sorted(negative_strata.items()):
        split_rows.append(
            {
                "generation_id": image_id,
                "sample_kind": stratum,
                "stratum": stratum,
                "split": "calibration"
                if image_id in negative_cal_ids
                else "held_out",
                "score_observations": sum(
                    row["generation_id"] == image_id for row in negative_rows
                ),
            }
        )
    with (out_dir / "split_assignments.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(split_rows)

    transfer_fields = [
        "target_fpr",
        "threshold",
        "calibration_tpr",
        "calibration_fpr",
        "held_out_tpr",
        "held_out_fpr",
    ]
    with (out_dir / "threshold_transfer.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=transfer_fields)
        writer.writeheader()
        writer.writerows(summary["threshold_transfer"])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = np.linspace(0, 1, 41)
    ax.hist(
        evaluation["positive_scores"],
        bins=bins,
        alpha=0.6,
        label="Held-out positive",
        color="#54A24B",
    )
    ax.hist(
        evaluation["negative_scores"],
        bins=bins,
        alpha=0.6,
        label="Held-out negative",
        color="#E45756",
    )
    ax.set_xlabel("Trust score")
    ax.set_ylabel("Observations")
    ax.set_title("Held-out score distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "held_out_score_distribution.png", dpi=300)
    plt.close(fig)

    report = [
        "# Image-Disjoint Threshold Calibration",
        "",
        "## Split",
        "",
        f"- Calibration positive images: {len(positive_cal_ids)}",
        f"- Held-out positive images: {len(positive_test_ids)}",
        f"- Calibration negative images: {len(negative_cal_ids)}",
        f"- Held-out negative images: {len(negative_test_ids)}",
        f"- Calibration positive observations: {len(positive_cal)}",
        f"- Held-out positive observations: {len(positive_test)}",
        f"- Calibration negative observations: {len(negative_cal)}",
        f"- Held-out negative observations: {len(negative_test)}",
        "",
        "## AUC",
        "",
        f"- Calibration AUC: {summary['calibration']['auc']:.6f} "
        f"(cluster bootstrap 95% CI "
        f"{summary['calibration']['auc_cluster_bootstrap_95ci'][0]:.6f}--"
        f"{summary['calibration']['auc_cluster_bootstrap_95ci'][1]:.6f})",
        f"- Held-out AUC: {summary['held_out']['auc']:.6f} "
        f"(cluster bootstrap 95% CI "
        f"{summary['held_out']['auc_cluster_bootstrap_95ci'][0]:.6f}--"
        f"{summary['held_out']['auc_cluster_bootstrap_95ci'][1]:.6f})",
        "",
        "## Threshold transfer",
        "",
        "| Target FPR | Threshold | Cal FPR | Cal TPR | Test FPR | Test TPR |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["threshold_transfer"]:
        report.append(
            f"| {row['target_fpr']:.3f} | {row['threshold']:.6f} | "
            f"{row['calibration_fpr']:.4f} | {row['calibration_tpr']:.4f} | "
            f"{row['held_out_fpr']:.4f} | {row['held_out_tpr']:.4f} |"
        )
    report += [
        "",
        "## Current operational thresholds on held-out data",
        "",
        "| Threshold | Value | FPR | TPR |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["operational_thresholds"]:
        report.append(
            f"| {row['name']} | {row['threshold']:.2f} | "
            f"{row['fpr']:.4f} | {row['tpr']:.4f} |"
        )
    report += [
        "",
        "The split is by generation image, so attack variants of the same image",
        "never cross the calibration and held-out sets.",
        "",
        "![calibration ROC](roc_calibration.png)",
        "",
        "![held-out ROC](roc_held_out.png)",
        "",
        "![held-out scores](held_out_score_distribution.png)",
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
