#!/usr/bin/env python3
"""Create figures and a Markdown report from experiment outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def attack_label(row):
    params = json.loads(row["params"]) if row.get("params") else {}
    if not params:
        return row["attack"]
    return row["attack"] + " " + ",".join(f"{k}={v}" for k, v in params.items())


def main(results_dir=None):
    results = Path(results_dir) if results_dir else SCRIPT_DIR / "results_full"
    figures = results / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    quality = load_csv(results / "quality_metrics.csv")
    robustness = load_csv(results / "robustness_detail.csv")
    negatives = load_csv(results / "negative_fpr_detail.csv")
    summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))

    psnr_values = [float(row["psnr"]) for row in quality]
    ssim_values = [float(row["ssim"]) for row in quality]
    alpha_values = sorted({float(row["alpha"]) for row in quality})
    if not alpha_values:
        raise ValueError(f"No embedding-strength values found in {results}")
    alpha_text = ", ".join(f"{value:g}" for value in alpha_values)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(psnr_values, bins=20, color="#4C78A8", edgecolor="white")
    axes[0].set_title("PSNR distribution")
    axes[0].set_xlabel("PSNR (dB)")
    axes[0].set_ylabel("Images")
    axes[1].hist(ssim_values, bins=20, color="#F58518", edgecolor="white")
    axes[1].set_title("SSIM distribution")
    axes[1].set_xlabel("SSIM")
    axes[1].set_ylabel("Images")
    fig.tight_layout()
    fig.savefig(figures / "quality_distribution.png", dpi=220)
    plt.close(fig)

    grouped = defaultdict(list)
    for row in robustness:
        grouped[attack_label(row)].append(row)
    labels = list(grouped.keys())
    success = [
        sum(int(r["success"]) for r in grouped[label]) / len(grouped[label])
        for label in labels
    ]
    ber = [
        sum(float(r["ber"]) for r in grouped[label]) / len(grouped[label])
        for label in labels
    ]

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(labels))
    ax.bar(x, success, color="#54A24B")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Success rate")
    ax.set_title("Verification success under attacks")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(figures / "robustness_success.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x, ber, color="#E45756")
    ax.set_ylabel("Mean BER")
    ax.set_title("Bit error rate under attacks")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(figures / "robustness_ber.png", dpi=220)
    plt.close(fig)

    trust_levels = ["high", "medium", "low"]
    trust_counts = {
        level: [
            sum(1 for r in grouped[label] if r["trust"] == level) for label in labels
        ]
        for level in trust_levels
    }
    fig, ax = plt.subplots(figsize=(11, 5))
    bottom = np.zeros(len(labels))
    colors = {"high": "#54A24B", "medium": "#F2CF5B", "low": "#E45756"}
    for level in trust_levels:
        values = np.array(trust_counts[level])
        ax.bar(x, values, bottom=bottom, label=level, color=colors[level])
        bottom += values
    ax.set_ylabel("Images")
    ax.set_title("Trust-level distribution under attacks")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.legend(title="Trust level")
    fig.tight_layout()
    fig.savefig(figures / "trust_distribution.png", dpi=220)
    plt.close(fig)

    fp_count = sum(int(row["false_positive"]) for row in negatives)
    tn_count = len(negatives) - fp_count
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["True negative", "False positive"], [tn_count, fp_count], color=["#4C78A8", "#E45756"])
    ax.set_ylabel("Images")
    ax.set_title("Negative-sample verification")
    fig.tight_layout()
    fig.savefig(figures / "false_positive.png", dpi=220)
    plt.close(fig)

    lines = [
        "# 论文一实验结果报告",
        "",
        "## 实验设置",
        "",
        f"- 数据库记录数：{summary['database_records']}",
        f"- 嵌入图像数：{len(quality)}",
        f"- 攻击评价样本数：{len(robustness)}",
        f"- 负样本数：{len(negatives)}",
        "- 水印方法：DWT+DCT 盲水印",
        "- 载荷结构：平台 ID、generation_id、模型版本、时间摘要、内容摘要、CRC16、RS(32,16)",
        "- 重复编码：4 次比特重复",
        f"- 嵌入强度：alpha={alpha_text}",
        "",
        "## 图像质量",
        "",
        f"- 平均 PSNR：{summary['quality']['mean_psnr']:.4f} dB",
        f"- 平均 SSIM：{summary['quality']['mean_ssim']:.6f}",
        "",
        "## 鲁棒性",
        "",
        "| Attack | Success rate | Mean BER | Mean score | High | Medium | Low |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label in labels:
        rows = grouped[label]
        counts = Counter(row["trust"] for row in rows)
        lines.append(
            f"| {label} | {sum(int(r['success']) for r in rows) / len(rows):.4f} | "
            f"{sum(float(r['ber']) for r in rows) / len(rows):.4f} | "
            f"{sum(float(r['score']) for r in rows) / len(rows):.4f} | "
            f"{counts['high']} | {counts['medium']} | {counts['low']} |"
        )

    lines += [
        "",
        "## 负样本误报",
        "",
        f"- 负样本总数：{len(negatives)}",
        f"- 误报数：{fp_count}",
        f"- 误报率：{fp_count / len(negatives):.4f}",
        "",
        "## 图表",
        "",
        "![quality](figures/quality_distribution.png)",
        "",
        "![success](figures/robustness_success.png)",
        "",
        "![ber](figures/robustness_ber.png)",
        "",
        "![trust](figures/trust_distribution.png)",
        "",
        "![fpr](figures/false_positive.png)",
        "",
    ]
    (results / "experiment_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"report={results / 'experiment_report.md'}")
    print(f"figures={figures}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        default=str(SCRIPT_DIR / "results_full"),
    )
    args = parser.parse_args()
    main(args.results_dir)
