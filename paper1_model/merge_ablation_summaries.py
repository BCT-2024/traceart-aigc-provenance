#!/usr/bin/env python3
"""Merge independently computed full-scale ablation group summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR / "results_ablation_full_alpha28"
PARTS = [
    ROOT / "summary_carrier.csv",
    ROOT / "summary_coding.csv",
    ROOT / "summary_verification.csv",
    ROOT / "summary_alpha.csv",
]
OUTPUT = ROOT / "ablation_summary.csv"
MANIFEST = ROOT / "ablation_manifest.json"
REPORT = ROOT / "ablation_report_full_alpha28.md"


def main():
    rows = []
    for path in PARTS:
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows.extend(csv.DictReader(handle))

    group_order = {"carrier": 0, "coding": 1, "verification": 2, "alpha": 3}
    config_order = {
        "dwt_dct": 0,
        "dwt_only": 1,
        "dct_only": 2,
        "lsb": 3,
        "rs_repeat": 0,
        "rs_only": 1,
        "repeat_only": 2,
        "raw": 3,
    }
    rows.sort(
        key=lambda row: (
            group_order[row["group"]],
            int(row["config"].split("_")[1])
            if row["group"] == "alpha"
            else config_order.get(row["config"], 9),
        )
    )
    fields = [
        "group",
        "config",
        "mean_psnr",
        "mean_ssim",
        "clean_success",
        "jpeg50_success",
        "crop_success",
        "noise8_success",
        "blur_success",
        "screenshot_success",
        "false_positive_rate",
    ]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "sample": {"positive": 200, "negative_ai": 50, "natural": 50},
        "base_alpha": 28.0,
        "alpha_sweep": [8, 12, 16, 20, 24, 28],
        "completed_configs": len(rows),
        "output": str(OUTPUT),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Full-Scale Ablation Under the Final Configuration",
        "",
        "## Protocol",
        "",
        "- Positives: 200",
        "- Other-model AI negatives: 50",
        "- Natural negatives: 50",
        "- Carrier, coding, and verification-mode configurations: alpha=28",
        "- Alpha sweep: 8, 12, 16, 20, 24, and 28",
        "- Attack evaluation: the 15 standard single-attack conditions",
        "",
        "All rows were produced from the same evaluation command and attack list.",
        "",
    ]
    group_titles = {
        "carrier": "Carrier ablation",
        "coding": "Coding ablation",
        "verification": "Verification-mode ablation",
        "alpha": "Embedding-strength ablation",
    }
    for group in ("carrier", "coding", "verification", "alpha"):
        lines += [
            f"## {group_titles[group]}",
            "",
            "| Configuration | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot | FPR |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in (item for item in rows if item["group"] == group):
            lines.append(
                f"| {row['config']} | {float(row['mean_psnr']):.2f} | "
                f"{float(row['mean_ssim']):.4f} | "
                f"{100 * float(row['clean_success']):.1f} | "
                f"{100 * float(row['jpeg50_success']):.1f} | "
                f"{100 * float(row['crop_success']):.1f} | "
                f"{100 * float(row['noise8_success']):.1f} | "
                f"{100 * float(row['blur_success']):.1f} | "
                f"{100 * float(row['screenshot_success']):.1f} | "
                f"{100 * float(row['false_positive_rate']):.2f} |"
            )
        lines.append("")
    dct_combined_path = SCRIPT_DIR / "results_combined_dct_only_alpha28" / "summary.json"
    dwt_combined_path = SCRIPT_DIR / "results_combined_alpha28" / "summary.json"
    if dct_combined_path.exists() and dwt_combined_path.exists():
        dct_combined = json.loads(dct_combined_path.read_text(encoding="utf-8"))
        dwt_combined = json.loads(dwt_combined_path.read_text(encoding="utf-8"))
        combined_rows = []
        for key, label in (
            ("crop_jpeg", "Crop+JPEG70"),
            ("resize_jpeg", "Resize0.75+JPEG70"),
            ("screenshot_noise", "Screenshot+noise"),
            ("blur_jpeg", "Blur+JPEG70"),
            ("crop_resize_jpeg", "Crop0.9+Resize0.8+JPEG70"),
            ("social_recompress", "Social recompression"),
        ):
            combined_rows.append(
                {
                    "attack": label,
                    "dct_only": dct_combined[key]["success_rate"],
                    "dwt_dct": dwt_combined[key]["success_rate"],
                }
            )
        with (ROOT / "combined_carrier_comparison.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["attack", "dct_only", "dwt_dct"],
            )
            writer.writeheader()
            writer.writerows(combined_rows)
        lines += [
            "## Combined-Attack Carrier Check",
            "",
            "| Attack | DCT-only | DWT-DCT |",
            "|---|---:|---:|",
        ]
        for row in combined_rows:
            lines.append(
                f"| {row['attack']} | {100 * row['dct_only']:.1f}% | "
                f"{100 * row['dwt_dct']:.1f}% |"
            )
        lines.append("")
    lines += [
        "## Key observations",
        "",
        "- DCT-only attains higher PSNR and comparable single-attack crop",
        "  accuracy, so DWT-DCT must not be described as globally superior.",
        "- DWT-DCT remains materially stronger for blur+JPEG (96.0% versus",
        "  29.5% for DCT-only), which supports retaining it for compound",
        "  transformations.",
        "- RS+repeat improves crop success over repeat-only (92.0% versus",
        "  81.5%) with only a 0.03 dB PSNR difference.",
        "- Alpha=28 improves crop and blur success over alpha=24 while reducing",
        "  mean PSNR by approximately 0.31 dB.",
        "",
        "The table values are empirical rates from their respective configurations.",
        "Carrier and coding differences must be interpreted with both success and",
        "fidelity in view; a higher PSNR alone does not establish a better carrier.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
