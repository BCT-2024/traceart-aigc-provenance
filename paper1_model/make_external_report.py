#!/usr/bin/env python3
"""Create a comparison report against external watermark baselines."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
EXTERNAL = SCRIPT_DIR / "results_external_baselines"
OUT = EXTERNAL


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def attack_rows(rows, attack, params=None):
    expected = params or {}
    return [
        row
        for row in rows
        if row["attack"] == attack and json.loads(row["params"] or "{}") == expected
    ]


def mean_metric(rows, field):
    if not rows:
        raise ValueError(f"No rows available for metric {field}")
    return float(np.mean([float(row[field]) for row in rows]))


def success(summary, key):
    return summary.get(key, {}).get("success_rate", 0.0)


def ber(summary, key):
    return summary.get(key, {}).get("mean_ber", 1.0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    external = json.loads((EXTERNAL / "summary.json").read_text(encoding="utf-8"))
    external_rows = load_csv(EXTERNAL / "external_detail.csv")
    ours = json.loads(
        (SCRIPT_DIR / "results_full_capture_scan" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    ours_combined = json.loads(
        (SCRIPT_DIR / "results_combined_alpha28" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    ours_single_rows = load_csv(
        SCRIPT_DIR / "results_full_capture_scan" / "robustness_detail.csv"
    )
    ours_combined_rows = load_csv(
        SCRIPT_DIR / "results_combined_alpha28" / "combined_detail.csv"
    )
    ours_quality_rows = load_csv(
        SCRIPT_DIR / "results_full_capture_scan" / "quality_metrics.csv"
    )

    ids_by_method = {
        method: {
            row["generation_id"]
            for row in external_rows
            if row["method"] == method
        }
        for method in ("dwtDct", "dwtDctSvd", "rivaGan")
    }
    matched_ids = set.intersection(*ids_by_method.values())
    ours_single = [
        row for row in ours_single_rows if row["generation_id"] in matched_ids
    ]
    ours_combined = [
        row for row in ours_combined_rows if row["generation_id"] in matched_ids
    ]
    ours_quality = [
        row for row in ours_quality_rows if row["generation_id"] in matched_ids
    ]

    ours_attacks = {
        "clean": attack_rows(ours_single, "clean"),
        "jpeg50": attack_rows(ours_single, "jpeg", {"quality": 50}),
        "crop": attack_rows(ours_single, "crop", {"ratio": 0.9}),
        "blur": attack_rows(ours_single, "blur", {"ksize": 3}),
        "screenshot": attack_rows(ours_single, "screenshot"),
        "crop_resize_jpeg": attack_rows(
            ours_combined,
            "crop_resize_jpeg",
            {"crop_ratio": 0.9, "scale": 0.8, "jpeg_quality": 70},
        ),
    }
    ours_matched = {
        attack: {
            "count": len(rows),
            "success_rate": mean_metric(rows, "success"),
            "mean_ber": mean_metric(rows, "ber"),
        }
        for attack, rows in ours_attacks.items()
    }
    ours_psnr = mean_metric(ours_quality, "psnr")
    ours_ssim = mean_metric(ours_quality, "ssim")

    rows = [
        {
            "method": "Ours (structured + DB, matched subset)",
            "payload_bits": 1024,
            "count": len(matched_ids),
            "psnr": ours_psnr,
            "ssim": ours_ssim,
            "jpeg50": ours_matched["jpeg50"]["success_rate"],
            "crop": ours_matched["crop"]["success_rate"],
            "blur": ours_matched["blur"]["success_rate"],
            "screenshot": ours_matched["screenshot"]["success_rate"],
            "crop_resize_jpeg": ours_matched["crop_resize_jpeg"]["success_rate"],
        },
        {
            "method": "external dwtDct",
            "payload_bits": 1024,
            "count": external["dwtDct:clean"]["count"],
            "psnr": external["dwtDct:clean"]["mean_psnr"],
            "ssim": external["dwtDct:clean"]["mean_ssim"],
            "jpeg50": success(external, "dwtDct:jpeg"),
            "crop": success(external, "dwtDct:crop"),
            "blur": success(external, "dwtDct:blur"),
            "screenshot": success(external, "dwtDct:screenshot"),
            "crop_resize_jpeg": success(external, "dwtDct:crop_resize_jpeg"),
        },
        {
            "method": "external dwtDctSvd",
            "payload_bits": 1024,
            "count": external["dwtDctSvd:clean"]["count"],
            "psnr": external["dwtDctSvd:clean"]["mean_psnr"],
            "ssim": external["dwtDctSvd:clean"]["mean_ssim"],
            "jpeg50": success(external, "dwtDctSvd:jpeg"),
            "crop": success(external, "dwtDctSvd:crop"),
            "blur": success(external, "dwtDctSvd:blur"),
            "screenshot": success(external, "dwtDctSvd:screenshot"),
            "crop_resize_jpeg": success(external, "dwtDctSvd:crop_resize_jpeg"),
        },
        {
            "method": "RivaGAN (pretrained)",
            "payload_bits": 32,
            "count": external["rivaGan:clean"]["count"],
            "psnr": external["rivaGan:clean"]["mean_psnr"],
            "ssim": external["rivaGan:clean"]["mean_ssim"],
            "jpeg50": success(external, "rivaGan:jpeg"),
            "crop": success(external, "rivaGan:crop"),
            "blur": success(external, "rivaGan:blur"),
            "screenshot": success(external, "rivaGan:screenshot"),
            "crop_resize_jpeg": success(external, "rivaGan:crop_resize_jpeg"),
        },
    ]

    # BER comparison for the three methods with directly measured BER.
    labels = ["Ours", "dwtDct", "dwtDctSvd", "RivaGAN"]
    attacks = ["clean", "jpeg50", "crop", "blur", "screenshot", "crop_resize_jpeg"]
    ber_values = {
        "Ours": [
            ours_matched["clean"]["mean_ber"],
            ours_matched["jpeg50"]["mean_ber"],
            ours_matched["crop"]["mean_ber"],
            ours_matched["blur"]["mean_ber"],
            ours_matched["screenshot"]["mean_ber"],
            ours_matched["crop_resize_jpeg"]["mean_ber"],
        ],
        "dwtDct": [
            ber(external, "dwtDct:clean"),
            ber(external, "dwtDct:jpeg"),
            ber(external, "dwtDct:crop"),
            ber(external, "dwtDct:blur"),
            ber(external, "dwtDct:screenshot"),
            ber(external, "dwtDct:crop_resize_jpeg"),
        ],
        "dwtDctSvd": [
            ber(external, "dwtDctSvd:clean"),
            ber(external, "dwtDctSvd:jpeg"),
            ber(external, "dwtDctSvd:crop"),
            ber(external, "dwtDctSvd:blur"),
            ber(external, "dwtDctSvd:screenshot"),
            ber(external, "dwtDctSvd:crop_resize_jpeg"),
        ],
        "RivaGAN": [
            ber(external, "rivaGan:clean"),
            ber(external, "rivaGan:jpeg"),
            ber(external, "rivaGan:crop"),
            ber(external, "rivaGan:blur"),
            ber(external, "rivaGan:screenshot"),
            ber(external, "rivaGan:crop_resize_jpeg"),
        ],
    }

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(attacks))
    width = 0.2
    for index, method in enumerate(labels):
        ax.bar(x + (index - 1.5) * width, ber_values[method], width, label=method)
    ax.set_ylabel("Mean BER")
    ax.set_title("External watermark comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(attacks, rotation=20)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "external_ber_comparison.png", dpi=220)
    plt.close(fig)

    comparison_fields = [
        "method",
        "payload_bits",
        "count",
        "psnr",
        "ssim",
        "jpeg50",
        "crop",
        "blur",
        "screenshot",
        "crop_resize_jpeg",
    ]
    with (OUT / "matched_comparison.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=comparison_fields)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 外部水印基线对比",
        "",
        "## 方法说明",
        "",
        "- `Ours`：128 位结构化载荷 + RS(32,16) + 4 次重复，总编码长度 1024 位，包含数据库联合验证。",
        "- `external dwtDct`：`invisible-watermark` 库的 DWT-DCT 实现，嵌入同样的 1024 位编码载荷。",
        "- `external dwtDctSvd`：`invisible-watermark` 库的 DWT-DCT-SVD 实现，嵌入同样的 1024 位编码载荷。",
        "- `RivaGAN`：预训练神经水印模型，原生 32 位载荷，无法承载本文的 128 位结构化载荷。",
        f"- 公平比较口径：四种方法均使用共同可用的 {len(matched_ids)} 张正样本。",
        (
            f"- 全量 200 张上的本方法结果另见 `results_full_capture_scan/`："
            f"PSNR {ours['quality']['mean_psnr']:.2f} dB，"
            f"SSIM {ours['quality']['mean_ssim']:.6f}。"
        ),
        "",
        "## 结果对比",
        "",
        "| Method | Payload bits | n | PSNR | SSIM | JPEG50 | Crop | Blur | Screenshot | Crop+Resize+JPEG |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['payload_bits']} | {row['count']} | "
            f"{row['psnr']:.2f} | {row['ssim']:.6f} | "
            f"{row['jpeg50']:.2f} | {row['crop']:.2f} | {row['blur']:.2f} | "
            f"{row['screenshot']:.2f} | {row['crop_resize_jpeg']:.2f} |"
        )
    lines += [
        "",
        "## 主要结论",
        "",
        "- 外部 `dwtDct` 即使干净图也无法可靠恢复 1024 位载荷，因此不适合作为长结构化载荷载体。",
        "- 外部 `dwtDctSvd` 可以承载 1024 位并在干净图、模糊和截图上表现较好，但裁剪和裁剪组合攻击失败。",
        "- `RivaGAN` 的画质和鲁棒性最好，但只支持 32 位载荷，不能承载本文的完整结构化来源信息。",
        "- 本文方法在 128 位结构化载荷、1024 位编码长度和数据库联合验证条件下，裁剪与组合攻击表现明显优于外部 dwtDct/dwtDctSvd。",
        "- RivaGAN 的结果只能作为短载荷鲁棒性参照，不能视为同等载荷条件下的直接竞争基线。",
        "",
        "## 图",
        "",
        "![ber](external_ber_comparison.png)",
        "",
    ]
    (OUT / "external_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report={OUT / 'external_report.md'}")


if __name__ == "__main__":
    main()
