#!/usr/bin/env python3
"""Create ablation figures and a Markdown report."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
ABLATION_DIR = SCRIPT_DIR / "results_ablation"
VERIFY_DIR = SCRIPT_DIR / "results_verification_ablation"
FIGURES = ABLATION_DIR / "figures"


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = load_csv(ABLATION_DIR / "ablation_summary.csv")
    verify_summary = json.loads(
        (VERIFY_DIR / "summary.json").read_text(encoding="utf-8")
    )
    full_rs_summary = json.loads(
        (SCRIPT_DIR / "results_full" / "summary.json").read_text(encoding="utf-8")
    )
    full_repeat_summary = json.loads(
        (SCRIPT_DIR / "results_full_repeat_only" / "summary.json").read_text(
            encoding="utf-8"
        )
    )

    metrics = [
        ("clean_success", "Clean"),
        ("jpeg50_success", "JPEG50"),
        ("crop_success", "Crop"),
        ("noise8_success", "Noise8"),
        ("blur_success", "Blur"),
        ("screenshot_success", "Screenshot"),
    ]

    def grouped_plot(group, filename, title):
        selected = [row for row in rows if row["group"] == group]
        labels = [row["config"] for row in selected]
        x = np.arange(len(labels))
        width = 0.12
        fig, ax = plt.subplots(figsize=(12, 5))
        for index, (key, label) in enumerate(metrics):
            values = [float(row[key]) for row in selected]
            ax.bar(x + (index - 2.5) * width, values, width, label=label)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Success rate")
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20)
        ax.legend(ncol=3, fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGURES / filename, dpi=220)
        plt.close(fig)

    grouped_plot("carrier", "carrier_ablation.png", "Carrier ablation")
    grouped_plot("coding", "coding_ablation.png", "Coding ablation")

    alpha_rows = sorted(
        [row for row in rows if row["group"] == "alpha"],
        key=lambda row: int(row["config"].split("_")[1]),
    )
    alpha_values = [int(row["config"].split("_")[1]) for row in alpha_rows]
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(
        alpha_values,
        [float(row["mean_psnr"]) for row in alpha_rows],
        marker="o",
        color="#4C78A8",
        label="PSNR",
    )
    ax1.set_xlabel("Alpha")
    ax1.set_ylabel("PSNR (dB)", color="#4C78A8")
    ax2 = ax1.twinx()
    ax2.plot(
        alpha_values,
        [float(row["crop_success"]) for row in alpha_rows],
        marker="s",
        color="#E45756",
        label="Crop success",
    )
    ax2.plot(
        alpha_values,
        [float(row["jpeg50_success"]) for row in alpha_rows],
        marker="^",
        color="#54A24B",
        label="JPEG50 success",
    )
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel("Success rate")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="best")
    ax1.set_title("Alpha trade-off")
    fig.tight_layout()
    fig.savefig(FIGURES / "alpha_tradeoff.png", dpi=220)
    plt.close(fig)

    modes = ["watermark_only", "db_only", "joint"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(
        modes,
        [verify_summary[mode]["acceptance_rate"] for mode in modes],
        color=["#E45756", "#4C78A8", "#54A24B"],
    )
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Forgery acceptance rate")
    ax.set_title("Forged watermark acceptance")
    fig.tight_layout()
    fig.savefig(FIGURES / "forgery_acceptance.png", dpi=220)
    plt.close(fig)

    lines = [
        "# 论文一消融实验报告",
        "",
        "## 载体消融",
        "",
        "| Carrier | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in [r for r in rows if r["group"] == "carrier"]:
        lines.append(
            f"| {row['config']} | {float(row['mean_psnr']):.2f} | "
            f"{float(row['mean_ssim']):.6f} | {float(row['clean_success']):.2f} | "
            f"{float(row['jpeg50_success']):.2f} | {float(row['crop_success']):.2f} | "
            f"{float(row['noise8_success']):.2f} | {float(row['blur_success']):.2f} | "
            f"{float(row['screenshot_success']):.2f} |"
        )
    lines += [
        "",
        "## 编码消融",
        "",
        "| Coding | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in [r for r in rows if r["group"] == "coding"]:
        lines.append(
            f"| {row['config']} | {float(row['mean_psnr']):.2f} | "
            f"{float(row['mean_ssim']):.6f} | {float(row['clean_success']):.2f} | "
            f"{float(row['jpeg50_success']):.2f} | {float(row['crop_success']):.2f} | "
            f"{float(row['noise8_success']):.2f} | {float(row['blur_success']):.2f} | "
            f"{float(row['screenshot_success']):.2f} |"
        )
    lines += [
        "",
        "## 强度消融",
        "",
        "| Config | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in alpha_rows:
        lines.append(
            f"| {row['config']} | {float(row['mean_psnr']):.2f} | "
            f"{float(row['mean_ssim']):.6f} | {float(row['clean_success']):.2f} | "
            f"{float(row['jpeg50_success']):.2f} | {float(row['crop_success']):.2f} | "
            f"{float(row['noise8_success']):.2f} | {float(row['blur_success']):.2f} | "
            f"{float(row['screenshot_success']):.2f} |"
        )
    lines += [
        "",
        "## 验证模式伪造实验",
        "",
        "对负样本嵌入“格式合法但数据库不存在的假水印”，比较三种验证模式：",
        "",
        "| Verification mode | Acceptance rate | Mean score |",
        "|---|---:|---:|",
    ]
    for mode in modes:
        lines.append(
            f"| {mode} | {verify_summary[mode]['acceptance_rate']:.4f} | "
            f"{verify_summary[mode]['mean_score']:.4f} |"
        )

    def success(summary, key):
        return summary["robustness"].get(key, {}).get("success_rate", 0.0)

    full_compare_rows = [
        {
            "encoding": "RS+repeat 4 (full 200)",
            "psnr": full_rs_summary["quality"]["mean_psnr"],
            "ssim": full_rs_summary["quality"]["mean_ssim"],
            "jpeg50": success(full_rs_summary, "jpeg:{'quality': 50}"),
            "crop": success(full_rs_summary, "crop:{'ratio': 0.9}"),
            "blur": success(full_rs_summary, "blur:{'ksize': 3}"),
            "brightness": success(full_rs_summary, "brightness_contrast:{}"),
            "screenshot": success(full_rs_summary, "screenshot:{}"),
        },
        {
            "encoding": "repeat 8 (full 200)",
            "psnr": full_repeat_summary["quality"]["mean_psnr"],
            "ssim": full_repeat_summary["quality"]["mean_ssim"],
            "jpeg50": success(full_repeat_summary, "jpeg:{'quality': 50}"),
            "crop": success(full_repeat_summary, "crop:{'ratio': 0.9}"),
            "blur": success(full_repeat_summary, "blur:{'ksize': 3}"),
            "brightness": success(full_repeat_summary, "brightness_contrast:{}"),
            "screenshot": success(full_repeat_summary, "screenshot:{}"),
        },
    ]
    with (ABLATION_DIR / "full_scale_coding_comparison.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "encoding",
                "psnr",
                "ssim",
                "jpeg50",
                "crop",
                "blur",
                "brightness",
                "screenshot",
            ],
        )
        writer.writeheader()
        writer.writerows(full_compare_rows)

    lines += [
        "",
        "## 全量编码对比",
        "",
        "| Encoding | PSNR | SSIM | JPEG50 | Crop | Blur | Brightness | Screenshot |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in full_compare_rows:
        lines.append(
            f"| {row['encoding']} | {row['psnr']:.2f} | {row['ssim']:.6f} | "
            f"{row['jpeg50']:.2f} | {row['crop']:.2f} | {row['blur']:.2f} | "
            f"{row['brightness']:.2f} | {row['screenshot']:.2f} |"
        )

    lines += [
        "",
        "## 主要结论",
        "",
        "- LSB 画质最高，但在 JPEG、裁剪、噪声、模糊和截图下几乎全部失效。",
        "- DWT-only 的裁剪成功率明显较低，DCT-only 和 DWT+DCT 的裁剪表现较好。",
        "- 仅使用 RS 而不用重复编码时，裁剪和模糊成功率下降；raw 模式整体最脆弱。",
        "- RS + 4 次重复在鲁棒性和画质之间取得较好平衡。",
        "- alpha 从 16 提升到 24 后，压缩、裁剪和模糊成功率明显改善，PSNR 仍保持在约 41 dB。",
        "- watermark-only 对伪造水印的接受率为 100%；数据库验证和联合验证均为 0%。",
        "- 全量 200 张样本上，RS+repeat 的裁剪、模糊和亮度鲁棒性优于 repeat-only。",
        "",
        "## 图表",
        "",
        "![carrier](figures/carrier_ablation.png)",
        "",
        "![coding](figures/coding_ablation.png)",
        "",
        "![alpha](figures/alpha_tradeoff.png)",
        "",
        "![forgery](figures/forgery_acceptance.png)",
        "",
    ]
    report = ABLATION_DIR / "ablation_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report={report}")
    print(f"figures={FIGURES}")


if __name__ == "__main__":
    main()
